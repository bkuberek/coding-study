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
    LanguageServerInstaller,
    LanguageServerLocator,
    NotInstalled,
    ProbeResult,
    ServerProbe,
    VersionFailed,
    VersionPrinted,
)
from coding_study.domain.attempts import Attempt
from coding_study.domain.code_intelligence import (
    LSP_DIRECTORY,
    NOT_AVAILABLE_YET,
    LanguageServer,
    no_code_intelligence,
    server_for,
)
from coding_study.domain.errors import LanguageServerNotInstalledError, UsageError
from coding_study.domain.layout import BUILD_DIRECTORY, CASES_DIRECTORY, RUNS_DIRECTORY
from coding_study.domain.preferences import Preferences
from coding_study.domain.problem import Language, ProblemKind
from coding_study.domain.workspace_projects import project_folder

FIX_COMMAND = "cstudy doctor --fix"
FIX_HINT = f"run {FIX_COMMAND}"
OFF = "code intelligence is off: turn it on in Settings"


class ServerStatus(StrEnum):
    INSTALLED = "installed"
    NOT_INSTALLED = "not_installed"
    NOT_AVAILABLE = "not_available"


@dataclass(frozen=True, slots=True)
class LanguageServerState:
    language: Language
    server: str | None
    """None where the language has no server yet."""
    version: str | None
    """The pinned version, whether or not it is installed."""
    status: ServerStatus
    detail: str
    """What the Settings view shows: the installed version, or why the server is not usable,
    ending in the fix unless the reason is the version command's own words."""
    idle_s: int | None
    problem: str | None
    """Why an unusable server is not usable, as the doctor row says it, without the fix; None
    unless the status is `not_installed`."""


def language_server_states(locator: LanguageServerLocator) -> tuple[LanguageServerState, ...]:
    """One state per language, in `cstudy list`'s order, whatever the preference says."""
    return tuple(_state(language, locator) for language in Language)


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

    @property
    def directory(self) -> Path:
        """The server's current directory."""
        return self.workspace / self.root

    @property
    def lsp_directory(self) -> Path:
        return self.workspace / LSP_DIRECTORY

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
    LanguageServerNotInstalledError.
    """
    attempt = attempt_in_progress(environment.progress, attempt_id)
    if not preferences.code_intelligence:
        raise UsageError(OFF)
    server = _server_of(environment, attempt)
    problem = _located(server, environment.language_servers.probe(server)).problem
    if problem is not None:
        raise LanguageServerNotInstalledError(problem, FIX_COMMAND)
    root = _root(environment, attempt, server)
    return SessionTarget(server, environment.root, root, environment.content_root)


def install_language_servers(installer: LanguageServerInstaller) -> ProbeResult | None:
    """Put the shipped manifest in `.cs/lsp/` and install it; None when `pnpm` is missing. The
    caller decides, from the `code_intelligence` preference, whether to."""
    return installer.install()


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


def _state(language: Language, locator: LanguageServerLocator) -> LanguageServerState:
    server = server_for(language)
    if server is None:
        return LanguageServerState(
            language, None, None, ServerStatus.NOT_AVAILABLE, NOT_AVAILABLE_YET, None, None
        )
    return _located(server, locator.probe(server))


def _located(server: LanguageServer, probe: ServerProbe) -> LanguageServerState:
    problem = _problem(server, probe)
    if problem is None:
        detail = f"{server.name} {server.version}"
        return _state_of(server, ServerStatus.INSTALLED, detail, None)
    detail = problem.reason if problem.own_words else f"{problem.reason}: {FIX_HINT}"
    return _state_of(server, ServerStatus.NOT_INSTALLED, detail, problem.row)


def _state_of(
    server: LanguageServer, status: ServerStatus, detail: str, problem: str | None
) -> LanguageServerState:
    return LanguageServerState(
        server.language, server.name, server.version, status, detail, server.idle_s, problem
    )


@dataclass(frozen=True, slots=True)
class _Problem:
    row: str
    """As the doctor row says it, after the server's name."""
    reason: str = ""
    """As the Settings view says it; the row's words unless given."""
    own_words: bool = False
    """The version command's own line, which needs no fix hint after it."""

    def __post_init__(self) -> None:
        if not self.reason:
            object.__setattr__(self, "reason", self.row)


def _problem(server: LanguageServer, probe: ServerProbe) -> _Problem | None:
    """None when the pinned version is installed and usable."""
    match probe:
        case NotInstalled():
            return _Problem(f"{server.name} is not installed", "not installed")
        case FileMissing():
            return _Problem(_missing(server))
        case VersionFailed(reason):
            return _Problem(reason, own_words=True)
        case VersionPrinted(output):
            return _version_problem(server, server.printed_version(output))


def _missing(server: LanguageServer) -> str:
    requirement = server.requirement
    return requirement.missing if requirement else f"{server.name} is incomplete"


def _version_problem(server: LanguageServer, printed: str | None) -> _Problem | None:
    if printed is None:
        return _Problem(f"{server.name} printed no version")
    if printed != server.version:
        return _Problem(f"{server.name} {printed} installed; cstudy needs {server.version}")
    return None
