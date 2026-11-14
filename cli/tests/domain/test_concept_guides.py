from dataclasses import replace
from datetime import UTC, datetime

import pytest

from coding_study.domain.attempts import Attempt, AttemptMode, AttemptStatus
from coding_study.domain.concept_guides import (
    GuideLevel,
    LearningPath,
    PathStep,
    ProblemFacts,
    StepKind,
    by_level,
    guide_step_progress,
    highest_level_passed,
    matches_search,
    path_level,
    problem_step_progress,
    search_words,
    unknown_slug_message,
)
from coding_study.domain.scheduling import ProblemStatus

STARTED = datetime(2026, 11, 11, 9, tzinfo=UTC)
INTRO, CORE, ADVANCED = GuideLevel.INTRO, GuideLevel.CORE, GuideLevel.ADVANCED
LEVELS = {
    "i1": INTRO,
    "i2": INTRO,
    "c1": CORE,
    "c2": CORE,
    "c3": CORE,
    "a1": ADVANCED,
    "a2": ADVANCED,
    "a3": ADVANCED,
}
"""Guides by slug: the letter is the level."""


def a_path(slug: str, *guides: str) -> LearningPath:
    return LearningPath(slug, slug, "Summary.", tuple(PathStep.guide(guide) for guide in guides))


def slugs(paths: tuple[LearningPath, ...]) -> list[str]:
    return [path.slug for path in paths]


def attempt(
    status: AttemptStatus, level_unlocked: int | None = None, levels_passed: int | None = None
) -> Attempt:
    return Attempt(
        id=1,
        slug="ledger",
        language=None,
        mode=AttemptMode.NEW,
        status=status,
        started_at=STARTED,
        level_unlocked=level_unlocked,
        levels_passed=levels_passed,
        levels_total=None if levels_passed is None else 4,
    )


def facts(
    status: ProblemStatus = ProblemStatus.NEW, passed: bool = False, level: int | None = None
) -> ProblemFacts:
    return ProblemFacts(title="Ledger", status=status, passed=passed, level_passed=level)


def test_a_step_is_a_guide_or_a_problem():
    assert (PathStep.guide("a").kind, PathStep.problem("b", 2)) == (
        StepKind.GUIDE,
        PathStep(StepKind.PROBLEM, "b", 2),
    )


def test_a_read_guide_is_done():
    progress = guide_step_progress(PathStep.guide("hash-maps"), "Hash maps", read=True)
    assert (progress.done, progress.status) == (True, "read")


def test_an_unread_guide_is_not_done():
    progress = guide_step_progress(PathStep.guide("hash-maps"), "Hash maps", read=False)
    assert (progress.done, progress.status) == (False, "not read")


def test_a_problem_is_done_once_passed():
    progress = problem_step_progress(PathStep.problem("ledger"), facts(ProblemStatus.DUE, True))
    assert (progress.done, progress.status) == (True, "passed")


def test_a_problem_not_passed_shows_its_status_in_words():
    progress = problem_step_progress(PathStep.problem("ledger"), facts(ProblemStatus.IN_PROGRESS))
    assert (progress.done, progress.status) == (False, "in progress")


def test_a_level_target_is_done_once_that_level_passed():
    progress = problem_step_progress(PathStep.problem("ledger", 2), facts(level=3))
    assert (progress.done, progress.status, progress.level_passed) == (True, "level 3 passed", 3)


def test_a_level_target_not_reached_shows_the_levels_passed():
    progress = problem_step_progress(PathStep.problem("ledger", 3), facts(level=1))
    assert (progress.done, progress.status) == (False, "level 1 passed")


def test_a_level_target_with_no_level_passed_shows_the_status():
    progress = problem_step_progress(PathStep.problem("ledger", 2), facts(level=0))
    assert (progress.done, progress.status) == (False, "new")


def test_a_passed_problem_meets_any_level_target():
    progress = problem_step_progress(PathStep.problem("ledger", 4), facts(passed=True, level=4))
    assert (progress.done, progress.status) == (True, "passed")


@pytest.mark.parametrize(
    ("attempts", "expected"),
    [
        ((), 0),
        ((attempt(AttemptStatus.IN_PROGRESS, 1),), 0),
        ((attempt(AttemptStatus.IN_PROGRESS, 3),), 2),
        ((attempt(AttemptStatus.ABANDONED, 4), attempt(AttemptStatus.FAILED, 2)), 3),
        ((attempt(AttemptStatus.PASSED, 4),), 4),
        ((attempt(AttemptStatus.PASSED, 1, levels_passed=2),), 2),
        ((attempt(AttemptStatus.PASSED, 3, levels_passed=1),), 2),
        ((attempt(AttemptStatus.PASSED, 4, levels_passed=4),), 4),
    ],
)
def test_the_highest_level_passed_reads_the_unlocked_levels(
    attempts: tuple[Attempt, ...], expected: int
):
    assert highest_level_passed(attempts, levels=4) == expected


def test_a_problem_without_levels_has_no_level_passed():
    assert highest_level_passed((attempt(AttemptStatus.PASSED),), levels=0) is None


def test_an_unknown_slug_suggests_the_nearest():
    assert unknown_slug_message("guide", "hash-fn", ["hash-functions", "prefix-sums"]) == (
        'unknown guide "hash-fn"; did you mean hash-functions?'
    )


def test_an_unknown_slug_with_nothing_near_says_where_to_look():
    assert unknown_slug_message("path", "zzz", ["hashing"]) == (
        'unknown path "zzz"; cstudy learn lists the paths'
    )


def test_a_path_of_intro_guides_is_an_intro_path():
    assert path_level(a_path("p", "i1", "i2"), LEVELS) is INTRO


@pytest.mark.parametrize(
    ("guides", "expected"),
    [
        (("i1", "c1", "c2", "c3", "a1"), CORE),
        (("i1", "a1", "a2"), CORE),
        (("c1", "a1", "a2", "a3"), ADVANCED),
        (("i1", "i2", "c1"), INTRO),
    ],
)
def test_a_path_is_at_the_level_nearest_the_mean_of_its_guides(
    guides: tuple[str, ...], expected: GuideLevel
):
    assert path_level(a_path("p", *guides), LEVELS) is expected


def test_a_mean_halfway_between_two_levels_takes_the_higher():
    halfway = (a_path("p", "i1", "c1"), a_path("q", "c1", "a1"))
    assert [path_level(path, LEVELS) for path in halfway] == [CORE, ADVANCED]


def test_problem_steps_and_guides_that_do_not_exist_do_not_count():
    steps = (PathStep.problem("two-sum"), PathStep.guide("gone"), PathStep.guide("i1"))
    assert path_level(LearningPath("p", "P", "Summary.", steps), LEVELS) is INTRO


def test_a_path_without_guides_has_no_level():
    path = LearningPath("p", "P", "Summary.", (PathStep.problem("two-sum"),))
    assert path_level(path, LEVELS) is None


def test_paths_go_from_introductory_to_advanced():
    paths = (a_path("deep", "a1", "a2"), a_path("daily", "c1"), a_path("first", "i1"))
    assert slugs(by_level(paths, LEVELS)) == ["first", "daily", "deep"]


def test_within_a_level_the_path_whose_guides_average_lower_comes_first():
    paths = (
        a_path("steeper", "c1", "c2", "a1"),
        a_path("even", "c1"),
        a_path("gentler", "i1", "c1", "c2"),
    )
    assert slugs(by_level(paths, LEVELS)) == ["gentler", "even", "steeper"]


def test_paths_with_the_same_mean_keep_their_order():
    paths = (a_path("b", "i1", "a1"), a_path("a", "c1"), a_path("c", "c2", "c3"))
    assert slugs(by_level(paths, LEVELS)) == ["b", "a", "c"]


def test_a_path_without_guides_comes_last():
    problems_only = LearningPath("problems", "P", "Summary.", (PathStep.problem("two-sum"),))
    paths = (problems_only, a_path("deep", "a1"), a_path("first", "i1"))
    assert slugs(by_level(paths, LEVELS)) == ["first", "deep", "problems"]


def test_a_level_the_path_names_wins_over_its_guides():
    assert path_level(replace(a_path("p", "i1", "i2"), level=ADVANCED), LEVELS) is ADVANCED


def test_a_named_level_orders_a_path_whatever_its_guides_average():
    paths = (
        replace(a_path("deep", "i1"), level=ADVANCED),
        a_path("daily", "c1", "c2"),
        replace(a_path("first", "c1"), level=INTRO),
    )
    assert slugs(by_level(paths, LEVELS)) == ["first", "daily", "deep"]


def test_a_path_without_guides_that_names_a_level_is_ordered_by_it():
    steps = (PathStep.problem("two-sum"),)
    problems_only = LearningPath("problems", "P", "Summary.", steps, level=INTRO)
    assert slugs(by_level((a_path("daily", "c1"), problems_only), LEVELS)) == ["problems", "daily"]


def test_a_search_finds_every_word_in_any_field_in_any_case():
    words = search_words("  HASH   maps ")
    assert [
        words,
        matches_search(words, "Hash maps and sets", "A summary.", "hash-maps"),
        matches_search(words, "Hash functions", "Buckets need maps.", "hash-functions"),
        matches_search(words, "Hash functions", "A summary.", "hash-functions"),
        matches_search((), "Anything"),
    ] == [("hash", "maps"), True, True, False, True]
