"""`cstudy status`: where an attempt in progress stands, without running anything
(docs/specs/cli.md#cstudy-status).

Every attempt has its file, statement, hints, time box and next step. An autograded problem adds
its latest `cstudy test`, a progressive or project problem its open levels, and a project problem
when each level opened, its latest submission, the best count per level and the state of each file
of its folder against what `cstudy` provided.
"""

from dataclasses import dataclass
from datetime import datetime

from coding_study.application.active_attempt import find_attempt
from coding_study.application.environment import Environment
from coding_study.application.project_manifest import folder_states
from coding_study.domain import layout
from coding_study.domain.attempts import Attempt, RunRecord, passed_every_case
from coding_study.domain.code_intelligence import NoCodeIntelligence, no_code_intelligence
from coding_study.domain.file_states import FolderFile, StarterChanges, starter_changes
from coding_study.domain.hints import hint_level, problem_hints
from coding_study.domain.items import EntryKind, entry_kind
from coding_study.domain.levels import FIRST_LEVEL, LevelProgress, level_progress
from coding_study.domain.mock_configs import visible_scenario_names
from coding_study.domain.problem import Language, Problem, ProblemKind, Track
from coding_study.domain.problem_files import PROBLEM_FILE
from coding_study.domain.project import NO_PROJECT_FILES
from coding_study.domain.service_project import MockScenarios, service_of
from coding_study.domain.submissions import LevelTally, SubmissionRecord, best_per_level

TEST_NEXT = "cstudy test --watch"
SERVICE_NEXT = "cstudy dev, then cstudy test and cstudy submit"
"""A service project's `cstudy test` takes no flag of a native run."""
DONE_NEXT = "cstudy done --rating easy|ok|hard"
NO_HINTS = 0


@dataclass(frozen=True, slots=True)
class OpenLevel:
    level: int
    title: str
    opened_at: datetime | None
    """None for a level whose opening `cstudy` did not record: every level of a progressive
    problem, and a project level opened before `cstudy` recorded unlocks."""


@dataclass(frozen=True, slots=True)
class HintCount:
    used: int
    total: int
    """The problem's hints; 0 for an item."""
    locked_until_level: int | None
    """The level a project problem's next hint opens with, while that level is locked."""


@dataclass(frozen=True, slots=True)
class ProjectStanding:
    """What only a project attempt has."""

    latest_submission: SubmissionRecord | None
    best_per_level: tuple[LevelTally, ...]
    """The most passed cases of each level over the attempt's submissions."""
    files: tuple[FolderFile, ...]
    """Every file of the folder and every file `cstudy` provided that it lacks, in path order."""

    @property
    def starter_changes(self) -> StarterChanges:
        return starter_changes(self.files)


@dataclass(frozen=True, slots=True)
class AttemptStanding:
    attempt: Attempt
    kind: EntryKind
    track: Track
    statement: str
    hints: HintCount
    now: datetime
    next_step: str
    levels: LevelProgress | None = None
    """None without levels."""
    opened: tuple[OpenLevel, ...] = ()
    """Levels 1 to the unlocked one."""
    last_test_run: RunRecord | None = None
    project: ProjectStanding | None = None
    no_code_intelligence: NoCodeIntelligence | None = None
    """None when the language's server decides, as for every attempt but a service project's in
    a language whose server runs in no sidecar yet."""
    service: tuple[MockScenarios, ...] | None = None
    """A service project's mock servers, each with its visible scenarios; None for any other."""

    @property
    def file(self) -> str | None:
        """The file `cstudy start` wrote: the stub, the project folder or the notes."""
        return self.attempt.stub_path

    @property
    def test_run_predates_level(self) -> int | None:
        """The first level that opened after the latest `cstudy test`, which that run did not
        cover; None without a run, or when it ran after every recorded unlock."""
        run = self.last_test_run
        if run is None:
            return None
        later = (
            level.level
            for level in self.opened
            if level.opened_at is not None and level.opened_at > run.ran_at
        )
        return next(later, None)


def attempt_status(
    environment: Environment, slug: str | None, language: Language | None
) -> AttemptStanding:
    """Raises UsageError without an attempt in progress."""
    attempt = find_attempt(environment.progress, slug, language)
    if attempt.language is None:
        return _item_status(environment, attempt)
    return _ProblemStatus(environment, attempt).standing()


def _item_status(environment: Environment, attempt: Attempt) -> AttemptStanding:
    meta = environment.items.load(attempt.slug)
    return AttemptStanding(
        attempt=attempt,
        kind=EntryKind.ITEM,
        track=meta.track,
        statement=layout.statement_path(meta.slug),
        hints=HintCount(attempt.hints_used, NO_HINTS, None),
        now=environment.clock.now(),
        next_step=f"answer in the notes, then cstudy solution {meta.slug}",
    )


class _ProblemStatus:
    def __init__(self, environment: Environment, attempt: Attempt) -> None:
        self._environment = environment
        self._attempt = attempt
        self._problem = environment.problems.load(attempt.slug)
        self._levels = level_progress(self._problem.meta, attempt.level_unlocked)

    def standing(self) -> AttemptStanding:
        meta = self._problem.meta
        last_run = self._environment.progress.latest_test_run(self._attempt.id)
        project = self._project()
        return AttemptStanding(
            attempt=self._attempt,
            kind=entry_kind(meta.kind),
            track=meta.track,
            statement=layout.statement_path(meta.slug),
            hints=self._hints(),
            now=self._environment.clock.now(),
            next_step=self._next_step(last_run, project),
            levels=self._levels,
            opened=self._opened(),
            last_test_run=last_run,
            project=project,
            no_code_intelligence=no_code_intelligence(meta, self._attempt.language),
            service=service_mocks(self._problem),
        )

    @property
    def _is_project(self) -> bool:
        return self._problem.meta.kind is ProblemKind.PROJECT

    def _opened(self) -> tuple[OpenLevel, ...]:
        levels = self._levels
        if levels is None:
            return ()
        unlocks = (
            {
                unlock.level: unlock.unlocked_at
                for unlock in self._environment.progress.level_unlocks(self._attempt.id)
            }
            if self._is_project
            else {}
        )
        return tuple(
            OpenLevel(level, levels.title(level), unlocks.get(level))
            for level in range(FIRST_LEVEL, levels.unlocked + 1)
        )

    def _hints(self) -> HintCount:
        """A project problem's next hint stays locked until the level it opens with opens."""
        text = self._environment.files.read_text(self._attempt.slug, PROBLEM_FILE) or ""
        total = len(problem_hints(text))
        used = self._attempt.hints_used
        levels = self._levels
        if not self._is_project or levels is None or used >= total:
            return HintCount(used, total, None)
        level = hint_level(used + 1, total, levels.last)
        return HintCount(used, total, level if level > levels.unlocked else None)

    def _next_step(self, last_run: RunRecord | None, project: ProjectStanding | None) -> str:
        if project is not None:
            return self._project_next_step(project)
        return self._single_file_next_step(last_run)

    def _project_next_step(self, project: ProjectStanding) -> str:
        if self._attempt.first_pass_at is not None:
            return DONE_NEXT
        if project.latest_submission is None or self._levels is None:
            return SERVICE_NEXT if service_of(self._problem.meta) else TEST_NEXT
        return f"cstudy submit once level {self._levels.unlocked} passes"

    def _single_file_next_step(self, last_run: RunRecord | None) -> str:
        """Testing until a run passes every case of the problem, as `cstudy done` requires."""
        language = self._attempt.language
        assert language is not None
        passed = passed_every_case(last_run, self._problem, language)
        return DONE_NEXT if passed else TEST_NEXT

    def _project(self) -> ProjectStanding | None:
        if not self._is_project or self._levels is None:
            return None
        submissions = self._environment.progress.submissions(self._attempt.id)
        return ProjectStanding(
            latest_submission=submissions[-1] if submissions else None,
            best_per_level=best_per_level(submissions),
            files=folder_states(self._environment, self._problem, self._levels.unlocked),
        )


def service_mocks(problem: Problem) -> tuple[MockScenarios, ...] | None:
    """The mock servers a dev stack holds, in the manifest's order, each with the scenarios it may
    switch to; None for a problem that is not a service project."""
    service = service_of(problem.meta)
    if service is None:
        return None
    files = (problem.project_files or NO_PROJECT_FILES).mocks
    return tuple(
        MockScenarios(mock.name, visible_scenario_names(files[mock.name]))
        for mock in service.mocks
        if mock.name in files
    )
