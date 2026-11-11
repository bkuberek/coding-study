"""Level passes: a problem with levels passes through level N of M
(docs/decisions/0024-level-passes.md, docs/specs/progress-and-scheduling.md#level-passes).

Every case of levels 1 to N passed, with N at least 1, is a pass: `cstudy done` takes a rating,
stores the attempt as `passed` and grades it from the rating, with the caps that do not come from
levels. A mock attempt keeps the rule of an interview: a progressive problem needs every level for
a rating, a project's levels cap its grade, and only every level passes.

Mastery, the most levels a passed attempt in a language passed, and the next goal are read from
the attempts; nothing else stores them.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from coding_study.domain.attempts import (
    FINISHED_STATUSES,
    Attempt,
    AttemptMode,
    AttemptStatus,
    Grade,
    RunRecord,
    passed_every_case,
)
from coding_study.domain.cases import Case
from coding_study.domain.config import ScheduleSettings
from coding_study.domain.judging import Judgement
from coding_study.domain.levels import FIRST_LEVEL
from coding_study.domain.problem import Language, Problem, ProblemKind
from coding_study.domain.scheduling import (
    LevelReview,
    ProblemStatus,
    ReviewState,
    ScheduleEntry,
    next_review_state,
)
from coding_study.domain.submissions import (
    StressSlot,
    finished_levels,
    level_grade_cap,
    level_tallies,
)


@dataclass(frozen=True, slots=True)
class LevelsPassed:
    """Every case of levels 1 to `passed` passed, of the problem's `last` levels; `passed` is 0
    when a case of level 1 did not."""

    passed: int
    last: int

    @property
    def every_level(self) -> bool:
        return self.passed >= self.last

    @property
    def partial(self) -> bool:
        """Passed level 1, and not the last level."""
        return FIRST_LEVEL <= self.passed < self.last

    @property
    def text(self) -> str:
        return f"through level {self.passed} of {self.last}"


@dataclass(frozen=True, slots=True)
class LevelOutcome:
    """What `cstudy done` makes of the levels an attempt passed."""

    levels: LevelsPassed
    rating_needed: bool
    """A rating finishes the attempt; `--gave-up` otherwise."""
    passes: bool
    """The attempt is `passed`; `failed` otherwise, even with a rating."""
    cap: Grade | None
    """The grade cap the levels set; None without one."""


def judged_levels(
    cases: Sequence[Case], judgement: Judgement | None, stress: Sequence[StressSlot] = ()
) -> int:
    """The largest L such that `judgement` ran and passed every case of levels 1 to L of
    `cases`, each (stress case, variant) of `stress` one case of its level; 0 without a
    judgement, when the code did not build."""
    if judgement is None:
        return 0
    return finished_levels(level_tallies(cases, judgement, stress))


def run_levels(run: RunRecord | None, problem: Problem, language: Language) -> LevelsPassed:
    """The levels the latest `cstudy test` run of a progressive attempt passed. A run recorded
    before runs recorded their levels passed every level when it passed every case, else none."""
    last = len(problem.meta.levels)
    if run is not None and run.levels_passed is not None:
        return LevelsPassed(min(run.levels_passed, last), last)
    return LevelsPassed(last if passed_every_case(run, problem, language) else 0, last)


def level_outcome(levels: LevelsPassed, mode: AttemptMode, kind: ProblemKind) -> LevelOutcome:
    """A pass through level 1 takes a rating and passes, uncapped. A mock keeps the rules from
    before level passes: a progressive problem takes a rating only for every level, a project
    takes one from level 1 with its levels capping the grade, and only every level passes."""
    if mode is not AttemptMode.MOCK:
        passed = levels.passed >= FIRST_LEVEL
        return LevelOutcome(levels, rating_needed=passed, passes=passed, cap=None)
    rating_needed = (
        levels.every_level if kind is ProblemKind.PROGRESSIVE else levels.passed >= FIRST_LEVEL
    )
    cap = level_grade_cap(levels.passed, levels.last)
    return LevelOutcome(levels, rating_needed, passes=levels.every_level, cap=cap)


def recorded_levels(attempt: Attempt, last: int) -> LevelsPassed | None:
    """The levels a finished attempt passed, as `cstudy done` recorded them, of `last` levels
    when it recorded none. An attempt passed before attempts recorded their levels passed every
    level; one failed then, or one not finished, recorded none."""
    if attempt.status not in FINISHED_STATUSES:
        return None
    total = attempt.levels_total if attempt.levels_total is not None else last
    if attempt.levels_passed is not None:
        return LevelsPassed(attempt.levels_passed, total)
    if attempt.status is AttemptStatus.PASSED:
        return LevelsPassed(total, total)
    return None


@dataclass(frozen=True, slots=True)
class LevelMastery:
    """A problem's levels over its finished attempts in one language."""

    last: int
    """The problem's levels now."""
    best: int | None
    """Mastery: the most levels a passed attempt passed; None before any pass."""
    last_time: int | None
    """The levels passed by the latest attempt that passed level 1; None without one."""

    @property
    def try_level(self) -> int | None:
        """The level after last time's, while it is not the last."""
        if self.last_time is None or self.last_time >= self.last:
            return None
        return self.last_time + 1

    @property
    def best_text(self) -> str | None:
        """`through level 3 of 4`; None before any pass."""
        return None if self.best is None else LevelsPassed(self.best, self.last).text

    @property
    def goal(self) -> str | None:
        """`last time: through level 2 of 4; try level 3`; None without a level to try."""
        if self.last_time is None or self.try_level is None:
            return None
        last_time = LevelsPassed(self.last_time, self.last).text
        return f"last time: {last_time}; try level {self.try_level}"


def level_mastery(attempts: Iterable[Attempt], last: int) -> LevelMastery:
    """Over the attempts of one problem in one language, latest start first; levels passed above
    the problem's `last`, from before it lost a level, count as `last`."""
    recorded = [
        (attempt, levels)
        for attempt in attempts
        if (levels := recorded_levels(attempt, last)) is not None
    ]
    passed = [
        min(levels.passed, last)
        for attempt, levels in recorded
        if attempt.status is AttemptStatus.PASSED
    ]
    through = (min(levels.passed, last) for _, levels in recorded if levels.passed >= FIRST_LEVEL)
    return LevelMastery(last, max(passed, default=None), next(through, None))


def next_level_reviews(
    previous: ScheduleEntry | None,
    passed: LevelsPassed,
    grade: Grade,
    schedule: ScheduleSettings,
) -> tuple[LevelReview, ...]:
    """Each level after the first, once a graded attempt passed through `passed`
    (docs/specs/progress-and-scheduling.md#mastery-per-level): a level it passed takes its grade,
    from a fresh review the first time; a level reached before that it did not pass takes
    `again`; a level never reached has no review yet. A schedule written before levels had
    reviews counts every level reached, with the problem's own review."""
    reviews: list[LevelReview] = []
    for level in range(FIRST_LEVEL + 1, passed.last + 1):
        before = _level_state(previous, level)
        if passed.passed >= level:
            taken = grade
        elif before is not None:
            taken = Grade.AGAIN
        else:
            continue
        state = next_review_state(
            before or ReviewState(), taken, schedule.max_interval_days, schedule.intervals
        )
        reviews.append(LevelReview(level, state, taken))
    return tuple(reviews)


def _level_state(previous: ScheduleEntry | None, level: int) -> ReviewState | None:
    if previous is None:
        return None
    if previous.levels is None:
        return previous.state
    return next((review.state for review in previous.levels if review.level == level), None)


type MasteredOf = tuple[int, int]
"""A problem's levels mastered, and its last level."""


def status_text(status: ProblemStatus, levels: MasteredOf | None) -> str:
    """`mastered through level 2 of 4` for a problem mastered below its last level; else the
    status as people read it (docs/specs/progress-and-scheduling.md#problem-status)."""
    if not _mastered_below_last(status, levels):
        return status.label
    assert levels is not None
    mastered, last = levels
    return f"{status.label} through level {mastered} of {last}"


def status_cell(status: ProblemStatus, levels: MasteredOf | None) -> str:
    """`status_text` in a narrow column: `mastered 2/4`."""
    if not _mastered_below_last(status, levels):
        return status.label
    assert levels is not None
    mastered, last = levels
    return f"{status.label} {mastered}/{last}"


def _mastered_below_last(status: ProblemStatus, levels: MasteredOf | None) -> bool:
    return status is ProblemStatus.MASTERED and levels is not None and levels[0] < levels[1]


def masteries(attempts: Sequence[Attempt], last: int) -> tuple[tuple[Language, LevelMastery], ...]:
    """The mastery of each language with a finished attempt, in `Language` order; `attempts` of
    one problem, latest start first."""
    finished = {attempt.language for attempt in attempts if recorded_levels(attempt, last)}
    return tuple(
        (language, level_mastery([found for found in attempts if found.language is language], last))
        for language in Language
        if language in finished
    )
