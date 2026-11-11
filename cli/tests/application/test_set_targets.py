"""Target levels on set entries in the use cases of `cstudy set` and `cstudy next --set`
(docs/decisions/0024-level-passes.md#target-levels-in-sets), over a real `sets.yaml` and a real
database; level-store has 3 levels, parking-lot none."""

from dataclasses import replace
from pathlib import Path

import pytest

from coding_study.application.next_problem import NextRequest, Recommendation, recommend
from coding_study.application.problem_sets import (
    add_to_set,
    create_set,
    find_set,
    move_in_set,
    remove_from_set,
    set_standing,
    set_view,
    sets_with_standing,
)
from coding_study.domain.attempts import AttemptMode, AttemptStatus, Grade, NewAttempt
from coding_study.domain.errors import UsageError
from coding_study.domain.problem import Language
from tests.fakes import NOW, make_environment, repository_root

PHASE4 = Path(__file__).resolve().parents[1] / "fixtures" / "phase4" / "problems"
LOOP = "backend-loop"
STORE = "level-store"
DESIGN = "parking-lot"


@pytest.fixture
def environment(tmp_path: Path):
    environment = make_environment(repository_root(tmp_path, PHASE4))
    create_set(environment, LOOP)
    return environment


def passed_through(environment, levels: int) -> None:
    progress = environment.progress
    attempt = progress.add_attempt(NewAttempt(STORE, Language.PYTHON, AttemptMode.NEW, NOW))
    progress.update_attempt(
        replace(
            attempt,
            status=AttemptStatus.PASSED,
            ended_at=NOW,
            grade=Grade.OK,
            levels_passed=levels,
            levels_total=3,
        )
    )


def test_an_entry_is_added_with_its_target(environment):
    add_to_set(environment, LOOP, (STORE,), level=2)
    assert find_set(environment, LOOP).target_of(STORE) == 2


def test_a_target_on_an_entry_already_there_changes_it(environment):
    add_to_set(environment, LOOP, (STORE,))
    change = add_to_set(environment, LOOP, (STORE,), level=2)
    assert (change.retargeted, find_set(environment, LOOP).target_of(STORE)) == ((STORE,), 2)


def test_a_target_above_the_last_level_is_refused(environment):
    with pytest.raises(UsageError, match=f"{STORE} has levels 1 to 3"):
        add_to_set(environment, LOOP, (STORE,), level=4)


def test_a_target_for_a_problem_without_levels_is_refused(environment):
    with pytest.raises(UsageError, match=f"{DESIGN} has no levels"):
        add_to_set(environment, LOOP, (DESIGN,), level=2)


def test_moving_and_removing_others_keep_the_target(environment):
    add_to_set(environment, LOOP, (DESIGN,))
    add_to_set(environment, LOOP, (STORE,), level=2)
    move_in_set(environment, LOOP, STORE, 1)
    remove_from_set(environment, LOOP, (DESIGN,))
    assert find_set(environment, LOOP).levels == ((STORE, 2),)


def test_an_entry_counts_once_a_pass_reached_its_target(environment):
    add_to_set(environment, LOOP, (STORE,), level=2)
    passed_through(environment, 2)
    assert set_standing(environment, find_set(environment, LOOP)).passed == 1


def test_an_entry_without_a_target_counts_once_every_level_passed(environment):
    add_to_set(environment, LOOP, (STORE,))
    passed_through(environment, 2)
    assert sets_with_standing(environment)[0][1].passed == 0


def test_a_row_shows_its_target_and_whether_it_reached_it(environment):
    add_to_set(environment, LOOP, (STORE,), level=2)
    passed_through(environment, 2)
    row = set_view(environment, LOOP).rows[0]
    assert (row.level, row.passed) == (2, True)


def picked(environment) -> str:
    found = recommend(environment, NextRequest(set_name=LOOP))
    assert isinstance(found, Recommendation)
    return found.pick.candidate.slug


def test_next_passes_over_an_entry_that_reached_its_target(environment):
    add_to_set(environment, LOOP, (STORE,), level=2)
    add_to_set(environment, LOOP, (DESIGN,))
    passed_through(environment, 2)
    assert picked(environment) == DESIGN


def test_next_keeps_an_entry_below_its_target(environment):
    add_to_set(environment, LOOP, (STORE,))
    add_to_set(environment, LOOP, (DESIGN,))
    passed_through(environment, 2)
    assert picked(environment) == STORE
