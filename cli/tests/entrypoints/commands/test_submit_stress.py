"""`cstudy submit` on a project with stress cases: its report, JSON document and events
(docs/specs/cli.md#cstudy-submit, #event-stream)."""

import json
from dataclasses import replace

import pytest
from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from coding_study.application.environment import Environment
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import submit as submit_command
from tests.helpers import SCHEMAS_DIRECTORY
from tests.project_fakes import (
    TALLY_SLUG,
    ScriptedProjectProcess,
    stress_project_environment,
    tally_answers,
)

runner = CliRunner()
HEADER = f"{TALLY_SLUG} · python · submit levels 1-2 of 2"
EVIDENCE = "stress runs found no race (not a proof of thread safety)"
STRESS_RUNS = 3


@pytest.fixture
def process() -> ScriptedProjectProcess:
    return ScriptedProjectProcess()


@pytest.fixture
def environment(tmp_path, monkeypatch, process) -> Environment:
    environment = stress_project_environment(tmp_path, process)
    process.answer = tally_answers(environment.problems.load(TALLY_SLUG))
    start_attempt(environment, StartRequest(TALLY_SLUG))
    open_level_2(environment)
    monkeypatch.setattr(submit_command, "load_environment", lambda *_: environment)
    return environment


def open_level_2(environment: Environment) -> None:
    attempt = environment.progress.active_attempt()
    assert attempt is not None
    environment.progress.update_attempt(replace(attempt, level_unlocked=2))


def racy(environment: Environment, process: ScriptedProjectProcess) -> None:
    process.answer = tally_answers(environment.problems.load(TALLY_SLUG), racy=True)


def as_mock(environment: Environment) -> None:
    start_attempt(environment, StartRequest(TALLY_SLUG, fresh=True, mock=True))
    open_level_2(environment)


def lines(*arguments: str) -> list[str]:
    return runner.invoke(cli.app, ["submit", *arguments]).output.splitlines()


def document() -> dict:
    return json.loads(runner.invoke(cli.app, ["submit", "--json"]).stdout)


def events() -> list[dict]:
    output = runner.invoke(cli.app, ["submit", "--events"]).stdout
    return [json.loads(line) for line in output.splitlines()]


def test_stress_cases_print_under_their_level_after_the_cases(environment):
    found = lines()
    assert found[:10] == [
        HEADER,
        "",
        "level 1  PASS     6/6 (2 visible, 4 hidden)",
        "level 2  PASS     8/8 (2 visible, 6 hidden)",
        "PASS     ex1   level 1",
        "PASS     ex2   level 1",
        "PASS     ex3   level 2",
        "PASS     ex4   level 2",
        "PASS     s1    level 2 · 3/3 runs · median 2.00ms",
        "PASS     s2    level 2 · 3/3 runs · median 2.00ms",
    ]


def test_a_pass_says_the_stress_runs_found_no_race(environment):
    found = lines()
    assert found[found.index("14/14 passed") + 1] == EVIDENCE


def test_a_failing_stress_case_lists_its_failing_runs_with_their_seeds(environment, process):
    racy(environment, process)
    found = lines()
    failing = found.index("FAIL     s1    level 2 · 0/3 runs passed")
    assert [line[:31] for line in found[failing + 1 : failing + 4]] == [
        "         run 0 · seed 1000  dis",
        "         run 1 · seed 1001  dis",
        "         run 2 · seed 1002  dis",
    ]


def test_a_failing_stress_case_fails_its_level_and_finds_a_race(environment, process):
    racy(environment, process)
    found = lines()
    assert "level 2  FAIL     7/8 (2 visible, 6 hidden)" in found
    assert EVIDENCE not in found


def test_a_mock_attempt_only_counts_failing_stress_cases(environment, process):
    as_mock(environment)
    racy(environment, process)
    found = lines()
    assert "level 2  FAIL     7/8 (2 visible, 6 hidden) · 1 hidden case failed" in found
    assert [line for line in found if line.startswith(("PASS     s", "FAIL     s"))] == []


def test_json_lists_each_stress_verdict_with_its_level(environment):
    stress = document()["stress"]
    assert [(entry["id"], entry["variant"], entry["level"]) for entry in stress] == [
        ("s1", "thread", 2),
        ("s2", "thread", 2),
    ]
    assert (stress[0]["status"], stress[0]["runs"], stress[0]["runs_passed"]) == ("pass", 3, 3)


def test_json_of_a_mock_attempt_leaves_stress_verdicts_out(environment):
    as_mock(environment)
    found = document()
    assert (found["stress"], found["level_tallies"][1]["hidden_total"]) == ([], 6)


def test_json_tallies_count_stress_verdicts_as_hidden_cases(environment):
    found = document()
    assert (found["tally"]["total"], found["level_tallies"][1]["hidden_passed"]) == (14, 6)


def test_stress_events_carry_their_level(environment):
    stress = [event for event in events() if event["type"].startswith("stress_")]
    assert len(stress) == 2 * (2 * STRESS_RUNS + 1)
    assert {event["level"] for event in stress} == {2}
    graded = [event for event in stress if event["type"] == "stress_result"]
    assert [(event["id"], event["status"]) for event in graded] == [("s1", "pass"), ("s2", "pass")]


def test_level_results_come_after_the_stress_results(environment):
    types = [event["type"] for event in events()]
    last_stress = max(index for index, kind in enumerate(types) if kind == "stress_result")
    assert last_stress < types.index("level_result")


def test_every_event_of_a_submission_with_stress_cases_fits_the_schema(environment):
    schema = json.loads((SCHEMAS_DIRECTORY / "events.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    assert [list(validator.iter_errors(event)) for event in events()] == [[]] * len(events())
