"""Snapshots of the public surfaces (docs/specs/compatibility.md#snapshots).

A surface is a flat mapping from the name of an entry to its value. A snapshot is that mapping as
JSON, written with sorted keys and two-space indentation so a change reads as a short diff.
"""

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

type Surface = Mapping[str, object]

SNAPSHOT_DIRECTORY = Path(__file__).parent / "snapshots"
WRITE_VARIABLE = "CSTUDY_WRITE_SNAPSHOTS"
"""When set to 1, the contract tests write the snapshots from the live surfaces."""
REGENERATE_HINT = (
    "If the change is intended, accept it with "
    f"`{WRITE_VARIABLE}=1 uv run pytest -q tests/contract`."
)


@dataclass(frozen=True, slots=True)
class SurfaceDiff:
    removed: tuple[str, ...]
    """In the snapshot, not in the live surface: breaking."""
    changed: tuple[str, ...]
    """In both, with another value: breaking."""
    added: tuple[str, ...]
    """In the live surface, not in the snapshot: additive."""

    @property
    def empty(self) -> bool:
        return not (self.removed or self.changed or self.added)


def diff_surfaces(snapshot: Surface, live: Surface) -> SurfaceDiff:
    return SurfaceDiff(
        removed=tuple(sorted(snapshot.keys() - live.keys())),
        changed=tuple(
            sorted(name for name in snapshot.keys() & live.keys() if snapshot[name] != live[name])
        ),
        added=tuple(sorted(live.keys() - snapshot.keys())),
    )


def report(diff: SurfaceDiff, snapshot: Surface, live: Surface) -> str:
    """The three lists apart, each entry with what changed, and how to accept the change."""
    lines: list[str] = []
    for title, names in (
        ("removed", diff.removed),
        ("changed", diff.changed),
        ("added", diff.added),
    ):
        lines.append(f"{title} ({len(names)}):")
        for name in names:
            if title == "changed":
                lines.append(f"  {name}: {_text(snapshot[name])} -> {_text(live[name])}")
            else:
                lines.append(
                    f"  {name}: {_text(snapshot[name] if title == 'removed' else live[name])}"
                )
    return "\n".join([*lines, REGENERATE_HINT])


def snapshot_text(surface: Surface) -> str:
    return json.dumps(surface, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def writing_snapshots(environ: Mapping[str, str] = os.environ) -> bool:
    return environ.get(WRITE_VARIABLE) == "1"


def read_snapshot(path: Path) -> Surface:
    loaded: Surface = json.loads(path.read_text(encoding="utf-8"))
    return loaded


def check_snapshot(name: str, live: Surface, directory: Path = SNAPSHOT_DIRECTORY) -> None:
    """Fails with the removed, changed and added entries when `live` is not what `directory/name`
    holds; writes the file instead when snapshots are being written."""
    path = directory / name
    if writing_snapshots():
        directory.mkdir(parents=True, exist_ok=True)
        path.write_text(snapshot_text(live), encoding="utf-8")
        return
    assert path.is_file(), f"{path} is missing. {REGENERATE_HINT}"
    snapshot = read_snapshot(path)
    diff = diff_surfaces(snapshot, live)
    assert diff.empty, f"{name} differs from the live surface:\n{report(diff, snapshot, live)}"
    assert path.read_text(encoding="utf-8") == snapshot_text(live), (
        f"{path} is not in its stable form. {REGENERATE_HINT}"
    )


def _text(value: object) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False)
