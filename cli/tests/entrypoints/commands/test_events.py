"""`cstudy test --events` and `cstudy submit --events` on a project problem: one JSON event per
line on standard output (docs/specs/cli.md#event-stream)."""

import json
from dataclasses import dataclass

import pytest
from jsonschema import Draft202012Validator
from typer.testing import CliRunner, Result

from coding_study.application.ports import (
    ProgressNotice,
    ProjectScope,
    RunnerLaunch,
    SuiteListener,
)
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.errors import RunnerStartError
from coding_study.domain.problem import Language
from coding_study.domain.runs import (
    CaseOutcome,
    Crashed,
    Raised,
    Returned,
    RunCase,
    RunJob,
    TimedOut,
    UserError,
)
from coding_study.domain.suite_runs import (
    AssertionFailed,
    Comparison,
    Passed,
    Skipped,
    SuiteJob,
    SuiteReport,
    SuiteTest,
)
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import submit as submit_command
from coding_study.entrypoints.commands import test as test_command
from coding_study.entrypoints.shared import ExitCode
from tests.fakes import FakeStubGenerator, FakeToolchains, make_environment, repository_root
from tests.helpers import FIXTURE_PROBLEMS, PROJECT_PROBLEMS, SCHEMAS_DIRECTORY
from tests.project_fakes import (
    PROJECT_SLUG,
    FakeProjectRunner,
    ScriptedProjectProcess,
    project_environment,
)

runner = CliRunner()
EVENTS_SCHEMA = json.loads((SCHEMAS_DIRECTORY / "events.schema.json").read_text(encoding="utf-8"))
CASES = json.loads(
    (PROJECT_PROBLEMS / "0001-bank-project-python" / "tests.json").read_text(encoding="utf-8")
)["cases"]
EXPECTED = {case["id"]: case["expected"] for case in CASES}
BROKEN = UserError(
    "SyntaxError", "invalid syntax", "tests/test_level_1.py:1 in <module>\nbank/bank.py:5"
)
NOTICE = "warming the project runner"
FAILED = SuiteTest("tests/test_level_1.py::test_ex1", AssertionFailed("assert -1 == 5", 1000))


def correct(job: RunJob, case: RunCase) -> CaseOutcome:
    return Returned(EXPECTED[case.id], 1000)


def wrong_on_h1(job: RunJob, case: RunCase) -> CaseOutcome:
    return Returned(["wrong"], 1000) if case.id == "h1" else correct(job, case)


@dataclass
class StoppingProcess(ScriptedProjectProcess):
    """Stops the suite with `stop` instead of reporting it."""

    stop: BaseException | None = None

    def run_suite(
        self, launch: RunnerLaunch, job: SuiteJob, listener: SuiteListener | None = None
    ) -> SuiteReport:
        if self.stop is not None:
            raise self.stop
        return ScriptedProjectProcess.run_suite(self, launch, job, listener)


@dataclass
class NoticingRunner(FakeProjectRunner):
    """Says what it is doing before it launches, as a runner that warms up does."""

    def prepare_project(self, scope: ProjectScope, notify: ProgressNotice) -> RunnerLaunch:
        notify(NOTICE)
        return FakeProjectRunner.prepare_project(self, scope, notify)


@pytest.fixture
def process() -> StoppingProcess:
    return StoppingProcess(answer=correct)


@pytest.fixture
def environment(tmp_path, monkeypatch, process):
    environment = project_environment(tmp_path, process)
    start_attempt(environment, StartRequest(PROJECT_SLUG))
    for command in (test_command, submit_command):
        monkeypatch.setattr(command, "load_environment", lambda *_: environment)
    return environment


def cs(*arguments: str) -> Result:
    return runner.invoke(cli.app, list(arguments))


def events(*arguments: str) -> list[dict]:
    return [json.loads(line) for line in cs(*arguments, "--events").stdout.splitlines()]


def types(*arguments: str) -> list[str]:
    return [event["type"] for event in events(*arguments)]


def last(*arguments: str) -> dict:
    return events(*arguments)[-1]


def first(event_type: str, *arguments: str) -> dict:
    return next(event for event in events(*arguments) if event["type"] == event_type)


def test_every_event_names_its_type_and_version_first(environment):
    assert {tuple(event)[:2] for event in events("test")} == {("type", "version")}


def test_every_event_is_version_1(environment):
    assert {event["version"] for event in events("submit")} == {1}


def test_a_test_run_starts_reports_each_test_as_it_starts_and_ends_then_ends(environment):
    assert types("test") == ["run_start", "test_start", "test_result", "run_end"]


def test_a_started_test_is_named(environment):
    assert first("test_start", "test") == {
        "type": "test_start",
        "version": 1,
        "id": "tests/test_level_1.py::test_ex1",
    }


def test_the_start_names_the_run(environment):
    assert events("test")[0] == {
        "type": "run_start",
        "version": 1,
        "command": "test",
        "slug": PROJECT_SLUG,
        "language": "python",
        "attempt_id": 1,
        "mode": "new",
        "levels": {"up_to": 1, "unlocked": 1, "last": 2},
    }


def test_a_test_result_is_the_json_documents_case(environment):
    assert first("test_result", "test") == {
        "type": "test_result",
        "version": 1,
        "id": "tests/test_level_1.py::test_ex1",
        "status": "pass",
        "duration_ns": 1000,
        "origin": "level",
        "level": 1,
    }


def test_the_end_carries_the_json_document(environment):
    document = json.loads(cs("test", "--json").stdout)
    end = last("test")
    assert end["summary"] | {"duration_s": None} == document | {"duration_s": None}


def test_the_end_says_why_a_suite_stopped_early(environment, process):
    process.stopped_early = "the runner was restarted 3 times"
    assert last("test")["summary"]["stopped_early"] == "the runner was restarted 3 times"


def test_a_passing_run_ends_passed_with_exit_code_0(environment):
    assert {key: last("test")[key] for key in ("outcome", "exit_code", "message")} == {
        "outcome": "passed",
        "exit_code": 0,
        "message": None,
    }


def test_a_failing_run_exits_as_its_end_says(environment, process):
    process.tests = (FAILED,)
    result = cs("test", "--events")
    end = json.loads(result.stdout.splitlines()[-1])
    assert (result.exit_code, end["outcome"], end["exit_code"]) == (1, "failed", 1)


def test_a_test_file_that_does_not_import_is_a_diagnostic(environment, process):
    process.tests = (SuiteTest("tests/test_level_1.py", Raised(BROKEN, 0)),)
    assert first("diagnostic", "test") == {
        "type": "diagnostic",
        "version": 1,
        "source": "load",
        "severity": "error",
        "file": "bank/bank.py",
        "line": 5,
        "column": None,
        "code": "SyntaxError",
        "message": "invalid syntax",
    }


def test_a_progress_notice_is_an_output_event(environment):
    environment.toolchains.runners[Language.PYTHON] = NoticingRunner()
    assert events("test")[1] == {"type": "output", "version": 1, "text": NOTICE}


def test_a_case_that_names_no_test_ends_the_stream_with_the_error(environment):
    end = last("test", "--case", "nope")
    assert {key: end[key] for key in ("outcome", "exit_code", "message", "summary")} == {
        "outcome": "error",
        "exit_code": ExitCode.USAGE_ERROR,
        "message": "no test matches --case nope",
        "summary": None,
    }


def test_an_error_after_the_start_still_reaches_standard_error(environment):
    result = cs("test", "--case", "nope", "--events")
    assert (result.exit_code, result.stderr) == (3, "error: no test matches --case nope\n")


def test_a_runner_that_does_not_start_ends_the_stream_with_exit_code_4(environment, process):
    process.stop = RunnerStartError("pytest is missing")
    result = cs("test", "--events")
    end = json.loads(result.stdout.splitlines()[-1])
    assert (result.exit_code, end["outcome"], end["exit_code"]) == (4, "error", 4)


def test_an_interrupted_run_ends_the_stream(environment, process):
    process.stop = KeyboardInterrupt()
    result = cs("test", "--events")
    end = json.loads(result.stdout.splitlines()[-1])
    assert (result.exit_code, end["outcome"], end["summary"]) == (130, "interrupted", None)


def test_a_locked_level_writes_no_event(environment):
    result = cs("test", "--level", "2", "--events")
    assert (result.exit_code, result.stdout) == (ExitCode.USAGE_ERROR, "")


@pytest.mark.parametrize("flag", ["--json", "--watch", "--debug"])
def test_events_exclude_the_other_outputs(environment, flag):
    result = cs("test", flag, "--events")
    assert (result.exit_code, result.stderr) == (3, f"error: --events excludes {flag}\n")


def test_events_are_for_project_problems(tmp_path, monkeypatch):
    toolchains = FakeToolchains(stub_generators={Language.PYTHON: FakeStubGenerator()})
    environment = make_environment(
        repository_root(tmp_path, FIXTURE_PROBLEMS), toolchains=toolchains
    )
    start_attempt(environment, StartRequest("two-sum", Language.PYTHON))
    monkeypatch.setattr(test_command, "load_environment", lambda *_: environment)
    result = cs("test", "--events")
    assert (result.exit_code, result.stderr) == (3, "error: --events is for project problems\n")


def test_a_submission_grades_each_case_as_it_starts_and_ends_then_opens_a_level(environment):
    assert types("submit") == [
        "run_start",
        *(["case_start", "case_result"] * 3),
        "level_result",
        "level_unlocked",
        "run_end",
    ]


def test_a_started_case_names_its_visibility_and_level(environment):
    assert first("case_start", "submit") == {
        "type": "case_start",
        "version": 1,
        "id": "ex1",
        "visible": True,
        "level": 1,
    }


def test_a_graded_case_is_the_json_documents_case(environment):
    assert first("case_result", "submit") == {
        "type": "case_result",
        "version": 1,
        "id": "ex1",
        "visible": True,
        "generated": False,
        "status": "pass",
        "duration_ns": 1000,
        "level": 1,
    }


def test_a_level_result_counts_the_level_with_its_status(environment, process):
    process.answer = wrong_on_h1
    assert first("level_result", "submit") == {
        "type": "level_result",
        "version": 1,
        "status": "fail",
        "level": 1,
        "total": 3,
        "passed": 2,
        "visible_total": 1,
        "visible_passed": 1,
        "hidden_total": 2,
        "hidden_passed": 1,
    }


def test_an_opened_level_names_its_methods_tests_and_statement(environment):
    assert first("level_unlocked", "submit") == {
        "type": "level_unlocked",
        "version": 1,
        "level": 2,
        "title": "Transfers",
        "methods": ["transfer(timestamp: int, source_id: str, target_id: str, amount: int) -> int"],
        "tests": {"path": "tests/test_level_2.py", "count": 1},
        "statement": f".statements/{PROJECT_SLUG}.md",
    }


def test_a_mock_submission_writes_no_hidden_case(environment, process):
    start_attempt(environment, StartRequest(PROJECT_SLUG, fresh=True, mock=True))
    process.answer = wrong_on_h1
    named = [event["id"] for event in events("submit") if event["type"].startswith("case_")]
    assert named == ["ex1", "ex1"]


def test_code_that_does_not_load_is_a_diagnostic_and_ends_load_failed(environment, process):
    process.load_error = BROKEN
    assert [(event["type"], event.get("outcome")) for event in events("submit")] == [
        ("run_start", None),
        ("diagnostic", None),
        ("level_result", None),
        ("run_end", "load_failed"),
    ]


def test_a_submission_exits_as_its_end_says(environment, process):
    process.load_error = BROKEN
    result = cs("submit", "--events")
    end = json.loads(result.stdout.splitlines()[-1])
    assert (result.exit_code, end["exit_code"]) == (2, 2)


def test_submit_events_exclude_json(environment):
    result = cs("submit", "--json", "--events")
    assert (result.exit_code, result.stderr) == (3, "error: --events excludes --json\n")


EVERY_OUTCOME = (
    SuiteTest("tests/test_level_1.py::test_ex1", Passed(1000, stdout="hi\n")),
    SuiteTest(
        "tests/test_level_1.py::test_ex2",
        AssertionFailed("assert -1 == 5", 1000, comparison=Comparison(5, -1)),
    ),
    SuiteTest("tests/test_mine.py::test_raises", Raised(UserError("KeyError", "'ivy'"), 1000)),
    SuiteTest("tests/test_mine.py::test_later", Skipped("not yet", 0)),
    SuiteTest("tests/test_mine.py::test_hangs", TimedOut(10_000)),
    SuiteTest("tests/test_mine.py::test_exits", Crashed(1, ("killed",))),
    SuiteTest("tests/test_broken.py", Raised(BROKEN, 0)),
)


def every_test_event(environment, process: StoppingProcess) -> list[dict]:
    environment.toolchains.runners[Language.PYTHON] = NoticingRunner()
    process.tests = EVERY_OUTCOME
    found = events("test")
    process.stop = RunnerStartError("pytest is missing")
    found += events("test")
    process.stop = KeyboardInterrupt()
    return found + events("test")


def every_submit_event(environment, process: StoppingProcess) -> list[dict]:
    environment.toolchains.runners[Language.PYTHON] = NoticingRunner()
    found = events("submit")
    process.answer = wrong_on_h1
    found += events("submit")
    process.load_error = BROKEN
    found += events("submit")
    start_attempt(environment, StartRequest(PROJECT_SLUG, fresh=True, mock=True))
    process.load_error = None
    return found + events("submit")


def test_the_events_schema_is_a_valid_schema():
    Draft202012Validator.check_schema(EVENTS_SCHEMA)


def test_every_event_of_cstudy_test_matches_the_schema(environment, process):
    validator = Draft202012Validator(EVENTS_SCHEMA)
    invalid = [
        event for event in every_test_event(environment, process) if not validator.is_valid(event)
    ]
    assert invalid == []


def test_every_event_of_cstudy_submit_matches_the_schema(environment, process):
    validator = Draft202012Validator(EVENTS_SCHEMA)
    invalid = [
        event for event in every_submit_event(environment, process) if not validator.is_valid(event)
    ]
    assert invalid == []


def test_the_schema_covers_every_event_type_the_commands_write(environment, process):
    written = {event["type"] for event in every_test_event(environment, process)}
    written |= {event["type"] for event in every_submit_event(environment, process)}
    assert written == {
        definition["$ref"].removeprefix("#/$defs/") for definition in EVENTS_SCHEMA["oneOf"]
    }


def test_the_schema_refuses_an_event_of_an_unknown_type():
    assert not Draft202012Validator(EVENTS_SCHEMA).is_valid({"type": "run_paused", "version": 1})
