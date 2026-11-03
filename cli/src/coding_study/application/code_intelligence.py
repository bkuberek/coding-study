"""The state of the language servers and their installation: the `code intelligence` rows of
`cstudy doctor`, `cstudy doctor --fix`, and `GET /api/v1/code-intelligence/languages`
(docs/specs/web-ui.md#language-servers).

Like highlighting, code intelligence grades nothing and records nothing.
"""

from dataclasses import dataclass
from enum import StrEnum

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
from coding_study.domain.code_intelligence import NOT_AVAILABLE_YET, LanguageServer, server_for
from coding_study.domain.problem import Language

FIX_HINT = "run cstudy doctor --fix"


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


def install_language_servers(installer: LanguageServerInstaller) -> ProbeResult | None:
    """Put the shipped manifest in `.cs/lsp/` and install it; None when `pnpm` is missing. The
    caller decides, from the `code_intelligence` preference, whether to."""
    return installer.install()


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
