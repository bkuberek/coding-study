"""`WorkspaceSetup` on the local filesystem: the template shipped in `workspace_template/` next to
this module, the marker, the runner runtime and `git init`
(docs/specs/installation-and-workspaces.md)."""

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
