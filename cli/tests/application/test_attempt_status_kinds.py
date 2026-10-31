"""`cstudy status` on single-file problems and items (docs/specs/cli.md#cstudy-status)."""

from dataclasses import replace
from pathlib import Path

import pytest

from coding_study.application.attempt_status import (
    DONE_NEXT,
    TEST_NEXT,
    AttemptStanding,
    HintCount,
    OpenLevel,
    attempt_status,
)
from coding_study.application.environment import Environment
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.application.start_item import ItemStartRequest, start_item_attempt
from coding_study.domain.attempts import RunRecord
from coding_study.domain.items import EntryKind
from coding_study.domain.judging import Tally
from coding_study.domain.problem import Language, Track
from tests.fakes import NOW, FakeStubGenerator, FakeToolchains, make_environment, repository_root
from tests.helpers import FIXTURE_TRACKS

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
PRACTICE = FIXTURES / "practice" / "problems"
PHASE4 = FIXTURES / "phase4" / "problems"
TWO_SUM_CASES = 4
LEVEL_STORE_CASES = 12
TOOLCHAINS = FakeToolchains(stub_generators={Language.PYTHON: FakeStubGenerator()})


def started(environment: Environment, slug: str) -> Environment:
    start_attempt(environment, StartRequest(slug, Language.PYTHON))
    return environment


@pytest.fixture
def function(tmp_path) -> Environment:
    root = repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS)
    return started(make_environment(root, toolchains=TOOLCHAINS), "two-sum")


@pytest.fixture
def progressive(tmp_path) -> Environment:
    root = repository_root(tmp_path, PHASE4)
    return started(make_environment(root, toolchains=TOOLCHAINS), "level-store")


@pytest.fixture
def item(tmp_path) -> Environment:
    environment = make_environment(repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS))
    start_item_attempt(environment, ItemStartRequest("url-shortener"))
    return environment


def status(environment: Environment) -> AttemptStanding:
    return attempt_status(environment, None, None)


def record_run(environment: Environment, passed: int, total: int) -> RunRecord:
    attempt = environment.progress.active_attempt()
    assert attempt is not None
    run = RunRecord(attempt.id, NOW, "abc", Tally(total=total, passed=passed), 700)
    environment.progress.add_test_run(run)
    return run


def unlock(environment: Environment, level: int) -> None:
    attempt = environment.progress.active_attempt()
    assert attempt is not None
    environment.progress.update_attempt(replace(attempt, level_unlocked=level))


# function problems


def test_a_function_problem_is_of_its_kind_and_track(function):
    found = status(function)
    assert (found.kind, found.track) == (EntryKind.FUNCTION, Track.DSA)


def test_a_function_problems_file_is_its_stub(function):
    assert status(function).file == "python/practice/two_sum.py"


def test_a_function_problem_counts_its_hints(function):
    assert status(function).hints == HintCount(0, 2, None)


def test_a_function_problem_has_no_levels(function):
    found = status(function)
    assert (found.levels, found.opened) == (None, ())


def test_a_function_problem_has_no_project_standing(function):
    assert status(function).project is None


def test_a_function_problem_shows_the_latest_test_run(function):
    run = record_run(function, 3, TWO_SUM_CASES)
    assert status(function).last_test_run == run


def test_before_a_run_the_next_step_is_testing(function):
    assert status(function).next_step == TEST_NEXT


def test_after_a_run_that_failed_a_case_the_next_step_is_testing(function):
    record_run(function, 3, TWO_SUM_CASES)
    assert status(function).next_step == TEST_NEXT


def test_after_a_run_of_some_cases_the_next_step_is_testing(function):
    record_run(function, 2, 2)
    assert status(function).next_step == TEST_NEXT


def test_after_a_run_that_passed_every_case_the_next_step_is_done(function):
    record_run(function, TWO_SUM_CASES, TWO_SUM_CASES)
    assert status(function).next_step == DONE_NEXT


# progressive problems


def test_a_progressive_problem_shows_its_open_levels_without_times(progressive):
    unlock(progressive, 2)
    assert status(progressive).opened == (
        OpenLevel(1, "Put and get", None),
        OpenLevel(2, "Remove and size", None),
    )


def test_a_progressive_problem_counts_its_levels(progressive):
    levels = status(progressive).levels
    assert levels is not None
    assert (levels.unlocked, levels.last) == (1, 3)


def test_a_pass_of_the_open_levels_only_leaves_testing_next(progressive):
    record_run(progressive, 4, 4)
    assert status(progressive).next_step == TEST_NEXT


def test_a_pass_of_every_level_makes_done_next(progressive):
    unlock(progressive, 3)
    record_run(progressive, LEVEL_STORE_CASES, LEVEL_STORE_CASES)
    assert status(progressive).next_step == DONE_NEXT


# items


def test_an_item_is_of_the_item_kind_on_its_track(item):
    found = status(item)
    assert (found.kind, found.track) == (EntryKind.ITEM, Track.SYSTEM_DESIGN)


def test_an_items_file_is_its_notes(item):
    assert status(item).file == "notes/system-design/url-shortener.md"


def test_an_item_points_at_its_prompt(item):
    assert status(item).statement == ".statements/url-shortener.md"


def test_an_item_has_no_hints(item):
    assert status(item).hints == HintCount(0, 0, None)


def test_an_item_has_no_levels_runs_or_project(item):
    found = status(item)
    assert (found.levels, found.last_test_run, found.project) == (None, None, None)


def test_an_items_next_step_is_the_notes_then_the_solution(item):
    assert status(item).next_step == "answer in the notes, then cstudy solution url-shortener"
