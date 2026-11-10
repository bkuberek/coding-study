"""`cstudy test --events` and `--json` on a service project, through a fake engine and fake HTTP
clients (docs/specs/service-projects.md#what-you-see): the stack's stages as they come, one result
for `commands.test` with its output streamed before it, each visible case of the unlocked levels,
and the document `--json` prints."""

import json
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from coding_study.application.http_grading_ports import StackClients, StackEndpoints
from coding_study.domain.docker_engine import EngineState, EngineStatus
from coding_study.domain.http_grading import HttpResponse
from coding_study.domain.sandbox import CommandOutcome, StackStartError, StartupFailure
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import start, submit
from coding_study.entrypoints.commands import test as test_command
from coding_study.entrypoints.shared import ExitCode
from tests.application.http_grading_fakes import FakeApp, FakeMockControl
from tests.fakes import make_environment
from tests.helpers import SCHEMAS_DIRECTORY
from tests.sandbox_fakes import FakeSandbox
from tests.service_problems import (
    FOLDER,
    SLUG,
    make_content,
    meta_document,
    write_cases,
    write_problem,
)

runner = CliRunner()
EVENTS_SCHEMA = json.loads((SCHEMAS_DIRECTORY / "events.schema.json").read_text(encoding="utf-8"))
OK_BODY = {"status": 200, "body": {"ok": True}}
RIGHT = HttpResponse(200, {}, b'{"ok": true}', 5_000_000)
WRONG = HttpResponse(500, {}, b"{}", 5_000_000)
COMMAND_TEST = "commands.test"
LEVELS = [{"level": 1, "title": "One"}, {"level": 2, "title": "Two"}]


def case(case_id: str, level: int, path: str, **fields: object) -> dict[str, object]:
    request = {"method": "GET", "path": path}
    return {"id": case_id, "level": level, "request": request, "expected": OK_BODY, **fields}


CASES = [
    case("v1", 1, "/a", visible=True),
    case("h1", 1, "/a"),
    case("v2", 2, "/b", visible=True),
]


@pytest.fixture
def engine() -> FakeSandbox:
    return FakeSandbox(exec_outcome=CommandOutcome(0, "ok 1 - rooms\nok 2 - slots\n"))


@pytest.fixture
def app() -> FakeApp:
    return FakeApp([], answers={"/a": RIGHT, "/b": RIGHT})


@pytest.fixture
def environment(tmp_path, monkeypatch, engine, app):
    root = make_content(tmp_path)
    document = meta_document()
    document["levels"] = LEVELS
    write_problem(root, document)
    write_cases(root, CASES)

    def clients(_endpoints: StackEndpoints) -> StackClients:
        return StackClients(app, FakeMockControl([]))

    built = make_environment(root, sandbox=engine, stack_clients=clients)
    for module in (start, test_command, submit):
        monkeypatch.setattr(module, "load_environment", lambda *_: built)
    (root / FOLDER / "node_modules").mkdir(parents=True)
    runner.invoke(cli.app, ["start", SLUG, "--no-open", "--yes"])
    return built


def cs(*arguments: str):
    return runner.invoke(cli.app, list(arguments))


def events(*arguments: str) -> list[dict[str, Any]]:
    lines = cs("test", SLUG, "--events", *arguments).stdout.splitlines()
    return [json.loads(line) for line in lines]


def types(found: list[dict[str, Any]]) -> list[str]:
    return [event["type"] for event in found]


def stack_states(found: list[dict[str, Any]]) -> list[str]:
    return [event["stack"] for event in found if event["type"] == "output" and "stack" in event]


def only(found: list[dict[str, Any]], event_type: str) -> dict[str, Any]:
    [event] = [event for event in found if event["type"] == event_type]
    return event


def test_every_event_meets_the_schema(environment):
    validator = Draft202012Validator(EVENTS_SCHEMA)

    for event in events():
        validator.validate(event)


def test_the_stream_starts_with_the_run_and_ends_with_its_end(environment):
    found = types(events())

    assert (found[0], found[-1]) == ("run_start", "run_end")


def test_the_start_names_a_test_of_the_open_levels(environment):
    started = events()[0]

    assert (started["command"], started["slug"], started["levels"]["up_to"]) == ("test", SLUG, 1)


def test_the_stack_reports_its_stages_in_order(environment):
    assert stack_states(events()) == ["starting", "ready", "stopped"]


def test_an_install_the_lock_asks_for_is_the_installing_stage(environment):
    (environment.root / FOLDER / "pnpm-lock.yaml").write_text("changed\n")

    assert stack_states(events())[0] == "installing"


def test_a_stopped_engine_starts_first_as_the_docker_stage(environment, engine):
    engine.engine = EngineState(EngineStatus.STOPPED)

    assert stack_states(events())[0] == "docker"


def test_ready_carries_the_startup_apart(environment):
    ready = next(event for event in events() if event.get("stack") == "ready")

    assert ready["startup_s"] == 2.5


def test_the_test_command_starts_before_its_output_and_ends_after_it(environment):
    found = events()
    texts = [event.get("text") or event.get("id") for event in found]

    start_at = texts.index(COMMAND_TEST)
    assert start_at < texts.index("ok 1 - rooms") < texts.index("ok 2 - slots")
    assert found[start_at]["type"] == "test_start"


def test_a_passing_test_command_is_one_passing_result(environment):
    result = only(events(), "test_result")

    assert (result["id"], result["status"]) == (COMMAND_TEST, "pass")


def test_a_failing_test_command_says_its_exit_and_keeps_its_output(environment, engine):
    engine.exec_outcome = CommandOutcome(1, "not ok 1 - rooms\n")

    result = only(events(), "test_result")

    assert (result["status"], result["message"]) == ("fail", "exited with 1")
    assert "not ok 1 - rooms" in result["stdout"]


def test_a_test_command_out_of_time_is_a_timeout(environment, engine):
    engine.exec_outcome = CommandOutcome(137, "", timed_out=True)

    result = only(events(), "test_result")

    assert (result["status"], result["message"]) == ("timeout", "did not finish within 120 s")


def test_each_visible_case_of_the_open_levels_starts_and_is_judged(environment):
    found = events()

    started = [event["id"] for event in found if event["type"] == "case_start"]
    judged = [(event["id"], event["status"]) for event in found if event["type"] == "case_result"]
    assert (started, judged) == (["v1"], [("v1", "pass")])


def test_the_cases_come_after_the_test_command(environment):
    found = types(events())

    assert found.index("test_result") < found.index("case_start")


def test_the_end_carries_the_json_document(environment):
    end = events()[-1]

    assert end["outcome"] == "passed"
    assert end["summary"]["tests"][0]["id"] == COMMAND_TEST


def test_a_failing_case_fails_the_run(environment, app):
    app.answers["/a"] = WRONG

    end = events()[-1]

    assert (end["outcome"], end["exit_code"]) == ("failed", ExitCode.FAILURES)


def test_code_that_keeps_the_stack_from_ready_is_a_load_failure(environment, engine):
    engine.start_error = StackStartError(StartupFailure.APP_EXITED, "your app exited", "tail\n")

    found = events()

    assert stack_states(found) == ["starting", "failed", "stopped"]
    assert found[-1]["outcome"] == "load_failed"
    assert found[-1]["summary"]["load_error"]["message"] == "your app exited"


def test_docker_missing_ends_the_stream_with_its_message(environment, engine):
    engine.engine = EngineState(EngineStatus.NOT_INSTALLED)

    end = events()[-1]

    assert (end["outcome"], end["exit_code"]) == ("error", ExitCode.ENVIRONMENT_ERROR)
    assert "docs.docker.com" in end["message"]


def test_json_prints_the_document_with_the_two_clocks_apart(environment):
    document = json.loads(cs("test", SLUG, "--json").stdout)

    assert document["startup_s"] == 2.5
    assert document["duration_s"] < 2.5


def test_json_keeps_progress_off_standard_output(environment):
    result = cs("test", SLUG, "--json")

    assert "the stack is ready" in result.stderr
    assert json.loads(result.stdout)["outcome"] == "passed"


def test_json_exits_as_the_report_does(environment, engine):
    engine.exec_outcome = CommandOutcome(1, "not ok\n")

    assert cs("test", SLUG, "--json").exit_code == ExitCode.FAILURES


@pytest.mark.parametrize("flag", [("--case", "v1"), ("--level", "1"), ("--typecheck",)])
def test_the_flags_of_a_native_run_still_exit_3_with_events(environment, flag):
    result = cs("test", SLUG, "--events", *flag)

    assert result.exit_code == ExitCode.USAGE_ERROR
    assert flag[0] in result.stderr


def test_submit_events_report_the_stacks_stages(environment):
    found = [json.loads(line) for line in cs("submit", SLUG, "--events").stdout.splitlines()]

    assert stack_states(found) == ["starting", "ready", "stopped"]
