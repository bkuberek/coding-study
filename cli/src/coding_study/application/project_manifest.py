"""The manifests of the workspace's project folders, in `.cs/projects/<slug>.json`
(docs/specs/installation-and-workspaces.md#project-folders).

`cstudy start` writes a folder's manifest when it copies the starter, and each generated test file
is recorded as it is written: level 1's at start, each next level's when `cstudy submit` opens
it. A file is recorded with the content `cstudy` provided, also when a file of yours was already
at its path and kept. A resumed attempt keeps what was recorded, and rebuilds a missing manifest
from what `cstudy` provides now. The manifest is per machine, as the rest of `.cs/` is.
"""

import json
from collections.abc import Mapping
from typing import cast

from coding_study.application.environment import Environment
from coding_study.application.ports import ProjectTestGenerator, Workspace
from coding_study.domain.file_states import FolderFile, folder_files
from coding_study.domain.levels import FIRST_LEVEL
from coding_study.domain.problem import Problem
from coding_study.domain.project import PATH_SEPARATOR, project_language, relative_path_issue
from coding_study.domain.project_manifest import (
    FileOrigin,
    ProjectManifest,
    ProvidedFile,
    level_file,
    manifest_path,
    starter_manifest,
)
from coding_study.domain.project_tests import level_tests
from coding_study.domain.workspace_projects import project_folder

MANIFEST_FORMAT = 1
INDENT = 2
_RECORDED_ORIGINS = frozenset({FileOrigin.STARTER, FileOrigin.LEVEL})


class ProjectManifests:
    """The manifest of each project folder, by the problem's slug."""

    def __init__(self, workspace: Workspace) -> None:
        self._workspace = workspace

    def load(self, slug: str) -> ProjectManifest | None:
        """None when the manifest is missing, unreadable or of another format."""
        path = manifest_path(slug)
        if not self._workspace.exists(path):
            return None
        try:
            document: object = json.loads(self._workspace.read_text(path))
        except (OSError, ValueError):
            return None
        return _manifest(document)

    def save(self, slug: str, manifest: ProjectManifest) -> None:
        files = {file.path: _entry(file) for file in manifest.files}
        document = {"format": MANIFEST_FORMAT, "files": dict(sorted(files.items()))}
        self._workspace.write_text(manifest_path(slug), json.dumps(document, indent=INDENT) + "\n")

    def record(self, slug: str, provided: ProvidedFile) -> None:
        """Records `provided` in place of what the manifest had for its path."""
        manifest = self.load(slug) or ProjectManifest()
        self.save(slug, manifest.with_file(provided))

    def recorded(self, slug: str, path: str) -> ProvidedFile | None:
        """What the manifest records for `path`, relative to the folder."""
        manifest = self.load(slug)
        return None if manifest is None else manifest.file(path)


def starter_files(problem: Problem) -> ProjectManifest:
    """The problem's starter as `cstudy start` copies it; nothing for a problem without one."""
    files = problem.project_files
    starter = files.starter if files else None
    return ProjectManifest() if starter is None else starter_manifest(starter)


def provided_now(
    problem: Problem, generator: ProjectTestGenerator, unlocked: int
) -> ProjectManifest:
    """What `cstudy` provides now in the folder of an attempt at level `unlocked`: the starter and
    the generated test file of each level from 1 to `unlocked`."""
    manifest = starter_files(problem)
    for level in range(FIRST_LEVEL, unlocked + 1):
        tests = level_tests(problem, level)
        manifest = manifest.with_file(level_file(tests.path, generator.generate(tests), level))
    return manifest


def folder_manifest(environment: Environment, problem: Problem, unlocked: int) -> ProjectManifest:
    """The folder's manifest; without one, what `cstudy` provides now (`provided_now`), which
    this writes nowhere."""
    manifest = ProjectManifests(environment.workspace).load(problem.meta.slug)
    if manifest is not None:
        return manifest
    generator = environment.toolchains.project_test_generator(project_language(problem.meta))
    return provided_now(problem, generator, unlocked)


def folder_states(
    environment: Environment, problem: Problem, unlocked: int
) -> tuple[FolderFile, ...]:
    """Every file of the folder of an attempt at level `unlocked`, untracked ones aside, and every
    file `cstudy` provided that the folder lacks, each with its origin and state."""
    workspace = environment.workspace
    folder = project_folder(problem.meta.slug)
    digests = {
        path: workspace.content_hash(f"{folder}{PATH_SEPARATOR}{path}")
        for path in workspace.tracked_files(folder)
    }
    return folder_files(folder_manifest(environment, problem, unlocked), digests)


def _entry(file: ProvidedFile) -> dict[str, object]:
    level = {} if file.level is None else {"level": file.level}
    return {"origin": file.origin.value, **level, "sha256": file.digest}


def _manifest(document: object) -> ProjectManifest | None:
    if not isinstance(document, dict):
        return None
    fields = cast("dict[str, object]", document)
    files = fields.get("files")
    if fields.get("format") != MANIFEST_FORMAT or not isinstance(files, dict):
        return None
    manifest = ProjectManifest()
    for path, entry in cast("dict[object, object]", files).items():
        provided = _provided(path, entry)
        if provided is None:
            return None
        manifest = manifest.with_file(provided)
    return manifest


def _provided(path: object, entry: object) -> ProvidedFile | None:
    """The file an entry of the manifest records; None for an entry `save` never writes."""
    if not isinstance(path, str) or relative_path_issue(path) or not isinstance(entry, dict):
        return None
    fields = cast("Mapping[str, object]", entry)
    origin, digest, level = fields.get("origin"), fields.get("sha256"), fields.get("level")
    if not isinstance(origin, str) or origin not in _RECORDED_ORIGINS:
        return None
    number = level if isinstance(level, int) and not isinstance(level, bool) else None
    if not isinstance(digest, str) or (number is not None) != (origin == FileOrigin.LEVEL):
        return None
    return ProvidedFile(path, digest, FileOrigin(origin), number)
