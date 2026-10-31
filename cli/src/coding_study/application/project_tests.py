"""The generated test files of a project attempt
(docs/specs/problem-format.md#generated-test-files).

A level's file is written when the level opens: level 1's when the attempt starts, each next
level's when a submission opens it. A file that exists is never written over, since the files
are the user's to edit; a resumed attempt writes back the missing files of its unlocked levels.
Each file is recorded in the folder's manifest (`project_manifest`) as `cstudy` generated it. The
commands (`cstudy start`, `cstudy submit`) choose when, and hold the project's lock while this
writes; this module takes no lock, since the lock is not reentrant.
"""

from dataclasses import dataclass

from coding_study.application.ports import ProjectTestGenerator, Workspace
from coding_study.application.project_manifest import ProjectManifests
from coding_study.domain.levels import FIRST_LEVEL
from coding_study.domain.problem import Problem
from coding_study.domain.project import PATH_SEPARATOR
from coding_study.domain.project_manifest import level_file
from coding_study.domain.project_tests import level_tests


@dataclass(frozen=True, slots=True)
class LevelTestFile:
    """What happened to one level's file."""

    level: int
    path: str
    """Relative to the project root, as `cstudy start` prints it: `tests/test_level_1.py`."""
    tests: int
    """The tests `cstudy` generates for the level, one per visible case."""
    written: bool
    """False: the file existed, and was kept as it is."""


class LevelTestWriter:
    """Writes a project's level test files into its folder, `project_root` in the workspace."""

    def __init__(self, workspace: Workspace, generator: ProjectTestGenerator) -> None:
        self._workspace = workspace
        self._generator = generator
        self._manifests = ProjectManifests(workspace)

    def write_level(self, problem: Problem, project_root: str, level: int) -> LevelTestFile:
        """Writes `level`'s file unless one exists, and records what it generated in the
        manifest: always when it wrote the file, else when the manifest lacks the path.

        Raises ValueError for a level the problem lacks, or a case a generated test cannot
        express (`level_tests`).
        """
        tests = level_tests(problem, level)
        slug = problem.meta.slug
        path = f"{project_root}{PATH_SEPARATOR}{tests.path}"
        written = not self._workspace.exists(path)
        if written:
            text = self._generator.generate(tests)
            self._workspace.write_text(path, text)
            self._manifests.record(slug, level_file(tests.path, text, level))
        elif self._manifests.recorded(slug, tests.path) is None:
            text = self._generator.generate(tests)
            self._manifests.record(slug, level_file(tests.path, text, level))
        return LevelTestFile(level, tests.path, len(tests.tests), written)

    def write_levels(
        self, problem: Problem, project_root: str, unlocked: int
    ) -> tuple[LevelTestFile, ...]:
        """Writes each missing file of levels 1 to `unlocked`, as a resumed attempt does."""
        return tuple(
            self.write_level(problem, project_root, level)
            for level in range(FIRST_LEVEL, unlocked + 1)
        )
