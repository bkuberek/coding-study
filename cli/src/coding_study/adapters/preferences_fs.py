"""`.cs/serve/preferences.json` in the workspace (docs/specs/web-ui.md#preferences)."""

import contextlib
import json
import os
from pathlib import Path

SERVE_DIRECTORY = ".cs/serve"
"""The web UI's files in the workspace: the preferences and the `--open` redirect file."""
PREFERENCES_FILE = f"{SERVE_DIRECTORY}/preferences.json"


class FsPreferencesStore:
    def __init__(self, workspace: Path) -> None:
        self._path = workspace / PREFERENCES_FILE

    def read(self) -> object:
        try:
            return json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return None

    def write(self, document: dict[str, object]) -> None:
        """Atomic: a temporary file beside it, then a rename."""
        temporary = self._path.with_name(f"{self._path.name}.{os.getpid()}.tmp")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            temporary.write_text(json.dumps(document) + "\n", encoding="utf-8")
            temporary.replace(self._path)
        finally:
            with contextlib.suppress(OSError):
                temporary.unlink(missing_ok=True)
