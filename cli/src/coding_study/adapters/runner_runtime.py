"""The runner runtime: a workspace's own copy of the content's runners
(docs/specs/installation-and-workspaces.md#runner-runtime).

Gradle, uv and Node write next to what they build, and the runners bundled with `cstudy` live in the
installed package, which must stay read-only. Each workspace therefore builds against a copy in
`.cs/runtime/runners/`, kept in step with the content by a digest of the copied sources:
changed files are rewritten, removed ones deleted, unchanged ones keep their timestamps (Gradle's
up-to-date checks stay cheap) and build output in the copy survives. The runtime also holds the
IntelliJ open-file launcher (`adapters/ide/launcher.py`), so whatever restores the runtime on a
fresh clone restores the launcher too.
"""

import hashlib
import json
import os
from collections.abc import Iterator
from pathlib import Path
from typing import cast

from coding_study.adapters.ide.launcher import IdeLauncher
from coding_study.domain.errors import RunnerStartError

RUNTIME_DIRECTORY = ".cs/runtime"
RUNTIME_RUNNERS = f"{RUNTIME_DIRECTORY}/runners"
STAMP_FILE = f"{RUNTIME_DIRECTORY}/stamp.json"
STAMP_FORMAT = 1
RUNNER_NAMES = ("python", "typescript", "jvm", "go")
"""The runners a workspace builds against; `conformance/` is content, read in place."""
SKIPPED_DIRECTORIES = frozenset(
    {
        "tests",
        "node_modules",
        "build",
        ".gradle",
        ".kotlin",
        ".venv",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
    }
)
"""Never copied from the content, and never deleted from the copy."""


class RunnerRuntime:
    def __init__(self, runners: Path, workspace: Path) -> None:
        """`runners` is the content root's `runners/`, `workspace` the workspace root."""
        self._runners = runners
        self._workspace = workspace
        self._launcher = IdeLauncher(workspace / RUNTIME_DIRECTORY)

    @property
    def directory(self) -> Path:
        return self._workspace / RUNTIME_RUNNERS

    def is_current(self) -> bool:
        return self._stamp() == self._digest(self._sources()) and self._launcher.is_current()

    def ensure(self) -> Path:
        """Brings the copy and the IDE launcher in step with the content; returns the copy's
        directory."""
        sources = self._sources()
        digest = self._digest(sources)
        self._launcher.install()
        if self._stamp() == digest:
            return self.directory
        for relative, source in sources.items():
            _copy_if_changed(source, self.directory / relative)
        for relative, path in _files(self.directory):
            if relative not in sources:
                path.unlink()
        stamp = self._workspace / STAMP_FILE
        stamp.write_text(json.dumps({"format": STAMP_FORMAT, "digest": digest}) + "\n")
        return self.directory

    def _sources(self) -> dict[str, Path]:
        if not self._runners.is_dir():
            raise RunnerStartError(f"the content has no runners directory: {self._runners}")
        return dict(
            item for name in RUNNER_NAMES for item in _files(self._runners / name, f"{name}/")
        )

    def _digest(self, sources: dict[str, Path]) -> str:
        digest = hashlib.sha256()
        for relative in sorted(sources):
            digest.update(relative.encode())
            digest.update(b"\0")
            digest.update(sources[relative].read_bytes())
        return digest.hexdigest()

    def _stamp(self) -> str | None:
        try:
            document: object = json.loads(
                (self._workspace / STAMP_FILE).read_text(encoding="utf-8")
            )
        except (OSError, ValueError):
            return None
        if not isinstance(document, dict):
            return None
        stamp = cast("dict[str, object]", document)
        digest = stamp.get("digest")
        if stamp.get("format") != STAMP_FORMAT or not isinstance(digest, str):
            return None
        return digest


def _files(directory: Path, prefix: str = "") -> Iterator[tuple[str, Path]]:
    """(relative POSIX path, path) of every file below `directory`, skipping build output."""
    for current, subdirectories, names in os.walk(directory):
        subdirectories[:] = sorted(
            name for name in subdirectories if name not in SKIPPED_DIRECTORIES
        )
        base = Path(current)
        for name in sorted(names):
            path = base / name
            yield f"{prefix}{path.relative_to(directory).as_posix()}", path


def _copy_if_changed(source: Path, target: Path) -> None:
    content = source.read_bytes()
    if target.is_file() and target.read_bytes() == content:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)
