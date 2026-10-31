"""`cstudy test --events` on a concurrent problem: its sequential cases, then each stress run as
it starts and ends, and each stress case and variant graded right after its last run
(docs/specs/cli.md#event-stream)."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from coding_study.application.ports import CaseListener, RunnerLaunch
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.problem import Language
from coding_study.domain.runs import RunReport, RunRequest
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import test as test_command
from tests.concurrency_fakes import duplicating, queue, stalling
from tests.fakes import (
    Answer,
    FakeLanguageRunner,
    FakeStubGenerator,
    FakeToolchains,
    ScriptedRunnerProcess,
    make_environment,
    repository_root,
)
from tests.helpers import CONCURRENCY_PROBLEMS, SCHEMAS_DIRECTORY

runner = CliRunner()
STRESS_TYPES = {"stress_run_start", "stress_run", "stress_result"}
VALIDATOR = Draft202012Validator(
    json.loads((SCHEMAS_DIRECTORY / "events.schema.json").read_text(encoding="utf-8"))
)


class UntoldRunProcess(ScriptedRunnerProcess):
    """Tells the listener of every case but one stress run, which only the report holds, as a
    run the runner never got to report while it ran."""

    def __init__(self, answer: Answer, untold: str) -> None:
        super().__init__(answer)
        self._untold = untold

    def run(
        self, launch: RunnerLaunch, request: RunRequest, listener: CaseListener | None = None
    ) -> RunReport:
        return super().run(launch, request, _Muffled(listener, self._untold) if listener else None)


class _Muffled:
    def __init__(self, listener: CaseListener, untold: str) -> None:
        self._listener = listener
        self._untold = untold

    def case_started(self, job_id: str, case_id: str) -> None:
        if case_id != self._untold:
            self._listener.case_started(job_id, case_id)

    def case_finished(self, job_id: str, report) -> None:
        if report.case_id != self._untold:
            self._listener.case_finished(job_id, report)


def environment_for(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, process) -> None:
    toolchains = FakeToolchains(
        {Language.PYTHON: FakeLanguageRunner()}, {Language.PYTHON: FakeStubGenerator()}
    )
    environment = make_environment(
        repository_root(tmp_path, CONCURRENCY_PROBLEMS),
        toolchains=toolchains,
        runner_process=process,
    )
    monkeypatch.setattr(test_command, "load_environment", lambda *_: environment)
    start_attempt(environment, StartRequest("bounded-blocking-queue", Language.PYTHON))


@pytest.fixture
def scripted(tmp_path, monkeypatch):
    def scripted_with(answer: Answer) -> None:
        root = tmp_path / answer.__name__
        environment_for(root, monkeypatch, ScriptedRunnerProcess(answer))

    return scripted_with


def events(*arguments: str) -> list[dict]:
    result = runner.invoke(cli.app, ["test", *arguments, "--events"])
    return [json.loads(line) for line in result.stdout.splitlines()]


def types(found: list[dict]) -> list[str]:
    return [event["type"] for event in found]


def of_type(found: list[dict], event_type: str) -> list[dict]:
    return [event for event in found if event["type"] == event_type]


def test_stress_runs_follow_the_sequential_cases_and_each_slot_is_graded_after_its_runs(
    scripted,
):
    scripted(queue)
    one_slot = [*(["stress_run_start", "stress_run"] * 3), "stress_result"]
    assert types(events()) == [
        "run_start",
        *(["case_start", "case_result"] * 6),
        *one_slot,
        *one_slot,
        "run_end",
    ]


def test_the_start_plans_the_stress_runs(scripted):
    scripted(queue)
    assert events("--stress", "2")[0]["planned"] == {
        "cases": 6,
        "visible": 2,
        "hidden": 4,
        "generated": 0,
        "oracle_inputs": 0,
        "stress": {"cases": 2, "variants": 1, "runs": 2},
    }


def test_a_started_stress_run_names_its_case_variant_run_and_seed(scripted):
    scripted(queue)
    assert of_type(events(), "stress_run_start")[1] == {
        "type": "stress_run_start",
        "version": 1,
        "id": "s1",
        "variant": "thread",
        "run": 1,
        "seed": 1001,
    }


def test_a_passing_stress_run_has_no_reasons(scripted):
    scripted(queue)
    first = of_type(events(), "stress_run")[0]
    assert (first["status"], first["reasons"], first["duration_ns"]) == ("pass", [], 2_000_000)


def test_a_failing_stress_run_gives_its_reasons_as_the_report_does(scripted):
    scripted(duplicating)
    first = of_type(events("--case", "s1", "--stress", "1"), "stress_run")[0]
    assert (first["status"], first["reasons"]) == (
        "fail",
        [
            "equal_multisets put.arg0 vs take: 1 missing (1000000), 1 extra (0)",
            "distinct take: 0 (2 times)",
        ],
    )


def test_a_stress_result_is_the_json_documents_stress_case(scripted):
    scripted(stalling)
    arguments = ("--case", "s2", "--stress", "2")
    document = json.loads(runner.invoke(cli.app, ["test", *arguments, "--json"]).stdout)
    (graded,) = of_type(events(*arguments), "stress_result")
    assert graded == {"type": "stress_result", "version": 1} | document["stress"][0]


def test_the_end_carries_the_json_document(scripted):
    scripted(duplicating)
    document = json.loads(runner.invoke(cli.app, ["test", "--json"]).stdout)
    assert events()[-1]["summary"] | {"duration_s": None} == document | {"duration_s": None}


def test_a_stress_run_the_runner_never_reported_comes_after_the_others(tmp_path, monkeypatch):
    environment_for(tmp_path, monkeypatch, UntoldRunProcess(queue, "s1:thread:1"))
    runs = [(event["id"], event["run"]) for event in of_type(events(), "stress_run")]
    assert runs[-1] == ("s1", 1)


def test_a_slot_with_a_run_never_reported_is_graded_after_that_run(tmp_path, monkeypatch):
    environment_for(tmp_path, monkeypatch, UntoldRunProcess(queue, "s1:thread:1"))
    found = events()
    assert types(found)[-3:] == ["stress_run", "stress_result", "run_end"]


def test_every_event_matches_the_schema(scripted):
    found = []
    for answer in (queue, duplicating, stalling):
        scripted(answer)
        found += events()
    assert [event for event in found if not VALIDATOR.is_valid(event)] == []


def test_a_concurrent_run_writes_every_stress_event_type(scripted):
    scripted(queue)
    assert set(types(events())) >= STRESS_TYPES
