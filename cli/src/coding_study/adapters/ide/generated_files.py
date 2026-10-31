"""Generated IDE files in a workspace and their manifest
(docs/specs/installation-and-workspaces.md#ide-files).

The manifest, `.cs/ide.json`, maps each file cstudy wrote to the SHA-256 of what it wrote. The
workspace `.gitignore` keeps it tracked with the IDE files, so a clone knows which of them are
still as cstudy wrote them.
"""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from coding_study.domain.ide import content_digest
from coding_study.domain.workspace_projects import CARGO_MANIFEST, PROJECTS_DIRECTORY

MANIFEST_FILE = ".cs/ide.json"
MANIFEST_FORMAT = 1
INDENT = 2


class FsGeneratedFiles:
    def __init__(self, root: Path) -> None:
        """`root` is the workspace root; every path is relative to it."""
        self._root = root

    def digest(self, path: str) -> str | None:
        target = self._root / path
        return content_digest(target.read_bytes()) if target.is_file() else None

    def write(self, path: str, content: str) -> None:
        target = self._root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content.encode())

    def remove(self, path: str) -> None:
        (self._root / path).unlink(missing_ok=True)

    def manifest(self) -> dict[str, str]:
        """The recorded digests by path; nothing when the manifest is missing or unreadable."""
        try:
            document: object = json.loads((self._root / MANIFEST_FILE).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        if not isinstance(document, dict):
            return {}
        manifest = cast("dict[str, object]", document)
        files = manifest.get("files")
        if manifest.get("format") != MANIFEST_FORMAT or not isinstance(files, dict):
            return {}
        entries = cast("dict[object, object]", files)
        return {
            path: digest
            for path, digest in entries.items()
            if isinstance(path, str) and isinstance(digest, str)
        }

    def save_manifest(self, manifest: Mapping[str, str]) -> None:
        document = {"format": MANIFEST_FORMAT, "files": dict(sorted(manifest.items()))}
        self.write(MANIFEST_FILE, json.dumps(document, indent=INDENT) + "\n")

    def rust_projects(self) -> tuple[str, ...]:
        projects = self._root / PROJECTS_DIRECTORY
        if not projects.is_dir():
            return ()
        return tuple(
            f"{PROJECTS_DIRECTORY}/{folder.name}/{CARGO_MANIFEST}"
            for folder in sorted(projects.iterdir())
            if (folder / CARGO_MANIFEST).is_file()
        )
