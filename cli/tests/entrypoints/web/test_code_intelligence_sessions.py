"""A code-intelligence session (docs/specs/web-ui.md#sessions, docs/specs/web-ui.md#lifecycle-and-
limits): messages relayed between a socket and a server in both directions, the close codes, the
limit of four servers, and the end of a session: no server is left behind when the socket closes,
when the server exits or when `cstudy serve` stops."""

import os
import shutil
import signal
from collections.abc import Iterator
from contextlib import ExitStack
from dataclasses import replace
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from coding_study.domain.attempts import AttemptStatus
from coding_study.entrypoints.web.code_intelligence import MESSAGE_LIMIT, LanguageSessions
from coding_study.entrypoints.web.language_server import LanguageServerCommand
from tests.language_server_scripts import QUICK, answer, notification, request
from tests.language_sessions import Rig, closed_with, received, rig, session, stopped
from tests.project_fakes import PROJECT_SLUG
from tests.scripted_runs import eventually, gone, is_alive, kill
from tests.web_server import session_client

PARSE_ERROR = {
    "jsonrpc": "2.0",
    "id": None,
    "error": {"code": -32700, "message": "not one JSON object"},
}
PING = {"reply": "textDocument/hover", "result": "pong"}
"""A server that answers a hover with "pong", which crosses the broker as it is."""
LIMIT_REASON = "at most 4 code intelligence sessions run at once; close one in another tab"


@pytest.fixture
def lab(tmp_path) -> Rig:
    return rig(tmp_path)


@pytest.fixture
def client(lab) -> Iterator[TestClient]:
    with session_client(lab.app) as page:
        yield page


def started_servers(lab: Rig) -> int:
    return len(lab.server.calls())


def wait_for_servers(lab: Rig, count: int) -> None:
    eventually(lambda: started_servers(lab), lambda started: started >= count)


def all_gone(lab: Rig) -> bool:
    eventually(lambda: [is_alive(pid) for pid in lab.server.pids()], lambda alive: not any(alive))
    return True


# relaying


def hover(lab: Rig, request_id: int, **extra: object) -> dict[str, object]:
    """A hover request for a file inside the session's root."""
    return request(
        request_id, "textDocument/hover", {"textDocument": {"uri": lab.document}, **extra}
    )


def test_a_request_reaches_the_server_and_its_answer_reaches_the_page(lab, client):
    lab.server.play(PING)
    with session(client, lab.query) as websocket:
        websocket.send_json(hover(lab, 7, position={"line": 1}))
        assert received(websocket) == answer(7, "pong")
    assert lab.server.received()[0] == hover(lab, 7, position={"line": 1})


def test_what_the_server_writes_reaches_the_page_in_order(lab, client):
    messages = [
        notification(
            "textDocument/publishDiagnostics",
            {"uri": lab.document, "diagnostics": [{"message": str(number)}]},
        )
        for number in range(4)
    ]
    lab.server.play(*({"send": message} for message in messages))
    with session(client, lab.query) as websocket:
        assert [received(websocket) for _ in messages] == messages


def test_text_beyond_ascii_crosses_both_ways_unchanged(lab, client):
    lab.server.play(
        PING,
        {
            "send": notification(
                "textDocument/publishDiagnostics",
                {"uri": lab.document, "diagnostics": [{"message": "é 🌍"}]},
            )
        },
    )
    with session(client, lab.query) as websocket:
        websocket.send_json(hover(lab, 1, note="héllo 🌍"))
        replies = [received(websocket), received(websocket)]
    assert (
        lab.server.received()[0]["params"]["note"],
        replies[1]["params"]["diagnostics"][0]["message"],
    ) == ("héllo 🌍", "é 🌍")


@pytest.mark.parametrize(
    "text",
    ["not json", "[1, 2]", "3", "null", '"text"', "", "{", "[" * 100_000],
    ids=["words", "list", "number", "null", "string", "empty", "unclosed", "nesting too deep"],
)
def test_text_that_is_not_one_json_object_gets_a_parse_error_and_the_session_goes_on(
    lab, client, text
):
    lab.server.play(PING)
    with session(client, lab.query) as websocket:
        websocket.send_text(text)
        assert received(websocket) == PARSE_ERROR
        websocket.send_json(hover(lab, 1))
        assert received(websocket) == answer(1, "pong")
    eventually(lab.server.methods, lambda methods: methods[-2:] == ["shutdown", "exit"])
    assert lab.server.received()[:-2] == [hover(lab, 1)]


def test_a_binary_message_closes_the_socket_with_1003(lab, client):
    with session(client, lab.query) as websocket:
        websocket.send_bytes(b"{}")
        assert closed_with(websocket) == (1003, "binary messages are not accepted")


def test_a_message_over_4_mib_closes_the_socket_with_1009(lab, client):
    with session(client, lab.query) as websocket:
        websocket.send_text("x" * (MESSAGE_LIMIT + 1))
        assert closed_with(websocket) == (1009, "message over 4 MiB")


def test_a_message_of_4_mib_is_still_a_message(lab, client):
    with session(client, lab.query) as websocket:
        websocket.send_text("x" * MESSAGE_LIMIT)
        assert received(websocket) == PARSE_ERROR


def test_the_limit_counts_bytes_not_characters(lab, client):
    with session(client, lab.query) as websocket:
        websocket.send_text("é" * (MESSAGE_LIMIT // 2 + 1))
        assert closed_with(websocket) == (1009, "message over 4 MiB")


def test_the_server_runs_in_the_practice_project_of_the_attempt(lab, client):
    lab.server.play()
    with session(client, lab.query):
        wait_for_servers(lab, 1)
    assert Path(lab.server.calls()[0]["cwd"]).resolve() == (lab.root / "python").resolve()


def test_a_project_attempts_server_runs_in_its_folder(tmp_path):
    lab = rig(tmp_path, project=True)
    lab.server.play()
    with session_client(lab.app) as page, session(page, lab.query):
        wait_for_servers(lab, 1)
    folder = tmp_path / "projects" / PROJECT_SLUG
    assert Path(lab.server.calls()[0]["cwd"]).resolve() == folder.resolve()


def test_a_session_outlives_the_attempt_it_was_opened_for(lab, client):
    lab.server.play(PING)
    with session(client, lab.query) as websocket:
        wait_for_servers(lab, 1)
        lab.environment.progress.update_attempt(replace(lab.attempt, status=AttemptStatus.PASSED))
        websocket.send_json(hover(lab, 1))
        assert received(websocket) == answer(1, "pong")


# the server ends


def test_a_server_that_exits_closes_the_socket_with_4002_its_exit_code_and_last_error(lab, client):
    lab.server.play({"err": "starting"}, {"err": "Error: Cannot find module"}, {"exit": 1})
    with session(client, lab.query) as websocket:
        assert closed_with(websocket) == (4002, "exit 1: Error: Cannot find module")


def test_a_server_that_exits_without_a_word_closes_with_4002_and_only_its_code(lab, client):
    lab.server.play({"exit": 0})
    with session(client, lab.query) as websocket:
        assert closed_with(websocket) == (4002, "exit 0")


def test_a_server_a_signal_ended_counts_as_128_plus_its_number(lab, client):
    lab.server.play({"wait_for": str(lab.server.gate("never"))})
    with session(client, lab.query) as websocket:
        wait_for_servers(lab, 1)
        os.kill(lab.server.pids()[0], signal.SIGKILL)
        assert closed_with(websocket) == (4002, f"exit {128 + signal.SIGKILL}")


def test_the_reason_is_cut_to_123_bytes_at_a_character_boundary(lab, client):
    lab.server.play({"err": "é" * 200}, {"exit": 1})
    with session(client, lab.query) as websocket:
        code, reason = closed_with(websocket)
    assert (code, reason.startswith("exit 1: é"), len(reason.encode())) == (4002, True, 122)


def test_output_that_is_not_lsp_closes_with_4002_and_says_so(lab, client):
    lab.server.play({"raw": "Warning: something\r\n\r\n"}, {"wait_for": str(lab.server.gate("x"))})
    with session(client, lab.query) as websocket:
        assert closed_with(websocket) == (4002, "bad output: a message without Content-Length")
    assert all_gone(lab)


def test_a_server_that_cannot_start_closes_with_4002_naming_what_is_missing(lab):
    lab.sessions = LanguageSessions(LanguageServerCommand(("cstudy-no-such-server",)), QUICK)
    with session_client(lab.app) as page, session(page, lab.query) as websocket:
        assert closed_with(websocket) == (4002, "cannot start: cstudy-no-such-server not found")


def test_a_root_that_is_not_there_closes_with_4002(lab, client):
    shutil.rmtree(lab.root / "python")
    with session(client, lab.query) as websocket:
        code, reason = closed_with(websocket)
    assert (code, reason.startswith("cannot start: no such directory: ")) == (4002, True)


def test_the_process_group_of_a_server_that_exited_is_still_ended(lab):
    pid_file = lab.server.gate("sleeper.pid")
    lab.server.play({"spawn_sleeper": str(pid_file)}, {"exit": 0})
    try:
        with session_client(lab.app) as page, session(page, lab.query) as websocket:
            assert closed_with(websocket) == (4002, "exit 0")
        assert gone(pid_file)
    finally:
        kill(pid_file)


# the socket ends


def test_closing_the_socket_stops_the_server_with_shutdown_then_exit(lab, client):
    lab.server.play()
    with session(client, lab.query):
        eventually(lab.server.ready, bool)
    eventually(lab.server.methods, lambda methods: methods == ["shutdown", "exit"])
    assert all_gone(lab)


def test_no_process_is_left_when_the_socket_closes_and_the_server_stops(lab):
    """The test client cancels a handler as the socket closes, as an abrupt end would."""
    pid_file = lab.server.gate("sleeper.pid")
    lab.server.play({"spawn_sleeper": str(pid_file)}, {"ignore": ["shutdown", "exit", "eof"]})
    try:
        with session_client(lab.app) as page, session(page, lab.query):
            eventually(lab.server.ready, bool)
        assert (all_gone(lab), gone(pid_file)) == (True, True)
    finally:
        kill(pid_file)


def test_a_server_that_ignores_sigterm_too_is_killed(lab):
    lab.server.play({"ignore": ["shutdown", "exit", "eof", "SIGTERM"]})
    with session_client(lab.app) as page, session(page, lab.query):
        eventually(lab.server.ready, bool)
    assert all_gone(lab)


# the limit


def test_a_fifth_session_closes_with_4003_naming_the_limit(lab, client):
    lab.server.play(PING)
    with ExitStack() as stack:
        sessions = []
        for count in range(1, 5):
            sessions.append(stack.enter_context(session(client, lab.query)))
            wait_for_servers(lab, count)
        with session(client, lab.query) as fifth:
            assert closed_with(fifth) == (4003, LIMIT_REASON)
        for number, websocket in enumerate(sessions):
            websocket.send_json(hover(lab, number))
            assert received(websocket) == answer(number, "pong")
    assert started_servers(lab) == 4


def test_a_server_holds_its_slot_until_its_process_has_exited(tmp_path):
    slow = replace(QUICK, terminate_after_s=2.0, kill_after_s=1.0)
    lab = rig(tmp_path, timing=slow, limit=1)
    lab.server.play({"ignore": ["shutdown", "exit", "eof"]})
    with session_client(lab.app) as page:
        with session(page, lab.query):
            eventually(lab.server.ready, bool)
        with session(page, lab.query) as second:
            held = closed_with(second)
        assert all_gone(lab)
        lab.server.play()
        with session(page, lab.query):
            wait_for_servers(lab, 2)
    assert (held[0], started_servers(lab)) == (4003, 2)


def test_a_session_that_ended_frees_its_slot(tmp_path):
    lab = rig(tmp_path, limit=1)
    lab.server.play({"exit": 0})
    with session_client(lab.app) as page:
        for _ in range(2):
            with session(page, lab.query) as websocket:
                assert closed_with(websocket) == (4002, "exit 0")
            assert all_gone(lab)
    assert started_servers(lab) == 2


# the server stops


def test_a_server_that_stops_closes_every_socket_with_1001_and_stops_the_servers(lab, client):
    lab.server.play(PING)
    with session(client, lab.query) as websocket:
        websocket.send_json(hover(lab, 1))
        received(websocket)
        stopped(client, lab.sessions)
        assert closed_with(websocket) == (1001, "cstudy serve is stopping")
    assert (lab.server.methods()[-2:], all_gone(lab)) == (["shutdown", "exit"], True)


def test_a_session_that_starts_while_the_server_stops_closes_with_1001_and_starts_nothing(
    lab, client
):
    stopped(client, lab.sessions)
    with session(client, lab.query) as websocket:
        assert closed_with(websocket) == (1001, "cstudy serve is stopping")
    assert started_servers(lab) == 0


def test_stopping_twice_changes_nothing(lab, client):
    lab.server.play()
    with session(client, lab.query):
        eventually(lab.server.ready, bool)
        stopped(client, lab.sessions)
        stopped(client, lab.sessions)
    assert all_gone(lab)


def test_a_server_that_stops_with_no_session_returns_at_once(lab, client):
    stopped(client, lab.sessions)
