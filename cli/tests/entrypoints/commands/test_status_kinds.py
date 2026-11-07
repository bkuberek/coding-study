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
from coding_study.domain.attempts import RunRecord
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
    }


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
        "next": "answer in the notes, then cstudy solution url-shortener",
    }
