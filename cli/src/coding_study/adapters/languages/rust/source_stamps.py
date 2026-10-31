"""Sources that Cargo would take for unchanged (docs/specs/runners.md#rust-projects).

Cargo decides that a crate is up to date by comparing the modification times of its sources with
those of its last build. A source replaced by a copy that keeps an older time (`rsync -a`,
`cp -p`, a checkout that restores times) looks unchanged, and the tests would run the code of the
build before. Each build therefore records a digest of every source, and touches the ones whose
digest differs from the last build's, before Cargo looks.
"""

import hashlib
import json
import os
from collections.abc import Iterable, Iterator
from contextlib import suppress
from pathlib import Path
from typing import cast

SOURCE_SUFFIX = ".rs"
MANIFESTS = frozenset({"Cargo.toml", "Cargo.lock"})
SKIPPED_DIRECTORY = "target"
HIDDEN_PREFIX = "."


def project_sources(root: Path) -> list[Path]:
    """The Rust files and manifests under `root`, without its build output (`target`) and its
    hidden folders."""
    return list(_walk(root))


def _walk(directory: Path) -> Iterator[Path]:
    for current, folders, files in os.walk(directory):
        folders[:] = [
            name
            for name in folders
            if name != SKIPPED_DIRECTORY and not name.startswith(HIDDEN_PREFIX)
        ]
        for name in files:
            if name.endswith(SOURCE_SUFFIX) or name in MANIFESTS:
                yield Path(current, name)


def touch_replaced_sources(sources: Iterable[Path], record: Path) -> None:
    """Touches each of `sources` that is new, or whose content differs from the digest in
    `record`, then stores the digests. Nothing is touched when `record` is missing or unreadable:
    that is the first build, which has no earlier one to be stale against. Files that cannot be
    read or touched are left as they are."""
    digests = {str(path): digest for path in sources if (digest := _digest(path)) is not None}
    recorded = _read(record)
    if recorded is not None:
        for path, digest in digests.items():
            if recorded.get(path) != digest:
                with suppress(OSError):
                    os.utime(path)
    _write(record, digests)


def _digest(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _read(record: Path) -> dict[str, str] | None:
    try:
        stored: object = json.loads(record.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(stored, dict):
        return None
    digests = cast("dict[str, object]", stored)
    if not all(isinstance(digest, str) for digest in digests.values()):
        return None
    return cast("dict[str, str]", digests)


def _write(record: Path, digests: dict[str, str]) -> None:
    with suppress(OSError):
        record.parent.mkdir(parents=True, exist_ok=True)
        record.write_text(json.dumps(digests), encoding="utf-8")
