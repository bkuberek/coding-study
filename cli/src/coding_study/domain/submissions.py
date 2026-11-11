"""Project submissions: what `cstudy submit` stores, and what `cstudy done` grades from
(docs/specs/progress-and-scheduling.md#project-attempts).

A project attempt is graded from its submissions, not its test runs. The counted submission is the
latest that graded every unlocked level; the levels it finished cap the grade.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime

from coding_study.domain.attempts import Grade
from coding_study.domain.case_status import CaseStatus
from coding_study.domain.cases import Case
from coding_study.domain.concurrency import StressVariant
from coding_study.domain.judging import Judgement, Tally
from coding_study.domain.stress import StressScenario

type StressSlot = tuple[Case, StressVariant]
"""One (stress case, variant): one verdict, and one hidden case of the stress case's level."""


@dataclass(frozen=True, slots=True)
class LevelTally:
    """One level's graded cases in a submission."""

    level: int
    visible_total: int
    visible_passed: int
    hidden_total: int
    hidden_passed: int

    @property
    def total(self) -> int:
        return self.visible_total + self.hidden_total

    @property
    def passed(self) -> int:
        return self.visible_passed + self.hidden_passed

    @property
    def all_passed(self) -> bool:
        return self.passed == self.total

    @property
    def hidden_failed(self) -> int:
        return self.hidden_total - self.hidden_passed


@dataclass(frozen=True, slots=True)
class SubmissionRecord:
    """One `cstudy submit` (a row of `submissions`)."""

    attempt_id: int
    submitted_at: datetime
    code_hash: str
    """sha256 of the project folder."""
    graded_up_to: int
    """Levels 1 to this one were graded."""
    every_level: bool
    """`graded_up_to` was the unlocked level: only such a submission opens a level or counts for
    `cstudy done`."""
    levels: tuple[LevelTally, ...]
    """One per graded level, in level order."""
    tally: Tally
    """Every graded case; a submission whose code did not load counts each as errored."""
    duration_ms: int

    @property
    def levels_finished(self) -> int:
        """The largest L such that every case of levels 1 to L passed; 0 when level 1 failed."""
        return finished_levels(self.levels)


@dataclass(frozen=True, slots=True)
class LevelUnlock:
    """When a level of a project attempt opened (a row of `level_unlocks`)."""

    attempt_id: int
    level: int
    unlocked_at: datetime


def level_tallies(
    cases: Sequence[Case], judgement: Judgement, stress: Sequence[StressSlot] = ()
) -> tuple[LevelTally, ...]:
    """The graded `cases` counted per level, in level order, with each (stress case, variant) of
    `stress` as a hidden case of its stress case's level; a case passed when its verdict says so,
    so code that did not load passes none."""
    passed = {
        verdict.case.id for verdict in judgement.verdicts if verdict.status is CaseStatus.PASS
    }
    passed_stress = {
        (verdict.case_id, verdict.variant)
        for verdict in judgement.stress
        if verdict.status is CaseStatus.PASS
    }
    sequential = [case for case in cases if not isinstance(case.input, StressScenario)]
    levels = sorted({case.level for case in cases if case.level is not None})
    return tuple(
        _level_tally(level, sequential, passed, _stress_counts(level, stress, passed_stress))
        for level in levels
    )


def _stress_counts(
    level: int, stress: Sequence[StressSlot], passed: set[tuple[str, StressVariant]]
) -> tuple[int, int]:
    """How many (stress case, variant) of `level` there are, and how many passed."""
    in_level = [(case.id, variant) for case, variant in stress if case.level == level]
    return len(in_level), sum(1 for slot in in_level if slot in passed)


def _level_tally(
    level: int, cases: Sequence[Case], passed: set[str], stress: tuple[int, int]
) -> LevelTally:
    in_level = [case for case in cases if case.level == level]
    visible = [case for case in in_level if case.visible]
    hidden = [case for case in in_level if not case.visible]
    stress_total, stress_passed = stress
    return LevelTally(
        level=level,
        visible_total=len(visible),
        visible_passed=sum(1 for case in visible if case.id in passed),
        hidden_total=len(hidden) + stress_total,
        hidden_passed=sum(1 for case in hidden if case.id in passed) + stress_passed,
    )


def finished_levels(tallies: Iterable[LevelTally]) -> int:
    """The largest L such that every case of levels 1 to L passed, `tallies` in level order; 0
    when level 1 did not."""
    finished = 0
    for tally in tallies:
        if not tally.all_passed:
            break
        finished = tally.level
    return finished


def counted_submission(submissions: Iterable[SubmissionRecord]) -> SubmissionRecord | None:
    """The latest submission that graded every unlocked level; `submissions` earliest first."""
    counted = [submission for submission in submissions if submission.every_level]
    return counted[-1] if counted else None


def levels_finished(submission: SubmissionRecord | None) -> int:
    return submission.levels_finished if submission is not None else 0


def level_grade_cap(finished: int, last: int) -> Grade | None:
    """Every level finished: no cap; all but the last: `hard`; fewer: `again`."""
    if finished >= last:
        return None
    return Grade.HARD if finished == last - 1 else Grade.AGAIN


def best_per_level(submissions: Iterable[SubmissionRecord]) -> tuple[LevelTally, ...]:
    """For each level any submission graded, the tally with the most passed cases (the earliest
    of equals), in level order."""
    best: dict[int, LevelTally] = {}
    for submission in submissions:
        for tally in submission.levels:
            known = best.get(tally.level)
            if known is None or tally.passed > known.passed:
                best[tally.level] = tally
    return tuple(best[level] for level in sorted(best))
