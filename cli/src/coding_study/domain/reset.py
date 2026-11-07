"""What `cstudy reset` says and asks (docs/specs/cli.md#cstudy-reset): the word that confirms it,
the shape of its preview, and what it keeps."""

from dataclasses import dataclass
from enum import StrEnum

RESET_WORD = "reset"
RESET_WARNING = "This can't be undone."
KEPT = (
    "config.toml and .cs/serve/preferences.json",
    "toolchains and language servers: .venv, node_modules, .cs/runtime, .cs/lsp",
    "the marker .cs/workspace.toml and your IDE files",
    "your own problems in problems/",
    "your problem sets: sets.yaml",
    "backups: progress-export.json",
    "caches that hold no progress: .cs/build, .cs/cases, .cs/calibration, the index",
)


class ResetOption(StrEnum):
    """What a reset deletes only when asked to."""

    FILES = "files"
    ARCHIVE = "archive"


@dataclass(frozen=True, slots=True)
class ResetEntry:
    label: str
    count: int


@dataclass(frozen=True, slots=True)
class ResetGroup:
    option: ResetOption | None
    """None: deleted by every reset."""
    title: str
    entries: tuple[ResetEntry, ...]


@dataclass(frozen=True, slots=True)
class ResetPreview:
    groups: tuple[ResetGroup, ...]
    kept: tuple[str, ...]
    busy: str | None
    """Why a reset would be refused now: a run or a job is active."""
