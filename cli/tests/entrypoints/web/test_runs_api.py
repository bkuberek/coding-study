"""Runs over HTTP (docs/specs/web-ui.md#runs): the options and the child's arguments, the
pre-checks, the stream and its replay, the slot, cancel and its escalation, and the documents,
with a scripted child in place of `cstudy`."""

import asyncio
import json
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from coding_study.application.environment import Environment
from coding_study.application.ports import StubGenerator
from coding_study.application.start_attempt import StartRequest, start_attempt
from coding_study.application.start_item import ItemStartRequest, start_item_attempt
from coding_study.domain.problem import Language
from coding_study.entrypoints.web.runs import Children
from tests.fakes import FakeStubGenerator, FakeToolchains, make_environment, repository_root
from tests.helpers import FIXTURE_TRACKS
from tests.project_fakes import PROJECT_SLUG, ScriptedProjectProcess, project_environment
from tests.sandbox_fakes import FakeSandbox
from tests.scripted_runs import (
    CASE_RESULT,
    CASE_START,
    PASSING_RUN,
    QUICK,
    RUN_END,
    RUN_START,
    SUMMARY,
    Script,
    answers_interrupt,
    eventually,
    frames,
    gone,
    kill,
    lines_of,
    outs,
)
from tests.service_problems import SLUG as SERVICE_SLUG
from tests.service_problems import make_content, write_problem
from tests.web_server import WRITE_HEADERS, session_client, web_app

PRACTICE = Path(__file__).resolve().parents[2] / "fixtures" / "practice" / "problems"
STUBS: dict[Language, StubGenerator] = {language: FakeStubGenerator() for language in Language}
RUNS = "/api/v1/runs"


@dataclass
class Server:
    """A test client of a server whose children play `script`, and the lines it printed."""

    client: TestClient
    script: Script
    children: Children
    printed: list[tuple[str, str]] = field(default_factory=list[tuple[str, str]])

    def start(self, attempt_id: int, **options: object):
        body = {"attempt_id": attempt_id, "command": "test", **options}
        return self.client.post(RUNS, json=body, headers=WRITE_HEADERS)

    def started(self, attempt_id: int, **options: object) -> str:
        response = self.start(attempt_id, **options)
        assert response.status_code == 201, response.text
        return response.json()["id"]

    def listening(self, attempt_id: int) -> str:
        """Starts a run and waits for its first event, written once the child set its signal
        handlers."""
        run_id = self.started(attempt_id)
        eventually(lambda: self.children.run(run_id).messages, bool)
        return run_id

    def events(self, run_id: str, last_event_id: str | None = None) -> str:
        headers = {} if last_event_id is None else {"Last-Event-ID": last_event_id}
        return self.client.get(f"{RUNS}/{run_id}/events", headers=headers).text

    def document(self, run_id: str) -> dict[str, object]:
        return self.client.get(f"{RUNS}/{run_id}").json()

    def cancel(self, run_id: str):
        return self.client.post(f"{RUNS}/{run_id}/cancel", headers=WRITE_HEADERS)


@pytest.fixture
def practice(tmp_path) -> Environment:
    root = repository_root(tmp_path / "workspace", PRACTICE, FIXTURE_TRACKS)
    return make_environment(root, toolchains=FakeToolchains(stub_generators=STUBS))


@pytest.fixture
def script(tmp_path) -> Script:
    script = Script(tmp_path / "script.json")
    script.play(*outs(*PASSING_RUN), {"exit": 0})
    return script


@contextmanager
def serve(tmp_path: Path, environment: Environment, script: Script) -> Iterator[Server]:
    """A server over `environment` until the block ends, when it stops as it does on Ctrl-C."""
    printed: list[tuple[str, str]] = []
    children = Children(QUICK, lambda label, text: printed.append((label, text)))
    app = web_app(tmp_path, environment, script.child, children)
    with session_client(app) as client:
        yield Server(client, script, children, printed)


@pytest.fixture
def server(tmp_path, practice, script) -> Iterator[Server]:
    with serve(tmp_path, practice, script) as running:
        yield running


@pytest.fixture
def two_sum(practice) -> int:
    return start_attempt(practice, StartRequest("two-sum", Language.PYTHON)).attempt.id


@pytest.fixture
def lru_cache(practice) -> int:
    return start_attempt(practice, StartRequest("lru-cache", Language.PYTHON)).attempt.id


def error(response) -> tuple[int, str]:
    return response.status_code, response.json()["error"]["code"]


# starting a run


def test_a_run_answers_201_with_its_id(server, two_sum):
    response = server.start(two_sum)
    assert (response.status_code, len(response.json()["id"])) == (201, 16)


def test_a_test_run_is_cstudy_test_of_the_attempt_with_events(server, two_sum):
    server.started(two_sum)
    assert server.script.arguments() == ["test", "two-sum", "--lang", "python", "--events"]


def test_a_child_works_on_the_servers_workspace(server, practice, two_sum):
    server.started(two_sum)
    calls = eventually(server.script.calls, bool)
    assert calls[-1]["arguments"][:2] == ["--workspace", str(practice.root)]


@pytest.mark.parametrize(
    ("options", "flags"),
    [
        ({"cases": ["ex1", "h2"]}, ["--case=ex1", "--case=h2"]),
        ({"stress": 30, "seed": 14}, ["--stress=30", "--seed=14"]),
        ({"time_limit": True}, ["--time-limit"]),
        ({"time_limit": False}, ["--no-time-limit"]),
        ({"time_limit": "5x"}, ["--time-limit=5x"]),
        ({"perf": True}, ["--perf"]),
        ({"perf": False, "cases": [], "stress": None}, []),
    ],
)
def test_run_options_become_the_childs_flags(server, two_sum, options, flags):
    server.started(two_sum, **options)
    assert server.script.arguments()[5:] == flags


def test_typecheck_applies_to_typescript_only(server, two_sum):
    server.started(two_sum, typecheck=True)
    assert "--typecheck" not in server.script.arguments()


def test_a_typescript_run_type_checks_as_the_preference_says(server, practice):
    attempt_id = start_attempt(practice, StartRequest("two-sum", Language.TYPESCRIPT)).attempt.id
    server.started(attempt_id)
    assert server.script.arguments()[-1] == "--typecheck"


def test_a_typescript_run_may_turn_the_type_check_off(server, practice):
    attempt_id = start_attempt(practice, StartRequest("two-sum", Language.TYPESCRIPT)).attempt.id
    server.started(attempt_id, typecheck=False)
    assert "--typecheck" not in server.script.arguments()


@pytest.mark.parametrize(
    "options",
    [
        {"stress": 0},
        {"stress": 101},
        {"stress": "10"},
        {"level": 0},
        {"cases": "ex1"},
        {"cases": [""]},
        {"perf": "yes"},
        {"time_limit": ""},
        {"command": "verify"},
        {"watch": True},
    ],
)
def test_an_option_of_the_wrong_name_type_or_range_is_a_usage_error(server, two_sum, options):
    assert error(server.start(two_sum, **options)) == (422, "usage")


@pytest.mark.parametrize("body", [{"command": "test"}, {"command": "test", "attempt_id": True}, []])
def test_a_run_needs_an_attempt_id(server, body):
    assert error(server.client.post(RUNS, json=body, headers=WRITE_HEADERS)) == (422, "usage")


def test_a_refused_run_starts_no_child(server, two_sum):
    server.start(two_sum, stress=0)
    assert server.script.calls() == []


def test_submit_takes_no_test_options(server, two_sum):
    response = server.start(two_sum, command="submit", cases=["ex1"])
    assert response.json()["error"]["message"] == "cstudy submit takes no cases"


# pre-checks


def test_a_run_of_an_unknown_attempt_is_not_found(server, two_sum):
    assert error(server.start(two_sum + 99)) == (404, "not_found")


def test_a_run_of_an_ended_attempt_is_refused(server, practice, two_sum):
    start_attempt(practice, StartRequest("two-sum", Language.PYTHON, fresh=True))
    assert error(server.start(two_sum)) == (409, "attempt_ended")


def test_submit_on_a_function_problem_gets_the_clis_message(server, two_sum):
    response = server.start(two_sum, command="submit")
    assert (response.status_code, response.json()["error"]["message"]) == (
        422,
        "cstudy submit is for project problems; cstudy test grades two-sum",
    )


def test_an_item_has_no_runs(server, practice):
    attempt_id = start_item_attempt(practice, ItemStartRequest("url-shortener")).attempt.id
    assert error(server.start(attempt_id)) == (422, "usage")


def test_a_level_on_a_problem_without_levels_is_refused(server, two_sum):
    assert error(server.start(two_sum, level=1)) == (422, "usage")


@pytest.fixture
def project(tmp_path) -> Environment:
    return project_environment(tmp_path / "project", ScriptedProjectProcess())


@pytest.fixture
def project_server(tmp_path, project, script) -> Iterator[Server]:
    with serve(tmp_path, project, script) as running:
        yield running


@pytest.fixture
def bank(project) -> int:
    return start_attempt(project, StartRequest(PROJECT_SLUG)).attempt.id


def test_a_project_run_names_no_language(project_server, bank):
    project_server.started(bank, command="submit", level=1)
    assert project_server.script.arguments() == ["submit", PROJECT_SLUG, "--events", "--level=1"]


@pytest.fixture
def service(tmp_path) -> Environment:
    root = make_content(tmp_path / "service")
    write_problem(root)
    return make_environment(root, sandbox=FakeSandbox())


@pytest.fixture
def service_server(tmp_path, service, script) -> Iterator[Server]:
    with serve(tmp_path, service, script) as running:
        yield running


@pytest.fixture
def rooms(service) -> int:
    return start_attempt(service, StartRequest(SERVICE_SLUG)).attempt.id


def test_a_service_project_test_runs_with_no_flag(service_server, rooms):
    service_server.started(rooms)
    assert service_server.script.arguments() == ["test", SERVICE_SLUG, "--events"]


def test_a_service_project_takes_no_type_check_from_the_preference(service_server, rooms):
    """Its TypeScript runs in the stack, and `cstudy test` there takes no flag."""
    run_id = service_server.started(rooms)
    assert service_server.document(run_id)["options"]["typecheck"] is None


def test_a_service_project_submits_with_its_level(service_server, rooms):
    service_server.started(rooms, command="submit", level=1)
    assert service_server.script.arguments() == ["submit", SERVICE_SLUG, "--events", "--level=1"]


def test_a_locked_level_is_refused_with_the_clis_message(project_server, bank):
    response = project_server.start(bank, command="submit", level=2)
    assert response.json()["error"]["message"] == (
        "level 2 is locked; pass level 1 with cstudy submit first"
    )


# the stream


def test_the_stream_relays_each_event_line_unchanged(server, two_sum):
    run_id = server.started(two_sum)
    relayed = [json.dumps(frame.data) for frame in frames(server.events(run_id))[:-1]]
    assert relayed == list(PASSING_RUN)


def test_each_message_is_named_by_its_type(server, two_sum):
    run_id = server.started(two_sum)
    names = [frame.event for frame in frames(server.events(run_id))]
    assert names == ["run_start", "case_start", "case_result", "run_end", "closed"]


def test_each_message_has_its_index_as_id_and_closed_has_none(server, two_sum):
    run_id = server.started(two_sum)
    assert [frame.id for frame in frames(server.events(run_id))] == [0, 1, 2, 3, None]


def test_the_stream_is_an_event_stream(server, two_sum):
    run_id = server.started(two_sum)
    response = server.client.get(f"{RUNS}/{run_id}/events")
    assert response.headers["content-type"].startswith("text/event-stream")


def test_a_line_that_is_not_an_event_is_dropped(server, script, two_sum, capsys):
    script.play(*outs(RUN_START, "warming up", "[1, 2]", RUN_END), {"exit": 0})
    run_id = server.started(two_sum)
    names = [frame.event for frame in frames(server.events(run_id))]
    assert names == ["run_start", "run_end", "closed"]


def test_a_dropped_line_is_reported_on_the_servers_standard_error(server, script, two_sum, capsys):
    script.play(*outs(RUN_START, "warming up", RUN_END), {"exit": 0})
    server.events(server.started(two_sum))
    assert "dropped a line that is not an event: warming up" in capsys.readouterr().err


def test_closed_carries_the_exit_code(server, script, two_sum):
    script.play(*outs(RUN_START, RUN_END), {"exit": 1})
    closed = frames(server.events(server.started(two_sum)))[-1]
    assert closed.data == {"exit_code": 1, "signal": None, "stderr": []}


def test_closed_carries_the_last_20_lines_of_standard_error_without_a_run_end(
    server, script, two_sum
):
    script.play(*({"err": f"line {number}"} for number in range(25)), {"exit": 3})
    closed = frames(server.events(server.started(two_sum)))[-1]
    assert closed.data["stderr"] == [f"line {number}" for number in range(5, 25)]


def test_closed_leaves_standard_error_out_after_a_run_end(server, script, two_sum):
    script.play({"err": "warming Gradle daemon"}, *outs(RUN_START, RUN_END), {"exit": 0})
    closed = frames(server.events(server.started(two_sum)))[-1]
    assert closed.data["stderr"] == []


# replay


def test_last_event_id_replays_the_lines_after_it(server, two_sum):
    run_id = server.started(two_sum)
    replayed = frames(server.events(run_id, last_event_id="1"))
    assert [frame.id for frame in replayed] == [2, 3, None]


def test_an_ended_run_replays_and_closes(server, two_sum):
    run_id = server.started(two_sum)
    server.events(run_id)
    assert [frame.event for frame in frames(server.events(run_id))][-1] == "closed"


def test_a_last_event_id_that_is_not_a_number_replays_everything(server, two_sum):
    run_id = server.started(two_sum)
    assert frames(server.events(run_id, last_event_id="x"))[0].event == "run_start"


# the slot


@pytest.fixture
def holding(script) -> Path:
    """The gate a run waits on after its run_end, before it exits."""
    gate = script.gate("release")
    script.play(*outs(*PASSING_RUN), {"wait_for": str(gate)}, {"exit": 0})
    return gate


def test_a_second_run_of_the_attempt_gets_409_with_the_active_runs_id(server, holding, two_sum):
    run_id = server.started(two_sum)
    response = server.start(two_sum)
    assert (error(response), response.json()["error"]["run"]) == ((409, "conflict"), run_id)


def test_the_slot_stays_taken_after_run_end_until_the_child_exits(server, holding, two_sum):
    run_id = server.started(two_sum)
    eventually(lambda: server.document(run_id)["summary"], bool)
    assert error(server.start(two_sum)) == (409, "conflict")


def test_the_slot_frees_when_the_child_exits(server, holding, two_sum):
    run_id = server.started(two_sum)
    holding.touch()
    server.events(run_id)
    assert server.start(two_sum).status_code == 201


def test_runs_of_different_attempts_may_overlap(server, holding, two_sum, lru_cache):
    server.started(two_sum)
    assert server.start(lru_cache).status_code == 201


def test_closed_comes_when_the_child_exits_while_a_process_it_left_holds_its_output(
    server, script, two_sum
):
    left = script.gate("left.pid")
    script.play({"leave_behind": str(left)}, *outs(*PASSING_RUN), {"exit": 0})
    try:
        closed = frames(server.events(server.started(two_sum)))[-1]
    finally:
        kill(left)
    assert closed.data["exit_code"] == 0


# cancel


@pytest.fixture
def waiting(script) -> None:
    """A run that writes its first case, then waits, stopping as cstudy does on SIGINT."""
    script.play(answers_interrupt(), *outs(RUN_START, CASE_START))


def test_cancel_answers_202(server, waiting, two_sum):
    assert server.cancel(server.started(two_sum)).status_code == 202


def test_cancel_sends_sigint_and_the_run_ends_interrupted(server, waiting, two_sum):
    run_id = server.listening(two_sum)
    server.cancel(run_id)
    run_end = next(lines_of(frames(server.events(run_id)), "run_end"))
    assert (run_end["outcome"], run_end["exit_code"]) == ("interrupted", 130)


def test_a_cancelled_run_closes_with_exit_130_and_no_signal(server, waiting, two_sum):
    run_id = server.listening(two_sum)
    server.cancel(run_id)
    closed = frames(server.events(run_id))[-1]
    assert (closed.data["exit_code"], closed.data["signal"]) == (130, None)


def test_a_child_that_ignores_sigint_gets_sigterm(server, script, two_sum):
    stopped = [{"out": json.dumps({"type": "run_end"})}, {"exit": 143}]
    script.play({"on": {"SIGINT": "ignore", "SIGTERM": stopped}}, *outs(RUN_START))
    run_id = server.listening(two_sum)
    server.cancel(run_id)
    assert frames(server.events(run_id))[-1].data["exit_code"] == 143


def test_a_child_that_ignores_sigint_and_sigterm_gets_sigkill(server, script, two_sum):
    script.play({"on": {"SIGINT": "ignore", "SIGTERM": "ignore"}}, *outs(RUN_START))
    run_id = server.listening(two_sum)
    server.cancel(run_id)
    closed = frames(server.events(run_id))[-1]
    assert (closed.data["exit_code"], closed.data["signal"]) == (137, "SIGKILL")


def test_sigkill_takes_the_childs_whole_process_group(server, script, two_sum):
    sleeper = script.gate("sleeper.pid")
    script.play(
        {"on": {"SIGINT": "ignore", "SIGTERM": "ignore"}},
        {"spawn_sleeper": str(sleeper)},
        *outs(RUN_START),
    )
    run_id = server.listening(two_sum)
    eventually(sleeper.exists, bool)
    server.cancel(run_id)
    server.events(run_id)
    try:
        assert gone(sleeper)
    finally:
        kill(sleeper)


def test_the_slot_frees_once_a_cancelled_child_exits(server, waiting, two_sum):
    run_id = server.listening(two_sum)
    server.cancel(run_id)
    server.events(run_id)
    assert server.start(two_sum).status_code == 201


def test_cancelling_an_ended_run_gets_409(server, two_sum):
    run_id = server.started(two_sum)
    server.events(run_id)
    assert error(server.cancel(run_id)) == (409, "conflict")


def test_cancelling_an_unknown_run_is_not_found(server):
    assert error(server.cancel("0123456789abcdef")) == (404, "not_found")


# documents


def test_a_runs_document_while_it_runs(server, waiting, two_sum):
    run_id = server.started(two_sum, cases=["ex1"])
    document = server.document(run_id)
    started_at = document.pop("started_at")
    assert (bool(started_at), document) == (
        True,
        {
            "id": run_id,
            "command": "test",
            "options": {
                "level": None,
                "cases": ["ex1"],
                "typecheck": True,
                "stress": None,
                "seed": None,
                "time_limit": None,
                "perf": False,
            },
            "state": "running",
            "exit_code": None,
            "attempt_id": two_sum,
            "summary": None,
        },
    )


def test_an_ended_runs_document_holds_its_exit_code_and_summary(server, two_sum):
    run_id = server.started(two_sum)
    server.events(run_id)
    document = server.document(run_id)
    assert (document["state"], document["exit_code"], document["summary"]) == (
        "ended",
        0,
        SUMMARY,
    )


def test_an_unknown_run_is_not_found(server):
    assert error(server.client.get(f"{RUNS}/0123456789abcdef")) == (404, "not_found")


def test_an_attempts_runs_come_newest_first(server, two_sum):
    first = server.started(two_sum)
    server.events(first)
    second = server.started(two_sum)
    server.events(second)
    listed = server.client.get(RUNS, params={"attempt_id": two_sum}).json()
    assert [run["id"] for run in listed] == [second, first]


def test_listing_runs_needs_the_attempt(server):
    assert error(server.client.get(RUNS)) == (422, "usage")


def test_an_attempt_keeps_its_last_ten_runs(server, two_sum):
    started: list[str] = []
    for _ in range(11):
        started.append(server.started(two_sum))
        server.events(started[-1])
    listed = server.client.get(RUNS, params={"attempt_id": two_sum}).json()
    assert [run["id"] for run in listed] == started[:0:-1]


def test_a_run_ten_newer_runs_replaced_is_not_found(server, two_sum):
    first = server.started(two_sum)
    server.events(first)
    for _ in range(10):
        server.events(server.started(two_sum))
    assert error(server.client.get(f"{RUNS}/{first}")) == (404, "not_found")


# the server's output


def test_the_server_prints_a_line_when_a_run_ends(server, two_sum):
    server.events(server.started(two_sum))
    assert server.printed == [("run", "test two-sum · python · passed · 2/2 · 0.9s")]


def test_a_run_without_run_end_is_printed_with_its_exit_code(server, script, two_sum):
    script.play({"err": "error: no attempt in progress"}, {"exit": 3})
    server.events(server.started(two_sum))
    assert server.printed == [("run", "test two-sum · python · exit 3")]


def test_a_killed_run_is_printed_with_its_signal(server, script, two_sum):
    script.play({"on": {"SIGINT": "ignore", "SIGTERM": "ignore"}}, *outs(RUN_START))
    run_id = server.listening(two_sum)
    server.cancel(run_id)
    server.events(run_id)
    assert server.printed == [("run", "test two-sum · python · SIGKILL")]


# stopping


def test_stopping_the_server_cancels_its_runs(tmp_path, practice, script, two_sum):
    pid_file = script.gate("child.pid")
    script.play(answers_interrupt(), *outs(RUN_START, CASE_START, CASE_RESULT))
    with serve(tmp_path, practice, script) as server:
        server.listening(two_sum)
        pid_file.write_text(str(server.script.pid()))
    assert gone(pid_file)


def test_a_stopping_server_starts_no_run(tmp_path, practice, script, two_sum):
    with serve(tmp_path, practice, script) as server:
        asyncio.run(server.children.stop())
        assert error(server.start(two_sum)) == (409, "conflict")
