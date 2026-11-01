"""What changed in the workspace, for the web UI's notifications
(docs/specs/web-ui.md#notifications).

A snapshot holds the SHA-256 of every file in the scope of each attempt in progress, of each
attempt's manifest and statement, and of progress.db and its write-ahead log, with the folders a
watch of them covers. Two snapshots give the changes between them by content, so a burst of
file-system events that changes nothing is no change, and neither is a snapshot's own read of
progress.db, which touches the database's files.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from coding_study.application.attempt_files import AttemptFolder, attempt_folder
from coding_study.application.environment import Environment
from coding_study.domain import layout
from coding_study.domain.attempts import Attempt
from coding_study.domain.errors import ContentError, UsageError
from coding_study.domain.project_manifest import MANIFESTS_DIRECTORY, manifest_path

WRITE_AHEAD_LOG = "-wal"
"""SQLite's suffix for the database's write-ahead log, which holds writes before they reach it."""


@dataclass(frozen=True, slots=True)
class WatchedFolder:
    path: str
    """Relative to the workspace root."""
    recursive: bool
    """Whether the folders under it are watched too."""
    names: frozenset[str] = frozenset()
    """The only entries of the folder that count; empty: every entry but the untracked ones
    (`workspace_projects.is_untracked`)."""


@dataclass(frozen=True, slots=True)
class WatchedAttempt:
    attempt: Attempt
    folder: AttemptFolder
    documents: str
    """The SHA-256 of the attempt's manifest and statement."""


@dataclass(frozen=True, slots=True)
class WorkspaceSnapshot:
    root: Path
    """The absolute workspace root, which the folders are relative to."""
    progress: str
    """The SHA-256 of progress.db and its write-ahead log."""
    attempts: tuple[WatchedAttempt, ...]
    """The attempts in progress, earliest start first."""
    folders: tuple[WatchedFolder, ...]
    """What a watch of them covers: only folders that exist, in path order."""


@dataclass(frozen=True, slots=True)
class FileChanged:
    """A file of an attempt's scope was written, created or deleted."""

    attempt_id: int
    path: str
    """Relative to the attempt's root."""
    sha256: str | None
    """Of the file's content now; None once it is gone."""


@dataclass(frozen=True, slots=True)
class AttemptChanged:
    """An attempt started, or its manifest or statement changed: a level opened, a restore."""

    attempt_id: int
    slug: str


@dataclass(frozen=True, slots=True)
class ProgressChanged:
    """progress.db changed: an attempt started, ended or recorded a run, a hint or a reveal."""


type WorkspaceChange = FileChanged | AttemptChanged | ProgressChanged


def workspace_snapshot(
    environment: Environment, previous: WorkspaceSnapshot | None = None
) -> WorkspaceSnapshot:
    """What the workspace holds now. While progress.db is as it was in `previous`, the attempts
    in progress are `previous`'s, so the snapshot reads the database only after a write."""
    progress = _progress_digest(environment)
    if previous is not None and previous.progress == progress:
        attempts = tuple(watched.attempt for watched in previous.attempts)
    else:
        attempts = environment.progress.attempts_in_progress()
    watched = tuple(
        found for attempt in attempts if (found := _watched(environment, attempt)) is not None
    )
    return WorkspaceSnapshot(environment.root, progress, watched, _folders(environment, watched))


def workspace_changes(
    before: WorkspaceSnapshot, after: WorkspaceSnapshot
) -> tuple[WorkspaceChange, ...]:
    """The files that changed, by attempt and path, then the attempts, then progress.db."""
    earlier = {watched.attempt.id: watched for watched in before.attempts}
    files: list[WorkspaceChange] = []
    attempts: list[WorkspaceChange] = []
    for now in after.attempts:
        then = earlier.get(now.attempt.id)
        if then is None or then.documents != now.documents:
            attempts.append(AttemptChanged(now.attempt.id, now.attempt.slug))
        if then is not None:
            files.extend(_file_changes(now.attempt.id, then.folder.digests, now.folder.digests))
    progress = [ProgressChanged()] if before.progress != after.progress else []
    return (*files, *attempts, *progress)


def _watched(environment: Environment, attempt: Attempt) -> WatchedAttempt | None:
    """None for an attempt whose problem no longer loads: its files are not watched."""
    try:
        folder = attempt_folder(environment, attempt)
    except (ContentError, LookupError, UsageError):
        return None
    workspace = environment.workspace
    documents = (manifest_path(attempt.slug), layout.statement_path(attempt.slug))
    return WatchedAttempt(attempt, folder, "".join(map(workspace.content_hash, documents)))


def _file_changes(
    attempt_id: int, then: Mapping[str, str], now: Mapping[str, str]
) -> list[FileChanged]:
    paths = sorted(then.keys() | now.keys())
    return [
        FileChanged(attempt_id, path, now.get(path))
        for path in paths
        if then.get(path) != now.get(path)
    ]


def _progress_files(environment: Environment) -> tuple[str, str]:
    database = environment.config.progress_db
    return database, f"{database}{WRITE_AHEAD_LOG}"


def _progress_digest(environment: Environment) -> str:
    return "".join(map(environment.workspace.content_hash, _progress_files(environment)))


def _folders(
    environment: Environment, watched: tuple[WatchedAttempt, ...]
) -> tuple[WatchedFolder, ...]:
    database, log = (PurePosixPath(path) for path in _progress_files(environment))
    folders = {
        *(WatchedFolder(found.folder.root, found.folder.recursive) for found in watched),
        WatchedFolder(MANIFESTS_DIRECTORY, False),
        WatchedFolder(layout.STATEMENTS_DIRECTORY, False),
        WatchedFolder(str(database.parent), False, frozenset({database.name, log.name})),
    }
    existing = (folder for folder in folders if environment.workspace.exists(folder.path))
    return tuple(sorted(existing, key=lambda folder: (folder.path, folder.recursive)))
