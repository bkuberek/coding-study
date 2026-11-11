"""Mastery per level in `cstudy list`, `cstudy history` and `cstudy status`
(docs/specs/progress-and-scheduling.md#mastery-per-level): a problem whose level 2 of 3 is
mastered, and whose latest pass reached level 3 once, reads mastered through level 2 and passed
through level 3."""

import json
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.application.environment import Environment
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.attempts import AttemptMode, AttemptStatus, Grade, NewAttempt
from coding_study.domain.problem import Language
from coding_study.domain.scheduling import LevelReview, ReviewState, ScheduleEntry
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import history, list_problems, status
from tests.fakes import NOW, FakeStubGenerator, FakeToolchains, make_environment, repository_root

runner = CliRunner()
PHASE4 = Path(__file__).resolve().parents[2] / "fixtures" / "phase4" / "problems"
SLUG = "level-store"
RECALLED = ReviewState(interval_days=45, reps=4)
LEARNING = ReviewState(interval_days=3, reps=1)


@pytest.fixture
def environment(tmp_path, monkeypatch) -> Environment:
    toolchains = FakeToolchains(stub_generators={Language.PYTHON: FakeStubGenerator()})
    environment = make_environment(repository_root(tmp_path, PHASE4), toolchains=toolchains)
    for module in (history, status):
        monkeypatch.setattr(module, "load_environment", lambda *_: environment)
    monkeypatch.setattr(list_problems, "load_catalog_environment", lambda *_: environment)
    _mastered_through_2_passed_through_3(environment)
    return environment


def _mastered_through_2_passed_through_3(environment: Environment) -> None:
    attempt = environment.progress.add_attempt(
        NewAttempt(SLUG, Language.PYTHON, AttemptMode.REVIEW, NOW)
    )
    environment.progress.update_attempt(
        replace(
            attempt,
            status=AttemptStatus.PASSED,
            ended_at=NOW + timedelta(minutes=30),
            rating=None,
            grade=Grade.OK,
            levels_passed=3,
            levels_total=3,
        )
    )
    levels = (LevelReview(2, RECALLED, Grade.OK), LevelReview(3, LEARNING, Grade.OK))
    environment.progress.save_schedule_entry(
        ScheduleEntry(SLUG, RECALLED, date(2026, 12, 8), Grade.OK, NOW, levels)
    )


def output(*arguments: str) -> list[str]:
    return runner.invoke(cli.app, list(arguments)).output.splitlines()


def document(*arguments: str):
    return json.loads(runner.invoke(cli.app, [*arguments, "--json"]).stdout)


def test_the_list_writes_the_level_mastered_in_its_status_column(environment):
    row = next(line for line in output("list") if SLUG in line)
    assert "  mastered 2/3  " in row


def test_the_list_json_gives_the_levels_passed_and_mastered(environment):
    entry = next(found for found in document("list")["entries"] if found["slug"] == SLUG)
    assert (entry["status"], entry["levels"]) == (
        "mastered",
        {"last": 3, "passed": 3, "mastered": 2},
    )


def test_a_problem_without_levels_has_none_in_the_list_json(environment):
    entries = document("list")["entries"]
    assert all(entry["levels"] is None for entry in entries if entry["kind"] != "progressive")


def test_the_history_header_reads_mastered_through_level_2(environment):
    assert output("history", SLUG)[0].endswith(" · mastered through level 2 of 3")


def test_the_history_json_gives_the_levels_mastered(environment):
    assert document("history", SLUG)["levels"]["mastered"] == 2


def test_status_reads_mastered_through_2_and_passed_through_3(environment):
    start_attempt(environment, StartRequest(SLUG, Language.PYTHON))
    lines = output("status")
    assert (
        next(line for line in lines if line.startswith("passed")),
        next(line for line in lines if line.startswith("mastered")),
    ) == ("passed     through level 3 of 3", "mastered   through level 2 of 3")


def test_status_json_gives_the_levels_mastered(environment):
    start_attempt(environment, StartRequest(SLUG, Language.PYTHON))
    assert document("status")["levels"]["mastered"] == 2
