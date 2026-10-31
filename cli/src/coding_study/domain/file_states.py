"""The state of each file of a project folder against what `cstudy` provided
(docs/specs/cli.md#cstudy-status).

A file the manifest records, a starter file or a generated test file, is unchanged while its
content is what `cstudy` provided, modified once it differs, and deleted when the folder lacks it.
Any other file of the folder is yours, added. `cstudy status` counts the starter's files changed
and removed and yours added; every file keeps its own state for an interface that shows the tree.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum

from coding_study.domain.project_manifest import FileOrigin, ProjectManifest, ProvidedFile


class FileState(StrEnum):
    UNCHANGED = "unchanged"
    MODIFIED = "modified"
    ADDED = "added"
    DELETED = "deleted"


@dataclass(frozen=True, slots=True)
class FolderFile:
    path: str
    """Relative to the folder."""
    origin: FileOrigin
    state: FileState
    level: int | None = None
    """The level of a generated test file; None for any other file."""


@dataclass(frozen=True, slots=True)
class StarterChanges:
    """The folder against the starter, each in path order; generated test files aside."""

    changed: tuple[str, ...]
    added: tuple[str, ...]
    removed: tuple[str, ...]


def folder_files(manifest: ProjectManifest, digests: Mapping[str, str]) -> tuple[FolderFile, ...]:
    """Every file of the folder, given as the digest of its content by path, and every file the
    manifest records that the folder lacks, in path order."""
    provided = {file.path: file for file in manifest.files}
    paths = sorted(provided.keys() | digests.keys())
    return tuple(_folder_file(path, provided.get(path), digests.get(path)) for path in paths)


def starter_changes(files: Iterable[FolderFile]) -> StarterChanges:
    starter = [file for file in files if file.origin is not FileOrigin.LEVEL]
    return StarterChanges(
        changed=_paths(starter, FileState.MODIFIED),
        added=_paths(starter, FileState.ADDED),
        removed=_paths(starter, FileState.DELETED),
    )


def _folder_file(path: str, provided: ProvidedFile | None, digest: str | None) -> FolderFile:
    if provided is None:
        return FolderFile(path, FileOrigin.YOURS, FileState.ADDED)
    return FolderFile(path, provided.origin, _state(provided.digest, digest), provided.level)


def _state(provided: str, digest: str | None) -> FileState:
    if digest is None:
        return FileState.DELETED
    return FileState.UNCHANGED if digest == provided else FileState.MODIFIED


def _paths(files: Iterable[FolderFile], state: FileState) -> tuple[str, ...]:
    return tuple(file.path for file in files if file.state is state)
