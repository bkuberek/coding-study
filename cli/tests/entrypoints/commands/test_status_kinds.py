"""`cstudy status` on single-file problems and items (docs/specs/cli.md#cstudy-status)."""

import json
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.application.environment import Environment
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.application.start_item import ItemStartRequest, start_item_attempt
from coding_study.domain.attempts import AttemptStatus, RunRecord
from coding_study.domain.judging import Tally
from coding_study.domain.problem import Language
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import status as status_command
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import NOW, FakeStubGenerator, FakeToolchains, make_environment, repository_root
from tests.helpers import FIXTURE_TRACKS

runner = CliRunner()
FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
PRACTICE = FIXTURES / "practice" / "problems"
PHASE4 = FIXTURES / "phase4" / "problems"
TOOLCHAINS = FakeToolchains(stub_generators={Language.PYTHON: FakeStubGenerator()})
STUB = "python/practice/two_sum.py"
NOTES = "notes/system-design/url-shortener.md"


def use(monkeypatch: pytest.MonkeyPatch, environment: Environment) -> Environment:
    monkeypatch.setattr(status_command, "load_environment", lambda *_: environment)
    return environment


@pytest.fixture
def function(tmp_path, monkeypatch) -> Environment:
    root = repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS)
    environment = make_environment(root, toolchains=TOOLCHAINS)
    start_attempt(environment, StartRequest("two-sum", Language.PYTHON))
    return use(monkeypatch, environment)


@pytest.fixture
def progressive(tmp_path, monkeypatch) -> Environment:
    environment = make_environment(repository_root(tmp_path, PHASE4), toolchains=TOOLCHAINS)
    start_attempt(environment, StartRequest("level-store", Language.PYTHON))
    return use(monkeypatch, environment)


@pytest.fixture
def item(tmp_path, monkeypatch) -> Environment:
    environment = make_environment(repository_root(tmp_path, PRACTICE, FIXTURE_TRACKS))
    start_item_attempt(environment, ItemStartRequest("url-shortener"))
    return use(monkeypatch, environment)


def cs_status(*arguments: str):
    return runner.invoke(cli.app, ["status", *arguments])


def lines(*arguments: str) -> list[str]:
    return cs_status(*arguments).output.splitlines()


def document(*arguments: str):
    return json.loads(cs_status("--json", *arguments).stdout)


def reveal(environment: Environment) -> None:
    attempt = environment.progress.active_attempt()
    assert attempt is not None
    environment.progress.update_attempt(replace(attempt, solution_revealed=True))


# function problems


def test_a_function_problem_shows_its_stub_hints_and_tests(function):
    assert lines() == [
        "two-sum · python · function · attempt 1 · new",
        f"file       {STUB}",
        "hints      0 of 2",
        "tested     not yet",
        "next       cstudy test --watch",
    ]


def test_status_of_a_function_problem_exits_0(function):
    assert cs_status("two-sum").exit_code == ExitCode.SUCCESS


def test_a_function_problem_shows_its_timer_and_latest_run(function):
    attempt = function.progress.active_attempt()
    function.progress.update_attempt(replace(attempt, time_limit_s=1500))
    function.progress.add_test_run(RunRecord(1, NOW, "abc", Tally(total=4, passed=3), 700))
    function.clock.advance(timedelta(minutes=12, seconds=31))
    assert lines()[2:5] == [
        "timer      12:31 / 25:00",
        "hints      0 of 2",
        "tested     3/4 passed, 12 min ago",
    ]


def test_a_full_pass_points_to_done(function):
    function.progress.add_test_run(RunRecord(1, NOW, "abc", Tally(total=4, passed=4), 700))
    assert lines()[-1] == "next       cstudy done --rating easy|ok|hard"


def test_a_revealed_solution_is_graded_as_again(function):
    reveal(function)
    assert "solution   revealed, graded as again" in lines()


def test_json_describes_a_function_attempt(function):
    assert document() == {
        "slug": "two-sum",
        "kind": "function",
        "track": "dsa",
        "language": "python",
        "attempt_id": 1,
        "mode": "new",
        "started_at": NOW.isoformat(),
        "file": STUB,
        "hints": {"used": 0, "total": 2, "locked_until_level": None},
        "solution_revealed": False,
        "statement": ".statements/two-sum.md",
        "levels": None,
        "timer": None,
        "last_test_run": None,
        "latest_submission": None,
        "best_per_level": [],
        "files": None,
        "no_code_intelligence": None,
        "service": None,
        "next": "cstudy test --watch",
    }


def test_json_has_the_latest_test_run(function):
    function.progress.add_test_run(RunRecord(1, NOW, "abc", Tally(total=4, passed=3), 700))
    assert document()["last_test_run"] == {
        "ran_at": NOW.isoformat(),
        "total": 4,
        "passed": 3,
        "predates_level": None,
    }


# progressive problems


def test_a_progressive_problem_shows_its_level_without_an_opening_time(progressive):
    assert lines() == [
        "level-store · python · progressive · attempt 1 · new",
        "file       python/practice/level_store.py",
        "level      1 of 3: Put and get",
        "hints      0 of 1",
        "tested     not yet",
        "next       cstudy test --watch",
    ]


def test_json_lists_a_progressive_problems_levels_without_opening_times(progressive):
    assert document()["levels"] == {
        "unlocked": 1,
        "last": 3,
        "titles": ["Put and get"],
        "opened_at": [],
        "passed": 0,
        "best": None,
        "last_time": None,
        "try_level": None,
        "mastered": 0,
    }


def passed_before(environment: Environment, levels: int) -> None:
    """The attempt in progress ends passed through `levels` of 3; a new one starts."""
    attempt = environment.progress.active_attempt()
    assert attempt is not None
    environment.progress.update_attempt(
        replace(attempt, status=AttemptStatus.PASSED, levels_passed=levels, levels_total=3)
    )
    start_attempt(environment, StartRequest("level-store", Language.PYTHON))


def test_a_new_attempt_shows_the_level_to_try_and_the_levels_passed(progressive):
    passed_before(progressive, 2)
    assert lines()[2:5] == [
        "level      1 of 3: Put and get",
        "goal       last time: through level 2 of 3; try level 3",
        "passed     through level 2 of 3",
    ]


def test_after_every_level_only_the_levels_passed_show(progressive):
    passed_before(progressive, 3)
    assert lines()[2:4] == [
        "level      1 of 3: Put and get",
        "passed     through level 3 of 3",
    ]


def test_json_has_the_levels_passed_the_best_and_the_level_to_try(progressive):
    passed_before(progressive, 2)
    levels = document()["levels"]
    assert (levels["passed"], levels["best"], levels["last_time"], levels["try_level"]) == (
        0,
        2,
        2,
        3,
    )


def ran_through(environment: Environment, levels: int) -> None:
    """The attempt in progress opened the level after `levels` and its latest run passed them."""
    attempt = environment.progress.active_attempt()
    assert attempt is not None
    environment.progress.update_attempt(replace(attempt, level_unlocked=levels + 1))
    tally = Tally(total=4 * levels + 4, passed=4 * levels, failed=4)
    environment.progress.add_test_run(
        RunRecord(attempt.id, NOW, "hash", tally, 10, levels_passed=levels)
    )


def test_a_run_through_a_level_offers_done_as_a_pass(progressive):
    ran_through(progressive, 1)
    assert lines()[-1] == (
        "next       cstudy test --watch, or cstudy done --rating easy|ok|hard to pass "
        "through level 1 of 3"
    )


def test_json_has_the_levels_the_latest_run_passed(progressive):
    ran_through(progressive, 2)
    assert document()["levels"]["passed"] == 2


def test_a_mock_through_a_level_still_tests_on(tmp_path, monkeypatch):
    environment = make_environment(repository_root(tmp_path, PHASE4), toolchains=TOOLCHAINS)
    start_attempt(environment, StartRequest("level-store", Language.PYTHON, mock=True))
    use(monkeypatch, environment)
    ran_through(environment, 1)
    assert lines()[-1] == "next       cstudy test --watch"


# items


def test_an_item_shows_its_track_notes_and_next_step(item):
    assert lines() == [
        "url-shortener · system-design · attempt 1 · new",
        f"file       {NOTES}",
        "next       answer in the notes, then cstudy solution url-shortener",
    ]


def test_an_items_revealed_solution_keeps_its_grade(item):
    reveal(item)
    assert "solution   revealed" in lines()


def test_json_describes_an_item_attempt(item):
    assert document() == {
        "slug": "url-shortener",
        "kind": "item",
        "track": "system-design",
        "language": None,
        "attempt_id": 1,
        "mode": "new",
        "started_at": NOW.isoformat(),
        "file": NOTES,
        "hints": {"used": 0, "total": 0, "locked_until_level": None},
        "solution_revealed": False,
        "statement": ".statements/url-shortener.md",
        "levels": None,
        "timer": None,
        "last_test_run": None,
        "latest_submission": None,
        "best_per_level": [],
        "files": None,
        "no_code_intelligence": None,
        "service": None,
        "next": "answer in the notes, then cstudy solution url-shortener",
    }
