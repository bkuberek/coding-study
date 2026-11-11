"""The state of the language servers and their installation: the `code intelligence` rows of
`cstudy doctor`, `cstudy doctor --fix`, and `GET /api/v1/code-intelligence/languages`
(docs/specs/web-ui.md#language-servers); which server and root a session gets from an attempt
(docs/specs/web-ui.md#sessions); and, for a service project, the sidecar its server runs in
(docs/specs/service-projects.md#language-servers).

Like highlighting, code intelligence grades nothing and records nothing.
"""

import secrets
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date, timedelta
from enum import StrEnum
from pathlib import Path

from coding_study.application.active_attempt import attempt_in_progress
from coding_study.application.environment import Environment
from coding_study.application.ports import (
    Fetched,
    FileMissing,
    JdkSelector,
    LanguageServerInstaller,
    LanguageServerLocator,
    NotInstalled,
    ProbeResult,
    ServerProbe,
    SidecarEngine,
    Unpacked,
    VersionFailed,
    VersionPrinted,
)
from coding_study.application.service_lifecycle import server_in_install_cache
from coding_study.application.service_stacks import RUN_ID_BYTES, workspace_id
from coding_study.domain.attempts import Attempt
from coding_study.domain.code_intelligence import (
    EXPIRY_WARNING_DAYS,
    LSP_DIRECTORY,
    NOT_AVAILABLE_YET,
    SIDECAR_SERVERS,
    LanguageServer,
    License,
    cache_install,
    route_of,
    server_for,
    sidecar_image,
    sidecar_server,
    sidecar_toolchain,
)
from coding_study.domain.docker_engine import EngineStatus
from coding_study.domain.errors import LanguageServerNotInstalledError, UsageError
from coding_study.domain.jdk import JdkRange, jdk_fix, no_jdk_sentence, range_text
from coding_study.domain.layout import BUILD_DIRECTORY, CASES_DIRECTORY, RUNS_DIRECTORY
from coding_study.domain.preferences import Preferences
from coding_study.domain.problem import Language, ProblemKind, ProblemMeta
from coding_study.domain.sandbox import (
    NODE_IMAGE,
    SIDECAR_DATA,
    SharedFolder,
    SidecarPlan,
    StackIdentity,
    StackKind,
    cache_volume_of,
    install_stack_name,
    run_stack_name,
)
from coding_study.domain.service_project import ServiceProject, service_of
from coding_study.domain.workspace_projects import project_folder

FIX_COMMAND = "cstudy doctor --fix"
ACCEPT_LICENSE_OPTION = "--accept-license"
OFF = "code intelligence is off: turn it on in Settings"
NO_DOCKER: Mapping[EngineStatus, str] = {
    EngineStatus.STOPPED: "Docker is not running",
    EngineStatus.NOT_INSTALLED: "Docker is not installed",
    EngineStatus.NO_COMPOSE: "Docker has no compose v2",
    EngineStatus.NO_PERMISSION: "Docker refuses this user",
}
"""Why a service project's server cannot start, by the engine's state, as the status bar says it;
`cstudy doctor` says the rest."""
NO_SIDECAR_IMAGE = f"needs the node image: docker pull {NODE_IMAGE}"
"""A TypeScript project's `cstudy start` pulled the image, a Python project's did not. The status
bar shows what comes before the colon, and its tooltip the rest."""
NOT_IN_INSTALL_CACHE = "not in the project's install cache"
INSTALL_CACHE_FIX = "cstudy test"
"""A run installs again while the install cache lacks the server, now that code intelligence is
on, and builds it there."""
NO_PROJECT_IMAGE = "needs the project's image: run cstudy test or cstudy dev, which pull it"
"""A Java project's server runs on the project's image, which a run pulls. Its name and digest
would not fit in a close reason, whose 123 bytes would cut the digest."""


class ServerStatus(StrEnum):
    INSTALLED = "installed"
    NOT_INSTALLED = "not_installed"
    NEEDS_JDK = "needs_jdk"
    """Installed, but the selected JDK is not one the server runs on."""
    EXPIRED = "expired"
    """The fetched build's last day has passed; `cstudy doctor --fix` fetches the newest."""
    LICENSE_NOT_ACCEPTED = "license_not_accepted"
    """Its vendor's license is not accepted, so `--fix` has not downloaded it and no session runs
    it, whatever `.cs/lsp/` holds."""
    NOT_AVAILABLE = "not_available"


@dataclass(frozen=True, slots=True)
class LanguageServerState:
    language: Language
    server: str | None
    """None where the language has no server yet."""
    version: str | None
    """The pinned version, whether or not it is installed: for gopls, the one the selected Go
    pins; for a server cstudy does not pin (rust-analyzer), the installed one, else None."""
    status: ServerStatus
    detail: str
    """What the Settings view shows: the installed version, or why the server is not usable,
    ending in the fix (`run cstudy doctor --fix`, `run rustup component add rust-analyzer`)
    unless the reason is the version command's own words."""
    idle_s: int | None
    problem: str | None
    """Why an unusable server is not usable, as the doctor row says it, without the fix; None
    unless the status is `not_installed` or `needs_jdk`."""
    fix: str | None
    """What makes an unusable server usable, as the doctor row names it."""
    warning: str | None = None
    """Set for a usable build that stops soon, as the doctor row warns of it; `fix` is None."""


def language_server_states(
    locator: LanguageServerLocator, jdk: JdkSelector
) -> tuple[LanguageServerState, ...]:
    """One state per language, in `cstudy list`'s order, whatever the preference says; a server
    that runs on a JDK is judged against the selected one, and one that Go builds against the
    version the selected Go pins."""
    return tuple(_state(language, locator, jdk) for language in Language)


def session_server_states(
    environment: Environment, attempt_id: int | None
) -> tuple[LanguageServerState, ...]:
    """The states as a session of the attempt judges its servers, which the page reads before it
    connects: a service project's TypeScript runs the project's own compiler in its sidecar, so it
    needs nothing of the workspace's `typescript/`, and its gopls is the one its install built into
    its install cache. Without an attempt, or for one that is no service project's, these are
    `language_server_states`."""
    locator, jdk = environment.language_servers, environment.jdk
    slug = _service_slug(environment, attempt_id)
    if slug is None:
        return language_server_states(locator, jdk)
    folder = str(environment.root / project_folder(slug))
    return tuple(
        _cache_state_of(environment, slug, language) or _state(language, locator, jdk, folder)
        for language in Language
    )


def _service_slug(environment: Environment, attempt_id: int | None) -> str | None:
    """The slug of a service project's attempt; None for any other."""
    attempt = None if attempt_id is None else environment.progress.attempt(attempt_id)
    if attempt is None or attempt.language is None:
        return None
    if service_of(environment.problems.load(attempt.slug).meta) is None:
        return None
    return attempt.slug


def _cache_state_of(
    environment: Environment, slug: str, language: Language
) -> LanguageServerState | None:
    """For a server that a service project's install builds into its install cache, whether the
    last install built the version cstudy pins; None for any other server."""
    server = server_for(language)
    install = None if server is None else cache_install(server)
    if server is None or install is None:
        return None
    built = server_in_install_cache(environment, slug, install.name)
    if built == install.version:
        return _state_of(server, built, f"{server.name} {built}", None)
    row = f"{server.name} {install.version} is not in the project's install cache"
    problem = _Problem(row, NOT_IN_INSTALL_CACHE, fix=INSTALL_CACHE_FIX)
    return _state_of(server, install.version, f"{problem.reason}: run {problem.fix}", problem)


@dataclass(frozen=True, slots=True)
class SessionTarget:
    """What a session runs: a server, in a root of the workspace."""

    server: LanguageServer
    workspace: Path
    """The workspace root, where `.cs/lsp/` is."""
    root: str
    """The session's root relative to the workspace, `/`-separated: the practice project of the
    attempt's language, or its project folder."""
    content_root: Path
    """Where the reference solutions are, which a library file is never read from."""
    java_home: Path | None = None
    """The selected JDK's home, for a server that runs on a JDK."""
    sidecar: SidecarPlan | None = None
    """Where a service project's server runs, in place of this machine: sandboxed code writes the
    project folder. None for every other attempt."""

    @property
    def directory(self) -> Path:
        """The server's current directory."""
        return self.workspace / self.root

    @property
    def lsp_directory(self) -> Path:
        return self.workspace / LSP_DIRECTORY

    @property
    def standard_library_links(self) -> Path | None:
        """Where the links to the standard library the server reads are, for the root; None for
        a server that finds the library itself."""
        library = self.server.standard_library
        return None if library is None else self.lsp_directory / library.links / self.root

    @property
    def hidden(self) -> tuple[Path, ...]:
        """Where the reference solutions, the generated cases with their expected values, the run
        data and the content root are: no library file is read from them, no answer names a place
        in them and a Node server cannot open them (docs/specs/web-ui.md#hidden-directories)."""
        return (
            self.workspace / BUILD_DIRECTORY,
            self.workspace / CASES_DIRECTORY,
            self.workspace / RUNS_DIRECTORY,
            self.content_root,
        )


def session_target(
    environment: Environment, preferences: Preferences, attempt_id: int
) -> SessionTarget:
    """The server and root for a session of the attempt, checked in the order the route's
    refusals come.

    Raises UnknownAttemptError, AttemptEndedError, UsageError (the preference is off, the attempt
    has no code, its language has no server yet, or none in a service project's sidecar) and
    LanguageServerNotInstalledError (the server is missing, or the selected JDK cannot run it).
    """
    attempt = attempt_in_progress(environment.progress, attempt_id)
    if not preferences.code_intelligence:
        raise UsageError(OFF)
    language = _language_of(attempt)
    meta = environment.problems.load(attempt.slug).meta
    server = _server_of(meta, language)
    root = _root(meta, server)
    service = service_of(meta)
    sidecar = None if service is None else _sidecar(environment, meta.slug, root, server, service)
    if sidecar is not None:
        server = sidecar_server(server, sidecar.project.path)
    jdk = environment.jdk
    state = None if sidecar is None else _cache_state_of(environment, meta.slug, language)
    if state is None:
        state = _located(server, environment.language_servers, jdk)
    if state.problem is not None:
        raise LanguageServerNotInstalledError(state.problem, state.fix or FIX_COMMAND)
    java_home = jdk.selected_home() if server.jdks is not None else None
    content_root = environment.content_root
    return SessionTarget(server, environment.root, root, content_root, java_home, sidecar)


def sidecar_unavailable(engine: SidecarEngine, image: str = NODE_IMAGE) -> str | None:
    """Why a service project's server cannot start now, as the status bar says it; None once the
    engine answers and the sidecar's `image` is here. A session starts no engine and pulls
    nothing: a file opened in the editor is no reason to start a VM or to download an image."""
    state = engine.state()
    if not state.running:
        return NO_DOCKER[state.status]
    if engine.image_present(image):
        return None
    return NO_SIDECAR_IMAGE if image == NODE_IMAGE else NO_PROJECT_IMAGE


def install_language_servers(installer: LanguageServerInstaller) -> ProbeResult | None:
    """Put the shipped manifest in `.cs/lsp/` and install it; None when `pnpm` is missing. The
    caller decides, from the `code_intelligence` preference, whether to."""
    return installer.install()


def is_unpacked(locator: LanguageServerLocator, server: LanguageServer) -> bool:
    """Whether the pinned build of an archive server is in `.cs/lsp/` already, when downloading
    it again would help nothing."""
    return isinstance(locator.probe(server), Unpacked)


def fetched_version(locator: LanguageServerLocator, server: LanguageServer) -> str | None:
    """The version of the build `cstudy doctor --fix` fetched for `server`, unless it has stopped:
    a newest build of that version needs no download."""
    probe = locator.probe(server)
    if not isinstance(probe, Fetched) or _has_stopped(probe, locator.today()):
        return None
    return probe.version


def is_usable(locator: LanguageServerLocator, server: LanguageServer, jdk: JdkSelector) -> bool:
    """Whether a session could run `server` now: installed, its license accepted, and on a JDK
    it can use."""
    return _located(server, locator, jdk).status is ServerStatus.INSTALLED


def download_language_server(
    installer: LanguageServerInstaller, server: LanguageServer
) -> ProbeResult | None:
    """Download the archive of `server` for this machine into `.cs/lsp/`, checked by its SHA-256;
    None for a server that is no archive, or has none for this machine. The caller decides, from
    the `code_intelligence` preference, `is_unpacked` and the server's license, whether to."""
    return None if server.archive is None else installer.download(server.archive)


def go_install_version(locator: LanguageServerLocator, server: LanguageServer) -> str | None:
    """The version `go install` builds of a server that Go builds: the one the selected Go pins,
    unless it is installed and runs already. None for a server Go does not build. The caller
    decides, from the `code_intelligence` preference, whether to."""
    if server.go_install is None:
        return None
    wanted = server.go_install.version_for(locator.go_release())
    return None if _problem(server, wanted, locator.probe(server)) is None else wanted


def install_language_server_with_go(
    installer: LanguageServerInstaller, server: LanguageServer, version: str
) -> ProbeResult | None:
    """`go install` of `version` of `server` into `.cs/lsp/bin/`; None when `go` is missing or
    Go does not build the server."""
    install = server.go_install
    return None if install is None else installer.go_install(install, version)


def _language_of(attempt: Attempt) -> Language:
    if attempt.language is None:
        raise UsageError(f"{attempt.slug} has no code")
    return attempt.language


def _server_of(meta: ProblemMeta, language: Language) -> LanguageServer:
    """The route table says where the server runs (docs/specs/web-ui.md#where-each-server-runs): a
    service project's folder is written by sandboxed code, and a server on this machine would read
    it, so its server runs in a sidecar, in the languages whose servers run there
    (docs/specs/service-projects.md#language-servers)."""
    server = server_for(language)
    if server is None:
        raise UsageError(f"no code intelligence for {language.value} yet")
    route = route_of(meta, language)
    if route is None:
        raise UsageError(f"no code intelligence for {meta.kind.value} problems yet")
    if not route.runs:
        raise UsageError(
            f"no code intelligence for {language.value} service projects yet: {route.reason}"
        )
    return server


def _root(meta: ProblemMeta, server: LanguageServer) -> str:
    if meta.kind is ProblemKind.PROJECT:
        return project_folder(meta.slug)
    return server.root_project


def _sidecar(
    environment: Environment,
    slug: str,
    root: str,
    server: LanguageServer,
    service: ServiceProject,
) -> SidecarPlan:
    """A sidecar of its own for each session, owned by this process, so a sweep of a `cstudy serve`
    that died takes it down: on the Node image for a Node server, on the project's own image for a
    server that needs its JDK and Gradle, with the project's install cache read-only."""
    engine = environment.sandbox
    owner = engine.owner_pid()
    name = run_stack_name(StackKind.LSP, owner, secrets.token_hex(RUN_ID_BYTES))
    workspace = workspace_id(environment)
    identity = StackIdentity(name, StackKind.LSP, workspace, slug, owner)
    run = str((environment.root / RUNS_DIRECTORY / name).resolve())
    cache = None
    if service.app.install_cache:
        cache = cache_volume_of(install_stack_name(slug, workspace))
    return SidecarPlan(
        identity=identity,
        user=engine.host_user(),
        project=_shared(environment.root / root),
        servers=_shared(environment.root / LSP_DIRECTORY),
        run=run,
        image=sidecar_image(server, service.image),
        toolchain=sidecar_toolchain(server, service, f"{run}/{SIDECAR_DATA}", cache),
    )


def _shared(folder: Path) -> SharedFolder:
    return SharedFolder(path=str(folder), source=str(folder.resolve()))


def _state(
    language: Language,
    locator: LanguageServerLocator,
    jdk: JdkSelector,
    service_folder: str | None = None,
) -> LanguageServerState:
    """The server's state on this machine, or in the sidecar of the service project whose folder
    is `service_folder`."""
    server = server_for(language)
    if server is None:
        return LanguageServerState(
            language, None, None, ServerStatus.NOT_AVAILABLE, NOT_AVAILABLE_YET, None, None, None
        )
    if service_folder is not None and server in SIDECAR_SERVERS:
        server = sidecar_server(server, service_folder)
    return _located(server, locator, jdk)


def _located(
    server: LanguageServer, locator: LanguageServerLocator, jdk: JdkSelector
) -> LanguageServerState:
    wanted = _pinned(server, locator)
    probe = locator.probe(server)
    today = locator.today()
    problem = (
        _expiry_problem(server, probe, today)
        or _license_problem(server, locator, probe)
        or _problem(server, wanted, probe)
        or _jdk_problem(server, jdk)
    )
    version = wanted or _printed(server, probe)
    if problem is None:
        state = _state_of(server, version, _installed(server, version, probe), None)
        return replace(state, warning=_expiry_warning(server, probe, today))
    detail = problem.reason if problem.own_words else f"{problem.reason}: run {problem.fix}"
    return _state_of(server, version, detail, problem)


def _pinned(server: LanguageServer, locator: LanguageServerLocator) -> str | None:
    """The version cstudy needs: the catalog's, or for a server that Go builds the one the
    selected Go pins; None for a server cstudy does not pin."""
    if server.go_install is None:
        return server.version
    return server.go_install.version_for(locator.go_release())


def _printed(server: LanguageServer, probe: ServerProbe) -> str | None:
    if isinstance(probe, Fetched):
        return probe.version
    return server.printed_version(probe.output) if isinstance(probe, VersionPrinted) else None


def _installed(server: LanguageServer, version: str | None, probe: ServerProbe) -> str:
    """`kotlin-lsp 263.7084.0, runs until 2026-11-12` for a fetched build that names its last
    day; the name and the version otherwise."""
    if isinstance(probe, Fetched) and probe.last_day is not None:
        return f"{server.name} {version}, runs until {probe.last_day.isoformat()}"
    return f"{server.name} {version}"


def _has_stopped(probe: Fetched, today: date) -> bool:
    return probe.last_day is not None and today > probe.last_day


def _expiry_warning(server: LanguageServer, probe: ServerProbe, today: date) -> str | None:
    """Set while a fetched build has fewer than `EXPIRY_WARNING_DAYS` days left to run."""
    if not isinstance(probe, Fetched) or probe.last_day is None:
        return None
    days = (probe.last_day - today).days + 1
    if days >= EXPIRY_WARNING_DAYS:
        return None
    left = "its last day is today" if days == 1 else f"{days} days left"
    return (
        f"{server.name} {probe.version} runs until {probe.last_day.isoformat()} ({left}), as "
        f"JetBrains' early-access builds stop; {FIX_COMMAND} fetches a newer one once there is"
    )


def _state_of(
    server: LanguageServer, version: str | None, detail: str, problem: "_Problem | None"
) -> LanguageServerState:
    return LanguageServerState(
        server.language,
        server.name,
        version,
        ServerStatus.INSTALLED if problem is None else problem.status,
        detail,
        server.idle_s,
        None if problem is None else problem.row,
        None if problem is None else problem.fix,
    )


@dataclass(frozen=True, slots=True)
class _Problem:
    row: str
    """As the doctor row says it, after the server's name."""
    reason: str = ""
    """As the Settings view says it; the row's words unless given."""
    own_words: bool = False
    """A reason that takes no `run <fix>` after it: the version command's own line,
    or a JDK, which the fix does not change."""
    status: ServerStatus = ServerStatus.NOT_INSTALLED
    fix: str = FIX_COMMAND

    def __post_init__(self) -> None:
        if not self.reason:
            object.__setattr__(self, "reason", self.row)


def _problem(server: LanguageServer, wanted: str | None, probe: ServerProbe) -> _Problem | None:
    """None when the `wanted` version is installed and usable, or any version for a server
    cstudy does not pin. The fix is the catalog's for a server cstudy does not install."""
    fix = server.fix or FIX_COMMAND
    match probe:
        case NotInstalled():
            return _Problem(f"{server.name} is not installed", "not installed", fix=fix)
        case FileMissing():
            return _Problem(_missing(server), fix=fix)
        case VersionFailed(reason):
            return _Problem(reason, own_words=True, fix=fix)
        case VersionPrinted(output):
            return _version_problem(server, wanted, server.printed_version(output))
        case Unpacked() | Fetched():
            return None


def _expiry_problem(server: LanguageServer, probe: ServerProbe, today: date) -> _Problem | None:
    """None unless the fetched build's last day has passed; `--fix` fetches the newest."""
    last_day = probe.last_day if isinstance(probe, Fetched) else None
    if last_day is None or today <= last_day or not isinstance(probe, Fetched):
        return None
    stopped = (last_day + timedelta(days=1)).isoformat()
    build = f"{server.name} {probe.version}"
    row = f"{build} expired on {stopped}, as JetBrains' early-access builds do"
    return _Problem(row, f"expired on {stopped}", status=ServerStatus.EXPIRED)


def accept_license_command(license: License) -> str:
    """`cstudy doctor --fix --accept-license kotlin-lsp`."""
    return f"{FIX_COMMAND} {ACCEPT_LICENSE_OPTION} {license.key}"


def _license_problem(
    server: LanguageServer, locator: LanguageServerLocator, probe: ServerProbe
) -> _Problem | None:
    """None unless the server's vendor asks you to accept a license that the workspace's marker
    does not record as accepted: the one the fetched build came under, else the catalog's."""
    license = probe.license if isinstance(probe, Fetched) else server.license
    if license is None or locator.license_accepted(license):
        return None
    row = f"{server.name} needs you to accept the {license.name}"
    return _Problem(
        row,
        "license not accepted",
        status=ServerStatus.LICENSE_NOT_ACCEPTED,
        fix=accept_license_command(license),
    )


def _jdk_problem(server: LanguageServer, jdk: JdkSelector) -> _Problem | None:
    """None unless the server runs on a JDK and the selected one is outside its range, or there
    is none: cstudy never looks for another JDK (ADR 0016)."""
    wanted = server.jdks
    selected = jdk.selected()
    if wanted is None or (selected is not None and wanted.contains(selected.feature)):
        return None
    needs = f"needs {_either(wanted)}"
    if selected is None:
        found = f"; {no_jdk_sentence(jdk.unusable_java_home())}"
    else:
        found = f", not {selected.version}"
    row = f"{server.name} {needs}{found}"
    return _Problem(row, needs, own_words=True, status=ServerStatus.NEEDS_JDK, fix=jdk_fix(wanted))


def _either(wanted: JdkRange) -> str:
    """`JDK 25 or 26` for two releases, `JDK 21 to 26` for more."""
    if wanted.maximum == wanted.minimum + 1:
        return f"JDK {wanted.minimum} or {wanted.maximum}"
    return range_text(wanted)


def _missing(server: LanguageServer) -> str:
    requirement = server.requirement
    return requirement.missing if requirement else f"{server.name} is incomplete"


def _version_problem(
    server: LanguageServer, wanted: str | None, printed: str | None
) -> _Problem | None:
    fix = server.fix or FIX_COMMAND
    if printed is None:
        return _Problem(f"{server.name} printed no version", fix=fix)
    if wanted is not None and printed != wanted:
        return _Problem(f"{server.name} {printed} installed; cstudy needs {wanted}", fix=fix)
    return None
