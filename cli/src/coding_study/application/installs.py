"""The `cstudy` installs on `PATH`: how they are told apart, and what `cstudy doctor` says about
them (docs/specs/cli.md#cstudy-doctor).

An install is the Python environment that holds a `cstudy` console script. Which one runs is the
first on `PATH`; a second one is a trap, since fixing the copy that does not run changes nothing.
"""

import re
import shlex
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

DISTRIBUTION = "coding-study"
HOMEBREW_FORMULA = "cstudy"
HOMEBREW_CELLAR = "Cellar"
PIPX_VENVS = "venvs"
INSTALLS_CHECK = "installs"
GENERIC_REINSTALL = "reinstall cstudy"
INSTALLS_ROW_POINTER = "see the installs row"
DOCTOR_POINTER = "see cstudy doctor"
_NUMERIC_VERSION = re.compile(r"\d+(?:\.\d+)*")


class InstallKind(StrEnum):
    HOMEBREW = "Homebrew"
    UV_TOOL = "uv tool"
    PIPX = "pipx"
    OTHER = "other"
    """A virtual environment or a checkout."""


@dataclass(frozen=True, slots=True)
class Install:
    kind: InstallKind
    prefix: Path
    """The environment's directory, symlinks resolved: what tells two installs apart."""
    executable: Path | None
    """The `cstudy` as `PATH` lists it; None for a running install that is not on `PATH`."""
    version: str | None
    """From the install's own package metadata; None when it has none."""
    source: Path | None = None
    """The directory a uv tool was built from, as its receipt records it."""
    editable: bool = False


@dataclass(frozen=True, slots=True)
class InstallScan:
    on_path: tuple[Install, ...]
    """In `PATH` order, each install once."""
    running: Install
    """The install this `cstudy` runs from, found by the interpreter's own prefix."""
    home: Path
    """For showing `~` instead of the home directory."""


@dataclass(frozen=True, slots=True)
class InstallRoots:
    """Where uv and pipx keep their environments."""

    uv_tools: tuple[Path, ...]
    pipx_homes: tuple[Path, ...]


@dataclass(frozen=True, slots=True)
class InstallsAdvice:
    detail: str
    fix: str | None
    """Set when more than one install is on `PATH`."""


def classify_install(prefix: Path, roots: InstallRoots) -> InstallKind:
    """Homebrew keeps a formula in `<prefix>/Cellar/cstudy/<version>`; uv and pipx name the
    environment after the package."""
    parts = prefix.parts
    for index, part in enumerate(parts[:-1]):
        if part == HOMEBREW_CELLAR and parts[index + 1] == HOMEBREW_FORMULA:
            return InstallKind.HOMEBREW
    if any(prefix == tools / DISTRIBUTION for tools in roots.uv_tools):
        return InstallKind.UV_TOOL
    if any(prefix == home / PIPX_VENVS / DISTRIBUTION for home in roots.pipx_homes):
        return InstallKind.PIPX
    return InstallKind.OTHER


def installs_advice(scan: InstallScan) -> InstallsAdvice:
    installs = scan.on_path
    running = scan.running
    if not installs:
        return InstallsAdvice(
            f"none on PATH; this doctor is {_described(running, scan.home)}", None
        )
    if len(installs) == 1:
        return InstallsAdvice(
            _described(installs[0], scan.home) + _running_note(scan, installs[0]), None
        )
    first, *shadowed = installs
    parts = [f"{_described(first, scan.home)} runs first"]
    parts += [f"{_described(install, scan.home)} is shadowed" for install in shadowed]
    detail = f"{len(installs)} cstudy installs on PATH: {'; '.join(parts)}"
    return InstallsAdvice(detail + _running_note(scan, first), _removal_advice(installs))


def reinstall_command(scan: InstallScan, pointer: str = INSTALLS_ROW_POINTER) -> str:
    """The reinstall that repairs the install that runs, whichever others `PATH` holds; with
    several, it ends with a note that says where to look at them (`pointer`)."""
    command = _reinstall(scan.running)
    return f"{command} (several cstudy installs: {pointer})" if len(scan.on_path) > 1 else command


def _reinstall(install: Install) -> str:
    match install.kind:
        case InstallKind.HOMEBREW:
            return f"brew reinstall {HOMEBREW_FORMULA}"
        case InstallKind.UV_TOOL:
            return _uv_reinstall(install)
        case InstallKind.PIPX:
            return f"pipx reinstall {DISTRIBUTION}"
        case InstallKind.OTHER:
            return GENERIC_REINSTALL


def _uv_reinstall(install: Install) -> str:
    base = "uv tool install --reinstall"
    if install.source is None:
        return f"{base} {DISTRIBUTION}"
    editable = " --editable" if install.editable else ""
    return f"{base}{editable} {shlex.quote(str(install.source))}"


def _running_note(scan: InstallScan, first: Install) -> str:
    """The doctor's own install, when `PATH` does not start with it."""
    running = scan.running
    if running.prefix == first.prefix:
        return ""
    if any(running.prefix == install.prefix for install in scan.on_path):
        return f"; this doctor is {_name(running)}"
    return f"; this doctor is {_described(running, scan.home)}"


def _removal_advice(installs: tuple[Install, ...]) -> str:
    first = installs[0]
    keep = _newest(installs)
    if keep is first:
        lead = f"keep {_name(keep)}, which runs first"
    else:
        runs_first = _name(first) + (" runs first and is older" if first.version else " runs first")
        lead = f"keep {_name(keep)}, the newest ({runs_first})"
    removals = [_removal(install) for install in installs if install is not keep]
    return f"{lead}; uninstall the others: {'; '.join(dict.fromkeys(removals))}"


def _removal(install: Install) -> str:
    match install.kind:
        case InstallKind.HOMEBREW:
            return f"brew uninstall {HOMEBREW_FORMULA}"
        case InstallKind.UV_TOOL:
            return f"uv tool uninstall {DISTRIBUTION}"
        case InstallKind.PIPX:
            return f"pipx uninstall {DISTRIBUTION}"
        case InstallKind.OTHER:
            where = install.executable.parent if install.executable else install.prefix
            return f"remove {where} from PATH"


def _newest(installs: tuple[Install, ...]) -> Install:
    """The highest known version; of equal ones, and when none is known, the one that runs first."""
    newest = installs[0]
    for candidate in installs[1:]:
        if _is_newer(candidate, newest):
            newest = candidate
    return newest


def _is_newer(candidate: Install, other: Install) -> bool:
    mine, theirs = _version_key(candidate.version), _version_key(other.version)
    return mine is not None and (theirs is None or mine > theirs)


def _version_key(version: str | None) -> tuple[int, ...] | None:
    found = _NUMERIC_VERSION.match(version or "")
    return None if found is None else tuple(int(part) for part in found[0].split("."))


def _name(install: Install) -> str:
    return f"{install.kind} {install.version}" if install.version else str(install.kind)


def _described(install: Install, home: Path) -> str:
    name = _name(install) if install.version else f"{install.kind}, version unknown"
    return f"{name} ({_shown(install.executable or install.prefix, home)})"


def _shown(path: Path, home: Path) -> str:
    if path.is_relative_to(home):
        return str(Path("~") / path.relative_to(home))
    return str(path)
