"""The dev stack from the page (docs/specs/web-ui.md#dev-stack): `cstudy dev <slug> --events` as a
child of the server, one per attempt, its stream, its stop, and a scenario switch written to its
standard input, with a scripted child in place of `cstudy`."""

import json
from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from starlette.testclient import TestClient

from coding_study.application.environment import Environment
from coding_study.application.ports import StubGenerator
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.domain.problem import Language
from coding_study.entrypoints.web.runs import Children
from tests.fakes import FakeStubGenerator, FakeToolchains, make_environment
from tests.sandbox_fakes import FakeSandbox
from tests.scripted_runs import (
    QUICK,
    Script,
    answers_interrupt,
    event,
    eventually,
    frames,
    outs,
)
from tests.service_problems import SLUG, make_content, write_problem
from tests.web_server import WRITE_HEADERS, session_client, web_app

DEV = "/api/v1/dev"
READY = event("dev_ready", app_url="http://127.0.0.1:56223", startup_s=2.5, mocks=[])
STOPPED = event("dev_end", outcome="stopped", exit_code=0, message="the stack is down")


@dataclass
class Server:
    client: TestClient
    script: Script
    children: Children

    def start(self, attempt_id: int):
        return self.client.post(DEV, json={"attempt_id": attempt_id}, headers=WRITE_HEADERS)

    def started(self, attempt_id: int) -> str:
        response = self.start(attempt_id)
        assert response.status_code == 201, response.text
        return response.json()["id"]

    def post(self, dev_id: str, action: str, body: object):
        return self.client.post(f"{DEV}/{dev_id}/{action}", json=body, headers=WRITE_HEADERS)


@pytest.fixture
def environment(tmp_path) -> Environment:
    root = make_content(tmp_path / "workspace")
    write_problem(root)
    stubs: dict[Language, StubGenerator] = {Language.PYTHON: FakeStubGenerator()}
    toolchains = FakeToolchains(stub_generators=stubs)
    return make_environment(root, sandbox=FakeSandbox(), toolchains=toolchains)


@pytest.fixture
def script(tmp_path) -> Script:
    script = Script(tmp_path / "script.json")
    script.play(answers_interrupt(), *outs(READY))
    return script


@pytest.fixture
def server(tmp_path, environment, script) -> Iterator[Server]:
    children = Children(QUICK)
    with session_client(web_app(tmp_path, environment, script.child, children)) as client:
        yield Server(client, script, children)


@pytest.fixture
def rooms(environment) -> int:
    return start_attempt(environment, StartRequest(SLUG)).attempt.id


def test_a_dev_stack_runs_cstudy_dev_with_events(server, rooms):
    server.started(rooms)

    assert server.script.arguments() == ["dev", SLUG, "--events"]


def test_its_events_stream_as_the_child_writes_them(server, rooms):
    dev_id = server.started(rooms)
    eventually(lambda: server.children.dev(dev_id).messages, bool)
    server.post(dev_id, "stop", {})

    events = [frame.event for frame in frames(server.client.get(f"{DEV}/{dev_id}/events").text)]

    assert events[0] == "dev_ready"
    assert events[-1] == "closed"


def test_one_dev_stack_runs_per_attempt(server, rooms):
    dev_id = server.started(rooms)

    response = server.start(rooms)

    assert response.status_code == 409
    assert response.json()["error"]["dev"] == dev_id


def test_another_kind_of_problem_has_no_dev_stack(tmp_path, script):
    environment = make_environment(
        make_content(tmp_path / "bank"),
        toolchains=FakeToolchains(stub_generators={Language.PYTHON: FakeStubGenerator()}),
    )
    attempt = start_attempt(environment, StartRequest("two-sum", Language.PYTHON)).attempt.id
    with session_client(web_app(tmp_path, environment, script.child, Children(QUICK))) as client:
        response = client.post(DEV, json={"attempt_id": attempt}, headers=WRITE_HEADERS)

    assert response.status_code == 422
    assert "service projects" in response.json()["error"]["message"]


def test_stop_ends_the_child_as_ctrl_c_does(server, rooms):
    dev_id = server.started(rooms)
    eventually(lambda: server.children.dev(dev_id).messages, bool)

    assert server.post(dev_id, "stop", {}).status_code == 202
    eventually(lambda: server.client.get(f"{DEV}/{dev_id}").json()["state"], "ended".__eq__)


def test_the_attempts_dev_stacks_are_listed_newest_first(server, rooms):
    dev_id = server.started(rooms)

    listed = server.client.get(f"{DEV}?attempt_id={rooms}").json()

    assert [found["id"] for found in listed] == [dev_id]


def test_a_scenario_switch_is_one_line_on_the_childs_standard_input(server, rooms, tmp_path):
    heard = tmp_path / "heard.txt"
    server.script.play(answers_interrupt(), *outs(READY), {"read_line": str(heard)})
    dev_id = server.started(rooms)
    switch = {"mock": "room-vendor", "scenario": "outage"}

    assert server.post(dev_id, "scenario", switch).status_code == 202
    line = eventually(lambda: heard.read_text() if heard.exists() else "", bool)
    assert json.loads(line) == switch


def test_none_switches_a_mock_server_to_no_scenario(server, rooms, tmp_path):
    heard = tmp_path / "heard.txt"
    server.script.play(answers_interrupt(), *outs(READY), {"read_line": str(heard)})
    dev_id = server.started(rooms)

    server.post(dev_id, "scenario", {"mock": "room-vendor", "scenario": None})

    line = eventually(lambda: heard.read_text() if heard.exists() else "", bool)
    assert json.loads(line)["scenario"] is None


@pytest.mark.parametrize("body", [{}, {"mock": 3, "scenario": "x"}, {"mock": "m", "scenario": 4}])
def test_a_switch_that_names_no_mock_server_and_scenario_is_a_usage_error(server, rooms, body):
    dev_id = server.started(rooms)

    assert server.post(dev_id, "scenario", body).status_code == 422


def test_a_switch_on_an_ended_dev_stack_is_a_conflict(server, rooms):
    server.script.play(*outs(STOPPED), {"exit": 0})
    dev_id = server.started(rooms)
    eventually(lambda: server.client.get(f"{DEV}/{dev_id}").json()["state"], "ended".__eq__)

    switch = {"mock": "room-vendor", "scenario": "outage"}
    assert server.post(dev_id, "scenario", switch).status_code == 409


def test_an_unknown_dev_stack_is_not_found(server):
    assert server.client.get(f"{DEV}/0123456789abcdef").status_code == 404


def test_the_server_stops_its_dev_stacks_as_it_stops(tmp_path, environment, script, rooms):
    children = Children(QUICK)
    with session_client(web_app(tmp_path, environment, script.child, children)) as client:
        response = client.post(DEV, json={"attempt_id": rooms}, headers=WRITE_HEADERS)
        dev_id = response.json()["id"]
        eventually(lambda: children.dev(dev_id).messages, bool)

    assert children.dev(dev_id).running is False
