"""`cstudy status`: where a project attempt in progress stands, without running anything
(docs/specs/cli.md#cstudy-status).

The unlocked level and when each level opened, the time box, the latest `cstudy test` run, the
latest submission and the best count per level, the state of each file of the folder against
what `cstudy` provided, and what to do next.
"""

from dataclasses import dataclass
from datetime import datetime

from coding_study.application.active_attempt import find_attempt
from coding_study.application.environment import Environment
from coding_study.application.project_manifest import folder_states
from coding_study.domain import layout
from coding_study.domain.attempts import Attempt, RunRecord
from coding_study.domain.errors import UsageError
from coding_study.domain.file_states import FolderFile, StarterChanges, starter_changes
from coding_study.domain.levels import FIRST_LEVEL, LevelProgress, level_progress
from coding_study.domain.problem import Language, ProblemKind, ProblemMeta
from coding_study.domain.submissions import LevelTally, SubmissionRecord, best_per_level

TEST_NEXT = "cstudy test --watch"
DONE_NEXT = "cstudy done --rating easy|ok|hard"


@dataclass(frozen=True, slots=True)
class OpenLevel:
    level: int
    title: str
    opened_at: datetime | None
    """None for a level opened before `cstudy` recorded unlocks."""


@dataclass(frozen=True, slots=True)
class ProjectStatus:
    meta: ProblemMeta
    attempt: Attempt
    statement: str
    levels: LevelProgress
    opened: tuple[OpenLevel, ...]
    """Levels 1 to the unlocked one."""
    now: datetime
    last_test_run: RunRecord | None
    latest_submission: SubmissionRecord | None
    best_per_level: tuple[LevelTally, ...]
    """The most passed cases of each level over the attempt's submissions."""
    files: tuple[FolderFile, ...]
    """Every file of the folder and every file `cstudy` provided that it lacks, in path order."""
    next_step: str

    @property
    def starter_changes(self) -> StarterChanges:
        return starter_changes(self.files)

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


def project_status(
    environment: Environment, slug: str | None, language: Language | None
) -> ProjectStatus:
    """Raises UsageError without an attempt in progress, or for another kind of problem."""
    attempt = find_attempt(environment.progress, slug, language)
    problem = environment.problems.load(attempt.slug)
    meta = problem.meta
    levels = level_progress(meta, attempt.level_unlocked)
    if meta.kind is not ProblemKind.PROJECT or levels is None:
        raise UsageError("cstudy status is for project problems")
    progress = environment.progress
    unlocks = {unlock.level: unlock.unlocked_at for unlock in progress.level_unlocks(attempt.id)}
    opened = tuple(
        OpenLevel(level, levels.title(level), unlocks.get(level))
        for level in range(FIRST_LEVEL, levels.unlocked + 1)
    )
    submissions = progress.submissions(attempt.id)
    latest = submissions[-1] if submissions else None
    return ProjectStatus(
        meta=meta,
        attempt=attempt,
        statement=layout.statement_path(meta.slug),
        levels=levels,
        opened=opened,
        now=environment.clock.now(),
        last_test_run=progress.latest_test_run(attempt.id),
        latest_submission=latest,
        best_per_level=best_per_level(submissions),
        files=folder_states(environment, problem, levels.unlocked),
        next_step=_next_step(attempt, latest, levels),
    )


def _next_step(attempt: Attempt, latest: SubmissionRecord | None, levels: LevelProgress) -> str:
    if attempt.first_pass_at is not None:
        return DONE_NEXT
    if latest is None:
        return TEST_NEXT
    return f"cstudy submit once level {levels.unlocked} passes"
