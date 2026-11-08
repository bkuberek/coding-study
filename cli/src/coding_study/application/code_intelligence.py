"""The state of the language servers and their installation: the `code intelligence` rows of
`cstudy doctor`, `cstudy doctor --fix`, and `GET /api/v1/code-intelligence/languages`
(docs/specs/web-ui.md#language-servers); and which server and root a session gets from an
attempt (docs/specs/web-ui.md#sessions).

Like highlighting, code intelligence grades nothing and records nothing.
"""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from coding_study.application.active_attempt import attempt_in_progress
from coding_study.application.environment import Environment
from coding_study.application.ports import (
    FileMissing,
    JdkSelector,
    LanguageServerInstaller,
    LanguageServerLocator,
    NotInstalled,
    ProbeResult,
    ServerProbe,
    Unpacked,
    VersionFailed,
    VersionPrinted,
)
from coding_study.domain.attempts import Attempt
from coding_study.domain.code_intelligence import (
    LSP_DIRECTORY,
    NOT_AVAILABLE_YET,
    LanguageServer,
    License,
    no_code_intelligence,
    server_for,
)
from coding_study.domain.errors import LanguageServerNotInstalledError, UsageError
from coding_study.domain.jdk import JdkRange, jdk_fix, no_jdk_sentence, range_text
from coding_study.domain.layout import BUILD_DIRECTORY, CASES_DIRECTORY, RUNS_DIRECTORY
from coding_study.domain.preferences import Preferences
from coding_study.domain.problem import Language, ProblemKind
from coding_study.domain.workspace_projects import project_folder

FIX_COMMAND = "cstudy doctor --fix"
ACCEPT_LICENSE_OPTION = "--accept-license"
OFF = "code intelligence is off: turn it on in Settings"


class ServerStatus(StrEnum):
    INSTALLED = "installed"
    NOT_INSTALLED = "not_installed"
    NEEDS_JDK = "needs_jdk"
    """Installed, but the selected JDK is not one the server runs on."""
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


def language_server_states(
    locator: LanguageServerLocator, jdk: JdkSelector
) -> tuple[LanguageServerState, ...]:
    """One state per language, in `cstudy list`'s order, whatever the preference says; a server
    that runs on a JDK is judged against the selected one, and one that Go builds against the
    version the selected Go pins."""
    return tuple(_state(language, locator, jdk) for language in Language)


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
    has no code, its language has no server yet, it is a service project) and
    LanguageServerNotInstalledError (the server is missing, or the selected JDK cannot run it).
    """
    attempt = attempt_in_progress(environment.progress, attempt_id)
    if not preferences.code_intelligence:
        raise UsageError(OFF)
    server = _server_of(environment, attempt)
    jdk = environment.jdk
    state = _located(server, environment.language_servers, jdk)
    if state.problem is not None:
        raise LanguageServerNotInstalledError(state.problem, state.fix or FIX_COMMAND)
    root = _root(environment, attempt, server)
    java_home = jdk.selected_home() if server.jdks is not None else None
    return SessionTarget(server, environment.root, root, environment.content_root, java_home)


def install_language_servers(installer: LanguageServerInstaller) -> ProbeResult | None:
    """Put the shipped manifest in `.cs/lsp/` and install it; None when `pnpm` is missing. The
    caller decides, from the `code_intelligence` preference, whether to."""
    return installer.install()


def is_unpacked(locator: LanguageServerLocator, server: LanguageServer) -> bool:
    """Whether the pinned build of an archive server is in `.cs/lsp/` already."""
    return isinstance(locator.probe(server), Unpacked)


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
    archive = server.archive_on(installer.machine)
    return None if archive is None else installer.download(archive)


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


def _server_of(environment: Environment, attempt: Attempt) -> LanguageServer:
    """A service project's folder is written by sandboxed code, and a server on this machine would
    read it, so it has none until P9 runs one in a sidecar
    (docs/specs/service-projects.md#language-servers)."""
    if attempt.language is None:
        raise UsageError(f"{attempt.slug} has no code")
    server = server_for(attempt.language)
    if server is None or no_code_intelligence(environment.problems.load(attempt.slug).meta):
        raise UsageError(f"no code intelligence for {attempt.language.value} yet")
    return server


def _root(environment: Environment, attempt: Attempt, server: LanguageServer) -> str:
    if environment.problems.load(attempt.slug).meta.kind is ProblemKind.PROJECT:
        return project_folder(attempt.slug)
    return server.root_project


def _state(
    language: Language, locator: LanguageServerLocator, jdk: JdkSelector
) -> LanguageServerState:
    server = server_for(language)
    if server is None:
        return LanguageServerState(
            language, None, None, ServerStatus.NOT_AVAILABLE, NOT_AVAILABLE_YET, None, None, None
        )
    return _located(server, locator, jdk)


def _located(
    server: LanguageServer, locator: LanguageServerLocator, jdk: JdkSelector
) -> LanguageServerState:
    wanted = _pinned(server, locator)
    probe = locator.probe(server)
    problem = (
        _license_problem(server, locator)
        or _problem(server, wanted, probe)
        or _jdk_problem(server, jdk)
    )
    version = wanted or _printed(server, probe)
    if problem is None:
        return _state_of(server, version, f"{server.name} {version}", None)
    detail = problem.reason if problem.own_words else f"{problem.reason}: run {problem.fix}"
    return _state_of(server, version, detail, problem)


def _pinned(server: LanguageServer, locator: LanguageServerLocator) -> str | None:
    """The version cstudy needs: the catalog's, or for a server that Go builds the one the
    selected Go pins; None for a server cstudy does not pin."""
    if server.go_install is None:
        return server.version
    return server.go_install.version_for(locator.go_release())


def _printed(server: LanguageServer, probe: ServerProbe) -> str | None:
    return server.printed_version(probe.output) if isinstance(probe, VersionPrinted) else None


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
        case Unpacked():
            return None


def accept_license_command(license: License) -> str:
    """`cstudy doctor --fix --accept-license kotlin-lsp`."""
    return f"{FIX_COMMAND} {ACCEPT_LICENSE_OPTION} {license.key}"


def _license_problem(server: LanguageServer, locator: LanguageServerLocator) -> _Problem | None:
    """None unless the server's vendor asks you to accept a license that the workspace's marker
    does not record as accepted."""
    license = server.license
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
