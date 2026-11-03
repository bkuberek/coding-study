"""The files of an attempt that is over, which the web UI's History shows read-only
(docs/specs/web-ui.md#past-attempt-files).

The next start moves an attempt's files to `.archive/<slug>/<attempt_id>-<lang>/` (`-notes` for an
item), so that folder holds them. Without one, the latest attempt of a problem and language has
its files where it left them, and they may have been edited since it ended. Any other attempt
has none to show. Reads never follow a link and never leave the folder they read from.
"""

from dataclasses import dataclass
from enum import StrEnum

from coding_study.application.attempt_files import (
    TOOL_OUTPUT,
    FileContent,
    ScopedFile,
    attempt_tree,
    read_attempt_file,
)
from coding_study.application.environment import Environment
from coding_study.domain import layout
from coding_study.domain.attempts import Attempt, AttemptStatus
from coding_study.domain.errors import UnknownAttemptError, UnknownFileError, UsageError
from coding_study.domain.project import PATH_SEPARATOR
from coding_study.domain.project_manifest import FileOrigin, folder_path
from coding_study.domain.workspace_projects import is_untracked


class FilesSource(StrEnum):
    ARCHIVE = "archive"
    """The folder the next start moved the attempt's files to."""
    CURRENT = "current"
    """The files as they are now: the latest attempt's, edited since it ended perhaps."""
    MISSING = "missing"


@dataclass(frozen=True, slots=True)
class PastEntry:
    path: str
    """Relative to the files' root, `/`-separated."""
    size: int


@dataclass(frozen=True, slots=True)
class PastFiles:
    source: FilesSource
    root: str | None
    """Relative to the workspace root; None for `MISSING`."""
    entries: tuple[PastEntry, ...]
    """In path order."""


@dataclass(frozen=True, slots=True)
class PastFile:
    source: FilesSource
    content: FileContent


def past_attempt_files(environment: Environment, attempt_id: int) -> PastFiles:
    """Raises UnknownAttemptError for an id no attempt has, and UsageError for an attempt in
    progress, which the Attempt view shows."""
    attempt = _past_attempt(environment, attempt_id)
    root = _archive_root(environment, attempt)
    if root is not None:
        archived = PastFiles(FilesSource.ARCHIVE, root, _archived_entries(environment, root))
        if archived.entries:
            return archived
    if _is_latest(environment, attempt):
        current = _current(environment, attempt)
        if current.entries:
            return current
    return PastFiles(FilesSource.MISSING, None, ())


def read_past_file(environment: Environment, attempt_id: int, path: str) -> PastFile:
    """Raises UsageError for a path the rules refuse, and UnknownFileError for a file the
    attempt's files lack; otherwise as `past_attempt_files`."""
    attempt = _past_attempt(environment, attempt_id)
    root = _archive_root(environment, attempt)
    if root is not None:
        return PastFile(FilesSource.ARCHIVE, _read_archived(environment, root, path))
    if _is_latest(environment, attempt):
        return PastFile(FilesSource.CURRENT, read_attempt_file(environment, attempt, path))
    raise UnknownFileError(path, f"attempt {attempt.id}")


def _past_attempt(environment: Environment, attempt_id: int) -> Attempt:
    attempt = environment.progress.attempt(attempt_id)
    if attempt is None:
        raise UnknownAttemptError(attempt_id)
    if attempt.status is AttemptStatus.IN_PROGRESS:
        raise UsageError(
            f"attempt {attempt.id} of {attempt.slug} is in progress; open it in the Attempt view"
        )
    return attempt


def _is_latest(environment: Environment, attempt: Attempt) -> bool:
    latest = environment.progress.latest_attempt(attempt.slug, attempt.language)
    return latest is not None and latest.id == attempt.id


def _archive_root(environment: Environment, attempt: Attempt) -> str | None:
    """The attempt's archive folder when it holds files the attempt wrote."""
    directory = _archive_directory(attempt)
    if _archived_before(attempt, directory):
        return None
    return directory if environment.workspace.tracked_files(directory) else None


def _archive_directory(attempt: Attempt) -> str:
    if attempt.language is None:
        return layout.notes_archive_directory(attempt.slug, attempt.id)
    return layout.archive_directory(attempt.slug, attempt.id, attempt.language)


def _archived_before(attempt: Attempt, directory: str) -> bool:
    """Whether the attempt's own start moved the files into `directory`: a start that found files
    no attempt had written archives them under the id of the attempt it starts, whose work is
    the new files."""
    moved = attempt.archive_path
    return moved is not None and (
        moved == directory or moved.startswith(directory + PATH_SEPARATOR)
    )


def _archived_entries(environment: Environment, root: str) -> tuple[PastEntry, ...]:
    workspace = environment.workspace
    entries: list[PastEntry] = []
    for path in workspace.tracked_files(root):
        try:
            entries.append(PastEntry(path, len(workspace.read_within(root, path))))
        except (FileNotFoundError, ValueError):
            continue
    return tuple(entries)


def _read_archived(environment: Environment, root: str, path: str) -> FileContent:
    cleaned = _archived_path(path)
    try:
        content = environment.workspace.read_within(root, cleaned)
    except FileNotFoundError:
        raise UnknownFileError(cleaned, root) from None
    except ValueError as error:
        raise UsageError(f"cannot read {path}: {error}") from None
    return FileContent(ScopedFile(cleaned, FileOrigin.YOURS), content)


def _archived_path(path: str) -> str:
    """`path` without `.` and `..` segments; raises UsageError when it leaves the folder, is
    absolute or uses `\\`, or names what tools write."""
    try:
        cleaned = folder_path(path)
    except ValueError as error:
        raise UsageError(f"cannot read {path}: {error}") from None
    if is_untracked(cleaned):
        raise UsageError(f"cannot read {path}: {TOOL_OUTPUT}")
    return cleaned


def _current(environment: Environment, attempt: Attempt) -> PastFiles:
    tree = attempt_tree(environment, attempt)
    entries = tuple(PastEntry(file.path, file.size) for file in tree.files if file.size is not None)
    return PastFiles(FilesSource.CURRENT, tree.root, entries)
