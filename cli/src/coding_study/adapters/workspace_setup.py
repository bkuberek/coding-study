"""`WorkspaceSetup` on the local filesystem: the template shipped in `workspace_template/` next to
this module, the marker, the runner runtime and `git init`
(docs/specs/installation-and-workspaces.md); and `ProjectLinks`, the links from the Python project
folders to the workspace venv."""

import re
import subprocess
from collections.abc import Iterator
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path

from coding_study.adapters.locations import enclosing_content_checkout, enclosing_workspace
from coding_study.adapters.runner_runtime import RunnerRuntime
from coding_study.adapters.workspace_marker import (
    MARKER_FILE,
    SCHEMA_VERSION,
    WorkspaceMarker,
    marker_text,
)
from coding_study.application.ports import ScaffoldOutcome
from coding_study.domain.errors import VersionControlError
from coding_study.domain.layout import PYTHON_PROJECT, PYTHON_VENV
from coding_study.domain.problem import Language
from coding_study.domain.project_checks import PYPROJECT_FILE
from coding_study.domain.workspace_projects import PROJECTS_DIRECTORY, ToolchainLink, toolchain_link

TEMPLATE_PACKAGE = "coding_study.adapters"
TEMPLATE_DIRECTORY = "workspace_template"
IGNORED_DIRECTORIES = frozenset(
    {
        "__pycache__",
        ".ruff_cache",
        ".pytest_cache",
        ".venv",
        "node_modules",
        "build",
        ".gradle",
        ".kotlin",
    }
)
"""Caches and build output that tools may leave in a checkout's template; never copied."""
IGNORED_FILES = frozenset({".DS_Store"})
EXECUTABLE_FILES = frozenset({"jvm/gradlew"})
"""Wheels do not always keep the executable bit, so it is set on every write."""
EXECUTABLE_MODE = 0o755
GIT_INIT = ("git", "init", "--quiet")
VENV_SCRIPTS = "bin"
_SHEBANG = "#!"
_SHELL = "/bin/sh"
_TRAMPOLINE = re.compile(r"'''exec' '(?P<interpreter>[^']+)'")
"""The second line of uv's shell trampoline, `'''exec' '<interpreter>' "$0" "$@"`."""
_PYTHON_EXECUTABLE = "python"
_SCRIPT_HEAD_BYTES = 1024


def _python_link() -> ToolchainLink:
    link = toolchain_link(Language.PYTHON)
    assert link is not None
    return link


_PYTHON_LINK = _python_link()


class FsWorkspaceSetup:
    def __init__(self, runners: Path, version: str, template: Traversable | None = None) -> None:
        """`runners` is the content root's `runners/`; `version` goes into new markers;
        `template` defaults to the one shipped with this package."""
        self._runners = runners
        self._version = version
        self._template = template or resources.files(TEMPLATE_PACKAGE) / TEMPLATE_DIRECTORY

    def workspace_at_or_above(self, directory: Path) -> Path | None:
        return enclosing_workspace(directory)

    def checkout_at_or_above(self, directory: Path) -> Path | None:
        return enclosing_content_checkout(directory)

    def missing_files(self, root: Path) -> tuple[str, ...]:
        expected = (*(relative for relative, _ in self._template_files()), MARKER_FILE)
        return tuple(relative for relative in expected if not (root / relative).exists())

    def write_missing(self, root: Path) -> ScaffoldOutcome:
        written: list[str] = []
        kept: list[str] = []
        for relative, source in self._template_files():
            target = root / relative
            if target.exists():
                kept.append(relative)
                continue
            _write(target, source.read_bytes())
            if relative in EXECUTABLE_FILES:
                target.chmod(EXECUTABLE_MODE)
            written.append(relative)
        if not (root / MARKER_FILE).exists():
            marker = marker_text(WorkspaceMarker(SCHEMA_VERSION, self._version))
            _write(root / MARKER_FILE, marker.encode())
            written.append(MARKER_FILE)
        return ScaffoldOutcome(tuple(written), tuple(kept))

    def runtime_current(self, root: Path) -> bool:
        return RunnerRuntime(self._runners, root).is_current()

    def refresh_runtime(self, root: Path) -> None:
        RunnerRuntime(self._runners, root).ensure()

    def init_git(self, root: Path) -> None:
        try:
            completed = subprocess.run(
                GIT_INIT, cwd=root, capture_output=True, text=True, check=False
            )
        except FileNotFoundError:
            raise VersionControlError("git not found on PATH") from None
        if completed.returncode != 0:
            raise VersionControlError(f"git init failed: {completed.stderr.strip()}")

    def _template_files(self) -> list[tuple[str, Traversable]]:
        return sorted(_walk(self._template, ""), key=lambda entry: entry[0])


class FsProjectLinks:
    """`ProjectLinks` on the local filesystem: a Python project folder is a folder in
    `projects/` with a `pyproject.toml`, and its `.venv` the link `cstudy start` makes."""

    def unlinked(self, root: Path) -> tuple[str, ...]:
        link = _PYTHON_LINK.path
        return tuple(
            folder for folder in _python_folders(root) if not (root / folder / link).exists()
        )

    def relink(self, root: Path) -> tuple[str, ...]:
        unlinked = self.unlinked(root)
        for folder in unlinked:
            link = root / folder / _PYTHON_LINK.path
            if link.is_symlink():
                link.unlink()
            link.symlink_to(_PYTHON_LINK.target, target_is_directory=True)
        return unlinked

    def moved_venv(self, root: Path) -> str | None:
        venv = root / PYTHON_PROJECT / PYTHON_VENV
        named = _scripts_venv(venv / VENV_SCRIPTS)
        if named is None or named.resolve() == venv.resolve():
            return None
        return str(named)


def _python_folders(root: Path) -> list[str]:
    projects = root / PROJECTS_DIRECTORY
    if not projects.is_dir():
        return []
    return [
        f"{PROJECTS_DIRECTORY}/{folder.name}"
        for folder in sorted(projects.iterdir())
        if (folder / PYPROJECT_FILE).is_file()
    ]


def _scripts_venv(scripts: Path) -> Path | None:
    """The venv named by the interpreter in the first Python console script's shebang."""
    if not scripts.is_dir():
        return None
    interpreters = (_interpreter(script) for script in sorted(scripts.iterdir()))
    interpreter = next((found for found in interpreters if found is not None), None)
    return interpreter.parent.parent if interpreter is not None else None


def _interpreter(script: Path) -> Path | None:
    """A script's Python interpreter: from `#!<interpreter>`, or from the shell trampoline uv
    writes when that path is too long for a shebang. None for anything else."""
    if script.is_symlink() or not script.is_file():
        return None
    with script.open("rb") as handle:
        lines = handle.read(_SCRIPT_HEAD_BYTES).decode("utf-8", "replace").splitlines()
    if not lines or not lines[0].startswith(_SHEBANG):
        return None
    command = lines[0].removeprefix(_SHEBANG).strip()
    trampoline = _TRAMPOLINE.match(lines[1]) if command == _SHELL and len(lines) > 1 else None
    found = Path(trampoline["interpreter"] if trampoline else command.partition(" ")[0])
    return found if found.name.startswith(_PYTHON_EXECUTABLE) else None


def _walk(directory: Traversable, prefix: str) -> Iterator[tuple[str, Traversable]]:
    for entry in directory.iterdir():
        path = f"{prefix}{entry.name}"
        if entry.is_dir():
            if entry.name not in IGNORED_DIRECTORIES:
                yield from _walk(entry, f"{path}/")
        elif entry.name not in IGNORED_FILES:
            yield path, entry


def _write(target: Path, content: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
