"""The levels an attempt has passed, and the mastery and goal of its problem in its language
(docs/specs/progress-and-scheduling.md#level-passes), read from progress.db for `cstudy done`,
`cstudy status` and the statement."""

from coding_study.application.environment import Environment
from coding_study.domain.attempts import Attempt
from coding_study.domain.level_passes import LevelMastery, LevelsPassed, level_mastery, run_levels
from coding_study.domain.levels import level_progress
from coding_study.domain.problem import Problem, ProblemKind
from coding_study.domain.submissions import counted_submission, levels_finished


def levels_passed(
    environment: Environment, attempt: Attempt, problem: Problem
) -> LevelsPassed | None:
    """A project's from its counted submission, which stands in for the latest test run; a
    progressive problem's from its latest test run; None for a problem without levels."""
    meta = problem.meta
    if meta.kind is ProblemKind.PROJECT:
        counted = counted_submission(environment.progress.submissions(attempt.id))
        return LevelsPassed(levels_finished(counted), len(meta.levels))
    if level_progress(meta, None) is None or attempt.language is None:
        return None
    latest = environment.progress.latest_test_run(attempt.id)
    return run_levels(latest, problem, attempt.language)


def language_mastery(
    environment: Environment, attempt: Attempt, problem: Problem
) -> LevelMastery | None:
    """The mastery and the next goal over the finished attempts of `attempt`'s problem in its
    language; None for a problem without levels."""
    if level_progress(problem.meta, None) is None:
        return None
    same_language = (
        found
        for found in environment.progress.attempts(attempt.slug)
        if found.language is attempt.language
    )
    return level_mastery(same_language, len(problem.meta.levels))
