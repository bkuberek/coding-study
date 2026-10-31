"""What `cstudy serve` needs from the installation: the page's built files as
`static/manifest.json` records them, and the web server libraries
(docs/specs/installation-and-workspaces.md#web-ui-assets).

The libraries are imported by name: this module, like every adapter, never uses them.
"""

import hashlib
import json
from importlib import import_module, metadata
from pathlib import Path
from typing import cast

from coding_study.application.ports import WebServerLibraries, WebUiAssets

MANIFEST_FILE = "manifest.json"
SERVER_LIBRARIES = ("starlette", "uvicorn")


class InstalledWebUi:
    def __init__(self, static_directory: Path) -> None:
        self._directory = static_directory

    def assets(self) -> WebUiAssets:
        manifest = self._directory / MANIFEST_FILE
        if not manifest.is_file():
            return WebUiAssets(0, f"missing {MANIFEST_FILE}")
        digests = _digests(manifest)
        if digests is None:
            return WebUiAssets(0, f"unreadable {MANIFEST_FILE}")
        size = 0
        for path, expected in sorted(digests.items()):
            try:
                content = (self._directory / path).read_bytes()
            except OSError:
                return WebUiAssets(size, f"missing {path}")
            if hashlib.sha256(content).hexdigest() != expected:
                return WebUiAssets(size, f"{path} does not match {MANIFEST_FILE}")
            size += len(content)
        return WebUiAssets(size)

    def server_libraries(self) -> WebServerLibraries:
        versions: list[str] = []
        for name in SERVER_LIBRARIES:
            try:
                import_module(name)
            except ImportError as error:
                return WebServerLibraries(tuple(versions), f"{name} does not import: {error}")
            versions.append(f"{name} {metadata.version(name)}")
        return WebServerLibraries(tuple(versions))


def _digests(manifest: Path) -> dict[str, str] | None:
    """The manifest's `files`, each path relative to it with its SHA-256; None when the file is
    not such a manifest."""
    try:
        document: object = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(document, dict):
        return None
    files = cast(dict[str, object], document).get("files")
    if not isinstance(files, dict):
        return None
    digests = cast(dict[object, object], files)
    if not all(isinstance(key, str) and isinstance(value, str) for key, value in digests.items()):
        return None
    return cast(dict[str, str], digests)
