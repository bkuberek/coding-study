"""`cstudy dev --events` through a fake engine and a fake mock control interface
(docs/specs/service-projects.md#web-ui): the dev stack as JSON events for the Web UI, and each line
of standard input a scenario to switch a mock server to while the stack runs."""

import json
import sys
import time
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from coding_study.application.http_grading_ports import StackClients, StackEndpoints
from coding_study.domain.sandbox import CommandOutcome, StackStartError, StartupFailure
from coding_study.entrypoints import cli
from coding_study.entrypoints.commands import dev, start
from coding_study.entrypoints.shared import ExitCode
from tests.application.http_grading_fakes import FakeApp, FakeMockControl
from tests.fakes import make_environment
from tests.helpers import SCHEMAS_DIRECTORY
from tests.sandbox_fakes import FakeSandbox
from tests.service_problems import (
    CONFIG,
    FOLDER,
    SLUG,
    make_content,
    meta_document,
    write_mock,
    write_problem,
)

runner = CliRunner()
DEV_SCHEMA = json.loads((SCHEMAS_DIRECTORY / "dev-events.schema.json").read_text(encoding="utf-8"))
SWITCH_WAIT_S = 10.0
OUTAGE = json.dumps({"mock": "room-vendor", "scenario": "outage"})


@pytest.fixture
def journal() -> list[str]:
    return []


@pytest.fixture
def engine() -> FakeSandbox:
    return FakeSandbox(control_port=5001, app_lines=("listening on 8000",))


@pytest.fixture
def environment(tmp_path, monkeypatch, engine, journal):
    root = make_content(tmp_path)
    write_problem(root, meta_document(mocks=[{"name": "room-vendor", "config": CONFIG}]))
    write_mock(root)

    def clients(_endpoints: StackEndpoints) -> StackClients:
        return StackClients(FakeApp(journal), FakeMockControl(journal))

    built = make_environment(root, sandbox=engine, stack_clients=clients)
    for module in (start, dev):
        monkeypatch.setattr(module, "load_environment", lambda *_: built)
    (root / FOLDER / "node_modules").mkdir(parents=True)
    runner.invoke(cli.app, ["start", SLUG, "--no-open", "--yes"])
    return built


def stop_with_ctrl_c() -> None:
    raise KeyboardInterrupt


def stop_once_switched(switches: int = 1):
    """Ctrl-C once the stream wrote `switches` scenario events, which the runner's captured
    standard output holds."""

    def stop() -> None:
        deadline = time.monotonic() + SWITCH_WAIT_S
        while printed().count('"type": "scenario"') < switches and time.monotonic() < deadline:
            time.sleep(0.01)
        raise KeyboardInterrupt

    return stop


def printed() -> str:
    return sys.stdout.buffer.getvalue().decode()  # pyright: ignore[reportAttributeAccessIssue, reportUnknownMemberType, reportUnknownVariableType]


def streamed(*arguments: str, stdin: str = "") -> tuple[int, list[dict[str, Any]]]:
    result = runner.invoke(cli.app, ["dev", SLUG, "--events", *arguments], input=stdin)
    return result.exit_code, [json.loads(line) for line in result.stdout.splitlines()]


def of_type(events: list[dict[str, Any]], event_type: str) -> list[dict[str, Any]]:
    return [event for event in events if event["type"] == event_type]


def test_every_event_meets_the_schema(environment, engine):
    engine.on_follow = stop_with_ctrl_c
    validator = Draft202012Validator(DEV_SCHEMA)

    for event in streamed()[1]:
        validator.validate(event)


def test_the_stack_reports_its_stages(environment, engine):
    engine.on_follow = stop_with_ctrl_c

    events = streamed()[1]

    stages = [event["stack"] for event in of_type(events, "output") if "stack" in event]
    assert stages == ["starting", "ready", "stopped"]


def test_ready_names_the_app_url_and_each_mock_servers_visible_scenarios(environment, engine):
    engine.on_follow = stop_with_ctrl_c

    [ready] = of_type(streamed()[1], "dev_ready")

    assert ready["app_url"] == "http://127.0.0.1:56223"
    assert ready["mocks"] == [{"name": "room-vendor", "scenario": None, "scenarios": ["outage"]}]


def test_ready_names_the_scenario_a_mock_server_started_with(environment, engine):
    engine.on_follow = stop_with_ctrl_c

    [ready] = of_type(streamed("--scenario", "room-vendor=outage")[1], "dev_ready")

    assert ready["mocks"][0]["scenario"] == "outage"


def test_each_line_the_app_prints_is_an_event(environment, engine):
    engine.on_follow = stop_with_ctrl_c

    assert [event["text"] for event in of_type(streamed()[1], "app")] == ["listening on 8000"]


def test_ctrl_c_ends_the_stream_stopped_with_exit_0(environment, engine):
    engine.on_follow = stop_with_ctrl_c

    exit_code, events = streamed()

    assert (exit_code, events[-1]["type"], events[-1]["outcome"]) == (0, "dev_end", "stopped")


def test_an_app_that_ends_ends_the_stream_with_exit_2(environment, engine):
    engine.app_ended = CommandOutcome(3, "boom\n")

    exit_code, events = streamed()

    assert (exit_code, events[-1]["outcome"]) == (ExitCode.USER_CODE_ERROR, "app_exited")
    assert "exited with code 3" in events[-1]["message"]


def test_an_app_that_will_not_start_ends_with_its_output(environment, engine):
    engine.start_error = StackStartError(StartupFailure.APP_EXITED, "your app exited", "boom")

    exit_code, events = streamed()

    assert (exit_code, events[-1]["outcome"]) == (ExitCode.USER_CODE_ERROR, "load_failed")
    assert events[-1]["output"] == "boom"


def test_a_refusal_before_the_stack_starts_ends_the_stream_with_its_message(environment):
    exit_code, events = streamed("--scenario", "nobody=outage")

    assert (exit_code, events[-1]["outcome"]) == (ExitCode.USAGE_ERROR, "error")
    assert "nobody" in events[-1]["message"]


def test_a_line_of_standard_input_switches_a_scenario(environment, engine, journal):
    engine.on_follow = stop_once_switched()

    events = streamed(stdin=f"{OUTAGE}\n")[1]

    assert journal == ["scenario room-vendor=outage"]
    assert of_type(events, "scenario") == [
        {
            "type": "scenario",
            "version": 1,
            "mock": "room-vendor",
            "scenario": "outage",
            "message": None,
        }
    ]


def test_a_null_scenario_sets_none(environment, engine, journal):
    engine.on_follow = stop_once_switched()
    back = json.dumps({"mock": "room-vendor", "scenario": None})

    events = streamed("--scenario", "room-vendor=outage", stdin=f"{back}\n")[1]

    assert of_type(events, "scenario")[0]["scenario"] is None


def test_a_hidden_scenario_is_refused_and_changes_nothing(environment, engine, journal):
    hidden = json.dumps({"mock": "room-vendor", "scenario": "rate_limited"})
    engine.on_follow = stop_once_switched()

    events = streamed(stdin=f"{hidden}\n")[1]

    [refused] = of_type(events, "scenario")
    assert (refused["scenario"], "outage" in refused["message"]) == (None, True)
    assert journal == []


def test_a_line_that_is_no_switch_is_refused(environment, engine, journal):
    engine.on_follow = stop_once_switched()

    [refused] = of_type(streamed(stdin="scenario please\n")[1], "scenario")

    assert refused["message"].startswith("not a scenario switch")
