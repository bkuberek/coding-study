"""`cstudy status` output and JSON document (docs/specs/cli.md#cstudy-status)."""

import json
from dataclasses import replace
from datetime import timedelta

import pytest
from typer.testing import CliRunner

from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.attempts import RunRecord
from coding_study.domain.judging import Tally
from coding_study.domain.problem import Language
from coding_study.domain.submissions import LevelTally, SubmissionRecord
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import status as status_command
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import NOW, FakeStubGenerator, FakeToolchains, make_environment, repository_root
from tests.helpers import FIXTURE_PROBLEMS
from tests.project_fakes import (
    PROJECT_FOLDER,
    PROJECT_SLUG,
    ScriptedProjectProcess,
    project_environment,
)

runner = CliRunner()
OPENED = NOW.astimezone().strftime("%H:%M")


@pytest.fixture
def environment(tmp_path, monkeypatch):
    environment = project_environment(tmp_path, ScriptedProjectProcess())
    start_attempt(environment, StartRequest(PROJECT_SLUG))
    monkeypatch.setattr(status_command, "load_environment", lambda *_: environment)
    return environment


def attempt_id(environment) -> int:
    return environment.progress.active_attempt().id


def submit(environment, *levels: LevelTally, minutes: int = 0) -> None:
    environment.progress.add_submission(
        SubmissionRecord(
            attempt_id=attempt_id(environment),
            submitted_at=NOW + timedelta(minutes=minutes),
            code_hash="abc",
            graded_up_to=len(levels),
            every_level=True,
            levels=levels,
            tally=Tally(total=sum(level.total for level in levels)),
            duration_ms=300,
        )
    )


def cs_status(*arguments: str):
    return runner.invoke(cli.app, ["status", *arguments])


def lines(*arguments: str) -> list[str]:
    return cs_status(*arguments).output.splitlines()


def test_a_new_attempt_has_nothing_tested_or_submitted(environment):
    assert lines() == [
        f"{PROJECT_SLUG} · python · project · attempt 1 · new",
        f"level      1 of 2: Accounts and deposits (opened {OPENED})",
        "tested     not yet",
        "submitted  not yet",
        "files      0 changed, 0 added, 0 removed against the starter",
        "next       cstudy test --watch",
    ]


def test_status_exits_0(environment):
    assert cs_status().exit_code == ExitCode.SUCCESS


def test_the_timer_shows_elapsed_and_the_time_box(environment):
    attempt = environment.progress.active_attempt()
    environment.progress.update_attempt(replace(attempt, time_limit_s=5400))
    environment.clock.advance(timedelta(minutes=33, seconds=5))
    assert "timer      33:05 / 90:00" in lines()


def test_tested_shows_the_latest_run_and_its_age(environment):
    run = RunRecord(attempt_id(environment), NOW, "abc", Tally(total=4, passed=3), 700)
    environment.progress.add_test_run(run)
    environment.clock.advance(timedelta(minutes=1))
    assert "tested     3/4 passed, 1 min ago" in lines()


def test_submitted_shows_each_level_of_the_latest_submission(environment):
    submit(environment, LevelTally(1, 1, 1, 2, 2), LevelTally(2, 1, 1, 2, 1))
    environment.clock.advance(timedelta(minutes=2))
    assert "submitted  level 1 3/3 · level 2 2/3, 2 min ago" in lines()


def test_submitted_adds_a_better_earlier_count(environment):
    submit(environment, LevelTally(1, 1, 1, 2, 2), LevelTally(2, 1, 1, 2, 2), minutes=-5)
    submit(environment, LevelTally(1, 1, 1, 2, 2), LevelTally(2, 1, 1, 2, 1))
    assert "submitted  level 1 3/3 · level 2 2/3, just now · best level 2 3/3" in lines()


def test_after_a_submission_next_names_the_level_to_pass(environment):
    submit(environment, LevelTally(1, 1, 1, 2, 1))
    assert lines()[-1] == "next       cstudy submit once level 1 passes"


def test_another_kind_of_problem_exits_3(tmp_path, monkeypatch):
    toolchains = FakeToolchains(stub_generators={Language.PYTHON: FakeStubGenerator()})
    environment = make_environment(
        repository_root(tmp_path, FIXTURE_PROBLEMS), toolchains=toolchains
    )
    start_attempt(environment, StartRequest("two-sum", Language.PYTHON))
    monkeypatch.setattr(status_command, "load_environment", lambda *_: environment)
    result = cs_status()
    assert (result.exit_code, result.stderr) == (
        ExitCode.USAGE_ERROR,
        "error: cstudy status is for project problems\n",
    )


def test_json_describes_the_attempt(environment):
    found = json.loads(cs_status("--json").stdout)
    assert {key: found[key] for key in ("slug", "language", "attempt_id", "mode", "next")} == {
        "slug": PROJECT_SLUG,
        "language": "python",
        "attempt_id": 1,
        "mode": "new",
        "next": "cstudy test --watch",
    }


def test_json_lists_the_open_levels(environment):
    assert json.loads(cs_status("--json").stdout)["levels"] == {
        "unlocked": 1,
        "last": 2,
        "titles": ["Accounts and deposits"],
        "opened_at": [NOW.isoformat()],
    }


def test_json_has_the_latest_submission_and_the_best_per_level(environment):
    submit(environment, LevelTally(1, 1, 1, 2, 1))
    found = json.loads(cs_status("--json").stdout)
    assert (found["latest_submission"]["level_tallies"][0]["passed"], found["best_per_level"]) == (
        2,
        [{"level": 1, "passed": 2, "total": 3}],
    )


def test_json_without_runs_has_nulls(environment):
    found = json.loads(cs_status("--json").stdout)
    assert (found["timer"], found["last_test_run"], found["latest_submission"]) == (
        None,
        None,
        None,
    )


def edit_the_folder(environment) -> None:
    workspace = environment.workspace
    workspace.write_text(f"{PROJECT_FOLDER}/README.md", "# mine\n")
    workspace.write_text(f"{PROJECT_FOLDER}/bank/ledger.py", "LEDGER = []\n")
    workspace.write_text(f"{PROJECT_FOLDER}/tests/test_level_1.py", "# mine\n")
    workspace.absolute(f"{PROJECT_FOLDER}/pyproject.toml").unlink()


def test_files_counts_the_changes_against_the_starter(environment):
    edit_the_folder(environment)
    assert "files      1 changed, 1 added, 1 removed against the starter" in lines()


def test_json_files_lists_the_changes_against_the_starter(environment):
    edit_the_folder(environment)
    files = json.loads(cs_status("--json").stdout)["files"]
    assert {key: files[key] for key in ("changed", "added", "removed")} == {
        "changed": ["README.md"],
        "added": ["bank/ledger.py"],
        "removed": ["pyproject.toml"],
    }


def test_json_files_has_every_files_origin_and_state(environment):
    edit_the_folder(environment)
    assert json.loads(cs_status("--json").stdout)["files"]["entries"] == [
        {"path": "README.md", "origin": "starter", "level": None, "state": "modified"},
        {"path": "bank/bank.py", "origin": "starter", "level": None, "state": "unchanged"},
        {"path": "bank/ledger.py", "origin": "yours", "level": None, "state": "added"},
        {"path": "pyproject.toml", "origin": "starter", "level": None, "state": "deleted"},
        {"path": "tests/test_level_1.py", "origin": "level", "level": 1, "state": "modified"},
    ]
