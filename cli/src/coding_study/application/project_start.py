"""`cstudy start` on a project problem (docs/specs/cli.md#cstudy-start).

A project starts in its one language. A new attempt copies the starter into `projects/<slug>/`,
writes level 1's test file and opens level 1; a resumed attempt writes back the missing test files
of its unlocked levels and leaves every other file as it is. `--fresh` and review attempts first
archive the folder; a refused archive leaves no half-started attempt.
"""

from dataclasses import dataclass, replace

from coding_study.application.environment import Environment
from coding_study.application.project_tests import LevelTestFile, LevelTestWriter
from coding_study.application.project_workspace import (
    archive_project,
    resume_project,
    seed_project,
)
from coding_study.application.statement_file import write_statement
from coding_study.domain.attempts import Attempt, AttemptMode, AttemptStatus, NewAttempt
from coding_study.domain.errors import UsageError
from coding_study.domain.levels import FIRST_LEVEL
from coding_study.domain.problem import Language, Problem
from coding_study.domain.project import entry_files, project_language
from coding_study.domain.signature import ClassSignature
from coding_study.domain.submissions import LevelUnlock
from coding_study.domain.workspace_projects import project_folder


@dataclass(frozen=True, slots=True)
class StartedProject:
    """What `cstudy start` reports about a project folder."""

    folder: str
    """`projects/<slug>`, relative to the workspace root."""
    files: int
    """The files the folder holds, untracked ones aside (`Workspace.tracked_files`)."""
    entry_file: str
    """Relative to the folder: the file that defines the entry class."""
    entry_class: str
    tests: LevelTestFile
    """The test file of the unlocked level."""


@dataclass(frozen=True, slots=True)
class ProjectStart:
    """A started or resumed project attempt."""

    attempt: Attempt
    project: StartedProject
    resumed: bool
    copied_starter: bool
    archived_to: str | None = None


@dataclass(frozen=True, slots=True)
class ProjectStartRequest:
    language: Language | None
    """None, or the problem's own language: a project never takes `default_lang`."""
    fresh: bool
    timer_s: int | None
    mode: AttemptMode


def project_start_language(problem: Problem, requested: Language | None) -> Language:
    """The project's one language; raises UsageError when `requested` names another."""
    language = project_language(problem.meta)
    if requested not in (None, language):
        raise UsageError(f"{problem.meta.slug} is solved in {language} only")
    return language


def start_project(
    environment: Environment, problem: Problem, request: ProjectStartRequest
) -> ProjectStart:
    language = project_start_language(problem, request.language)
    in_progress = environment.progress.in_progress_attempt(problem.meta.slug, language)
    starter = _ProjectStarter(environment, problem, language)
    if in_progress is not None and not request.fresh:
        return starter.resume(in_progress)
    return starter.begin(in_progress, request)


class _ProjectStarter:
    def __init__(self, environment: Environment, problem: Problem, language: Language) -> None:
        self._environment = environment
        self._problem = problem
        self._language = language
        self._folder = project_folder(problem.meta.slug)
        generator = environment.toolchains.project_test_generator(language)
        self._tests = LevelTestWriter(environment.workspace, generator)

    def resume(self, attempt: Attempt) -> ProjectStart:
        unlocked = attempt.level_unlocked or FIRST_LEVEL
        seeded = resume_project(self._environment.workspace, self._problem)
        written = self._tests.write_levels(self._problem, self._folder, unlocked)
        write_statement(self._environment, self._problem, unlocked)
        return ProjectStart(attempt, self._started(written[-1]), True, bool(seeded.copied))

    def begin(self, in_progress: Attempt | None, request: ProjectStartRequest) -> ProjectStart:
        progress = self._environment.progress
        slug = self._problem.meta.slug
        archives = request.fresh or request.mode is AttemptMode.REVIEW
        previous = progress.latest_attempt(slug, self._language)
        archived_to = self._archive(previous) if archives and previous else None
        if in_progress is not None:
            self._abandon(in_progress)
        attempt = progress.add_attempt(self._new_attempt(request))
        if archives and previous is None:
            archived_to = self._archive_under_new(attempt)
        attempt = replace(attempt, archive_path=archived_to, level_unlocked=FIRST_LEVEL)
        progress.update_attempt(attempt)
        now = self._environment.clock.now()
        progress.add_level_unlock(LevelUnlock(attempt.id, FIRST_LEVEL, now))
        seeded = seed_project(self._environment.workspace, self._problem)
        written = self._tests.write_level(self._problem, self._folder, FIRST_LEVEL)
        write_statement(self._environment, self._problem, FIRST_LEVEL)
        project = self._started(written)
        return ProjectStart(attempt, project, False, bool(seeded.copied), archived_to)

    def _new_attempt(self, request: ProjectStartRequest) -> NewAttempt:
        return NewAttempt(
            slug=self._problem.meta.slug,
            language=self._language,
            mode=request.mode,
            started_at=self._environment.clock.now(),
            time_limit_s=request.timer_s,
            stub_path=self._folder,
        )

    def _archive(self, owner: Attempt) -> str | None:
        return archive_project(self._environment.workspace, owner)

    def _archive_under_new(self, attempt: Attempt) -> str | None:
        """A folder that no earlier attempt wrote goes under the new attempt; a refused archive
        abandons the attempt again."""
        try:
            return self._archive(attempt)
        except UsageError:
            self._abandon(attempt)
            raise

    def _abandon(self, attempt: Attempt) -> None:
        ended = replace(
            attempt, status=AttemptStatus.ABANDONED, ended_at=self._environment.clock.now()
        )
        self._environment.progress.update_attempt(ended)

    def _started(self, tests: LevelTestFile) -> StartedProject:
        signature = self._problem.meta.signature
        assert isinstance(signature, ClassSignature)
        return StartedProject(
            folder=self._folder,
            files=len(self._environment.workspace.tracked_files(self._folder)),
            entry_file=self._entry_file(),
            entry_class=signature.name,
            tests=tests,
        )

    def _entry_file(self) -> str:
        """The entry module's file as the starter has it; the module file when it has neither."""
        project = self._problem.meta.project
        assert project is not None
        candidates = entry_files(project.entry, self._language)
        files = self._problem.project_files
        starter = files.starter.paths if files and files.starter else frozenset[str]()
        return next((path for path in candidates if path in starter), candidates[0])
