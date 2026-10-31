"""What `cstudy` provided in a project folder
(docs/specs/installation-and-workspaces.md#project-folders).

The manifest names each file `cstudy` put in `projects/<slug>/`, the starter's and the generated
test file of each open level, with the SHA-256 of the content it provided, so that each file of
the folder can be told unchanged, modified, added or deleted even after a newer `cstudy` changes
the starter or the generated tests. It lives in `.cs/projects/<slug>.json`, outside the folder,
next to the project's lock, which every command holds while it writes the folder's generated
files, its manifest or the attempt's levels.
"""

import hashlib
from dataclasses import dataclass
from enum import StrEnum

from coding_study.domain.project import PATH_SEPARATOR, ProjectTree

MANIFESTS_DIRECTORY = ".cs/projects"
_CURRENT_SEGMENT = "."
_PARENT_SEGMENT = ".."
_WINDOWS_SEPARATOR = "\\"
MANIFEST_SUFFIX = ".json"
LOCK_SUFFIX = ".lock"


class FileOrigin(StrEnum):
    """Where a file of a project folder comes from; a manifest records only the first two."""

    STARTER = "starter"
    LEVEL = "level"
    """The test file `cstudy` generates for one level."""
    YOURS = "yours"


@dataclass(frozen=True, slots=True)
class ProvidedFile:
    path: str
    """Relative to the folder."""
    digest: str
    """The SHA-256 of the content `cstudy` provided, in hex."""
    origin: FileOrigin
    level: int | None = None
    """The level of a generated test file; None for a starter file."""


@dataclass(frozen=True, slots=True)
class ProjectManifest:
    files: tuple[ProvidedFile, ...] = ()
    """One per path, in path order."""

    def file(self, path: str) -> ProvidedFile | None:
        return next((file for file in self.files if file.path == path), None)

    def with_file(self, provided: ProvidedFile) -> "ProjectManifest":
        """This manifest with `provided` in place of what it recorded for that path."""
        others = (file for file in self.files if file.path != provided.path)
        return ProjectManifest(tuple(sorted((*others, provided), key=_path)))


def content_digest(text: str) -> str:
    """The digest of `text` as `cstudy` writes it: UTF-8."""
    return hashlib.sha256(text.encode()).hexdigest()


def starter_manifest(starter: ProjectTree) -> ProjectManifest:
    """The starter's files as `cstudy start` copies them; a file that is not text is never copied
    (`project_workspace.seed_project` refuses the starter)."""
    provided = (
        ProvidedFile(file.path, content_digest(file.text), FileOrigin.STARTER)
        for file in starter.files
        if file.text is not None
    )
    return ProjectManifest(tuple(sorted(provided, key=_path)))


def level_file(path: str, text: str, level: int) -> ProvidedFile:
    """The generated test file of `level`, at `path` in the folder, as `text`."""
    return ProvidedFile(path, content_digest(text), FileOrigin.LEVEL, level)


def manifest_path(slug: str) -> str:
    """Relative to the workspace root."""
    return f"{MANIFESTS_DIRECTORY}/{slug}{MANIFEST_SUFFIX}"


def folder_path(path: str) -> str:
    """`path`, a file named relative to a project folder, without `.`, `..` and empty segments
    (`bank/../bank/bank.py` is `bank/bank.py`), as the manifest names it.

    Raises ValueError for an absolute path, a `\\` separator, a path that leaves the folder, or one
    that names the folder itself.
    """
    if path.startswith(PATH_SEPARATOR):
        raise ValueError("is absolute: name the file relative to the project folder")
    if _WINDOWS_SEPARATOR in path:
        raise ValueError(f"uses {_WINDOWS_SEPARATOR} instead of {PATH_SEPARATOR}")
    segments: list[str] = []
    for segment in path.split(PATH_SEPARATOR):
        if segment == _PARENT_SEGMENT:
            if not segments:
                raise ValueError("leaves the folder")
            segments.pop()
        elif segment not in ("", _CURRENT_SEGMENT):
            segments.append(segment)
    if not segments:
        raise ValueError("names no file in the folder")
    return PATH_SEPARATOR.join(segments)


def project_lock(slug: str) -> str:
    """The lock file of the project `slug`, relative to the workspace root."""
    return f"{MANIFESTS_DIRECTORY}/{slug}{LOCK_SUFFIX}"


def _path(file: ProvidedFile) -> str:
    return file.path
