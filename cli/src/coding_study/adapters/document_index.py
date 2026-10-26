"""The index cache in `.cs/index.json` (docs/architecture.md#cache-directory-cstudy).

It keeps the parsed and schema-validated YAML document of every content file a listing reads, so
`cstudy list`, `cstudy next` and `cstudy stats` skip parsing and validating hundreds of files. An
entry is trusted only while the file's modification time (ns) and size and the schema's are what
they were when it was stored; any other entry is a miss. The cache is best effort: an unreadable,
corrupt or unwritable index only costs the time of a cold read.
"""

import contextlib
import json
import os
from collections.abc import Callable, Collection
from pathlib import Path
from typing import Any, cast

from coding_study.domain.errors import ContentIssue

INDEX_FILE = ".cs/index.json"
FORMAT_VERSION = 2
"""2: keys are absolute paths, so the catalog and a workspace's own problems share one index."""

type Stamp = tuple[int, ...]


def index_key(path: Path) -> str:
    return path.absolute().as_posix()


def file_stamp(path: Path) -> Stamp | None:
    """Modification time in ns and size of `path`, or None when it cannot be read."""
    try:
        status = path.stat()
    except OSError:
        return None
    return (status.st_mtime_ns, status.st_size)


class DocumentIndex:
    """Validated documents by absolute path, shared by every repository of a command."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._entries: dict[str, dict[str, Any]] | None = None
        self._changed = False

    def validated(
        self,
        key: str,
        path: Path,
        schema: Stamp | None,
        read: Callable[[], tuple[Any, list[ContentIssue]]],
    ) -> tuple[Any, list[ContentIssue]]:
        """The stored document of `path` while neither it nor its schema (`schema` stamp) changed,
        else what `read` returns, which is stored when it has no issues. Content with issues is
        never stored, so every listing reports it again."""
        file = file_stamp(path)
        if file is None or schema is None:
            return read()
        stamp = (*file, *schema)
        document = self._lookup(key, stamp)
        if document is not None:
            return document, []
        document, issues = read()
        if not issues and document is not None:
            self._store(key, stamp, document)
        return document, issues

    def _store(self, key: str, stamp: Stamp, document: Any) -> None:
        self._loaded()[key] = {"stamp": list(stamp), "document": document}
        self._changed = True

    def _lookup(self, key: str, stamp: Stamp) -> Any | None:
        entry = self._loaded().get(key)
        if not isinstance(entry, dict) or tuple(entry.get("stamp", ())) != stamp:
            return None
        return entry.get("document")

    def retain(self, prefix: str, keys: Collection[str]) -> None:
        """Drop the entries under `prefix` whose file is no longer listed."""
        entries = self._loaded()
        gone = [key for key in entries if key.startswith(prefix) and key not in keys]
        for key in gone:
            del entries[key]
        self._changed = self._changed or bool(gone)

    def save(self) -> None:
        if not self._changed or self._entries is None:
            return
        document = {"version": FORMAT_VERSION, "entries": self._entries}
        temporary = self._path.with_name(f"{self._path.name}.{os.getpid()}.tmp")
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_text(json.dumps(document, separators=(",", ":")), encoding="utf-8")
            temporary.replace(self._path)
        except OSError:
            with contextlib.suppress(OSError):
                temporary.unlink(missing_ok=True)
            return
        self._changed = False

    def _loaded(self) -> dict[str, dict[str, Any]]:
        if self._entries is None:
            self._entries = self._read()
        return self._entries

    def _read(self) -> dict[str, dict[str, Any]]:
        try:
            document = json.loads(self._path.read_text(encoding="utf-8"))
            if document["version"] != FORMAT_VERSION:
                return {}
            entries: Any = document["entries"]
            if not isinstance(entries, dict):
                return {}
            return cast("dict[str, dict[str, Any]]", entries)
        except (OSError, ValueError, KeyError, TypeError):
            return {}
