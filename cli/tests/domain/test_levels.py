from dataclasses import replace

import pytest

from coding_study.domain.cases import Case, Expected, OperationSequence
from coding_study.domain.levels import (
    SUBMIT_COMMAND,
    LevelProgress,
    cases_up_to,
    has_levels,
    level_heading,
    level_progress,
)
from coding_study.domain.problem import (
    Approach,
    ApproachRole,
    ComparatorSpec,
    ComparatorType,
    ComplexityClass,
    ContentStatus,
    Difficulty,
    Level,
    ProblemKind,
    ProblemMeta,
    Track,
)
from coding_study.domain.signature import ClassSignature

LEVELS = (Level(1, "Set and get"), Level(2, "Delete"), Level(3, "Prefix scans"))
META = ProblemMeta(
    id="0001",
    slug="level-store",
    title="Level Store",
    status=ContentStatus.DRAFT,
    difficulty=Difficulty.MEDIUM,
    track=Track.PRACTICAL,
    kind=ProblemKind.PROGRESSIVE,
    signature=ClassSignature("LevelStore", (), ()),
    comparator=ComparatorSpec(ComparatorType.OPS),
    approaches=(
        Approach(
            "dict",
            "Dictionary",
            ApproachRole.OPTIMAL,
            "O(1)",
            "O(n)",
            ComplexityClass.LINEAR,
            ComplexityClass.LINEAR,
        ),
    ),
    levels=LEVELS,
)
DESIGN = replace(META, kind=ProblemKind.DESIGN, levels=())
PROJECT = replace(META, kind=ProblemKind.PROJECT)


def case(case_id: str, level: int | None) -> Case:
    return Case(case_id, OperationSequence(("LevelStore",), ((),)), Expected([None]), level=level)


def test_problems_without_levels_have_no_progress():
    assert level_progress(DESIGN, None) is None


def test_an_attempt_without_a_stored_level_has_level_1_unlocked():
    assert level_progress(META, None) == LevelProgress(LEVELS, 1)


def test_a_project_problem_opens_its_levels_as_a_progressive_one_does():
    assert level_progress(PROJECT, 2) == LevelProgress(LEVELS, 2, SUBMIT_COMMAND)


def test_a_locked_level_of_a_project_problem_names_cstudy_submit():
    progress = level_progress(PROJECT, 2)
    assert progress is not None
    locked = "level 3 is locked; pass level 2 with cstudy submit first"
    with pytest.raises(ValueError, match=locked):
        progress.run_level(3)


@pytest.mark.parametrize(
    ("kind", "leveled"),
    [
        (ProblemKind.PROGRESSIVE, True),
        (ProblemKind.PROJECT, True),
        (ProblemKind.FUNCTION, False),
        (ProblemKind.DESIGN, False),
        (ProblemKind.CONCURRENT, False),
    ],
)
def test_progressive_and_project_problems_have_levels(kind, leveled):
    assert has_levels(kind) is leveled


def test_the_stored_level_is_unlocked():
    assert level_progress(META, 2) == LevelProgress(LEVELS, 2)


def test_a_stored_level_beyond_the_last_is_the_last():
    assert level_progress(META, 7) == LevelProgress(LEVELS, 3)


def test_the_last_level_is_the_number_of_levels():
    assert LevelProgress(LEVELS, 1).last == 3


def test_passing_every_unlocked_level_unlocks_the_next():
    assert LevelProgress(LEVELS, 1).after_passing() == LevelProgress(LEVELS, 2)


def test_passing_the_last_level_unlocks_nothing_more():
    assert LevelProgress(LEVELS, 3).after_passing() == LevelProgress(LEVELS, 3)


@pytest.mark.parametrize(("unlocked", "complete"), [(2, False), (3, True)])
def test_all_levels_are_unlocked_at_the_last(unlocked, complete):
    assert LevelProgress(LEVELS, unlocked).all_unlocked is complete


def test_the_title_of_a_level():
    assert LevelProgress(LEVELS, 1).title(3) == "Prefix scans"


def test_locked_levels_are_the_ones_after_the_unlocked_level():
    assert LevelProgress(LEVELS, 1).locked == (2, 3)


def test_no_level_is_locked_once_all_are_unlocked():
    assert LevelProgress(LEVELS, 3).locked == ()


def test_runs_every_unlocked_level_by_default():
    assert LevelProgress(LEVELS, 2).run_level(None) == 2


def test_runs_up_to_a_requested_unlocked_level():
    assert LevelProgress(LEVELS, 2).run_level(1) == 1


def test_a_locked_level_cannot_run():
    with pytest.raises(ValueError, match="level 3 is locked; pass level 2 with cstudy test first"):
        LevelProgress(LEVELS, 2).run_level(3)


@pytest.mark.parametrize("requested", [0, 4])
def test_a_level_outside_the_problem_cannot_run(requested):
    with pytest.raises(ValueError, match=f"no level {requested}; levels are 1 to 3"):
        LevelProgress(LEVELS, 2).run_level(requested)


def test_cases_up_to_a_level_keep_lower_levels_in_order():
    cases = (case("a", 2), case("b", 1), case("c", 3), case("d", 2))
    assert [found.id for found in cases_up_to(cases, 2)] == ["a", "b", "d"]


def test_cases_without_a_level_belong_to_no_level():
    assert cases_up_to((case("a", None),), 3) == ()


def test_level_heading_gives_the_level_number():
    assert level_heading("Level 2: Delete") == 2


@pytest.mark.parametrize("title", ["Level two: Delete", "Level 2", "Examples", "Level 2:"])
def test_other_headings_are_not_level_headings(title):
    assert level_heading(title) is None
