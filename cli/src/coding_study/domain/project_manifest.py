"""What `cstudy` provided in a project folder
(docs/specs/installation-and-workspaces.md#project-folders).

The manifest names each file `cstudy` put in `projects/<slug>/`, the starter's and the generated
test file of each open level, with the SHA-256 of the content it provided, so that each file of
the folder can be told unchanged, modified, added or deleted even after a newer `cstudy` changes
the starter or the generated tests. It lives in `.cs/projects/<slug>.json`, outside the folder.
"""

import hashlib
from dataclasses import dataclass
from enum import StrEnum

from coding_study.domain.project import ProjectTree

MANIFESTS_DIRECTORY = ".cs/projects"
MANIFEST_SUFFIX = ".json"


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


def _path(file: ProvidedFile) -> str:
    return file.path
