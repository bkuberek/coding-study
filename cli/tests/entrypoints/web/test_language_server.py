"""A language server as a child process (docs/specs/web-ui.md#lifecycle-and-limits): LSP framing in
both directions, its exit and its last line of standard error, and the stop sequence: `shutdown`,
`exit`, standard input closed, SIGTERM to the process group, then SIGKILL."""

import asyncio
import json
import os
import signal
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass
from pathlib import Path

import pytest

from coding_study.domain.code_intelligence import BASEDPYRIGHT
from coding_study.entrypoints.web import language_server
from coding_study.entrypoints.web.language_server import (
    MESSAGE_LIMIT,
    LanguageServerCommand,
    LanguageTiming,
    ServerProcess,
    ServerStartError,
)
from tests.language_server_scripts import (
    QUICK,
    SHUTDOWN_ANSWER,
    ScriptedServer,
    answer,
    notification,
)
from tests.scripted_runs import eventually, gone, is_alive, kill

WAIT_S = 5.0
STOP_BOUND_S = 10.0
"""A stop that takes this long has hung: the sequence ends in about three seconds."""
MIB = 1024 * 1024
LOG = notification("window/logMessage", {"message": "héllo 🌍", "type": 3})
NEVER = "never"
SIGTERM_EXIT = 128 + signal.SIGTERM
SIGKILL_EXIT = 128 + signal.SIGKILL


@pytest.fixture
def server(tmp_path) -> ScriptedServer:
    return ScriptedServer(tmp_path / "server.json")


@asynccontextmanager
async def running(
    server: ScriptedServer, directory: Path, timing: LanguageTiming = QUICK
) -> AsyncIterator[ServerProcess]:
    process = await ServerProcess.start(server.arguments, directory, timing)
    try:
        yield process
    finally:
        await process.stop()


async def next_text(process: ServerProcess) -> str | None:
    return await asyncio.wait_for(process.receive(), WAIT_S)


# framing


def test_a_message_the_server_wrote_is_read_without_its_framing(server, tmp_path):
    server.play({"send": LOG})

    async def read() -> str | None:
        async with running(server, tmp_path) as process:
            return await next_text(process)

    assert json.loads(asyncio.run(read()) or "null") == LOG


def test_messages_are_read_in_the_order_they_were_written(server, tmp_path):
    methods = ["one", "two", "three"]
    server.play(*({"send": notification(method)} for method in methods))

    async def read() -> list[str]:
        async with running(server, tmp_path) as process:
            texts = [await next_text(process) for _ in methods]
            return [json.loads(text or "null")["method"] for text in texts]

    assert asyncio.run(read()) == methods


def test_a_message_sent_reaches_the_server_framed_by_its_length_in_bytes(server, tmp_path):
    server.play({"await": "textDocument/didOpen"}, {"exit": 0})
    text = json.dumps(
        notification("textDocument/didOpen", {"text": "héllo 🌍"}), ensure_ascii=False
    )

    async def send() -> int:
        async with running(server, tmp_path) as process:
            await process.send(text)
            return await asyncio.wait_for(process.exited(), WAIT_S)

    assert (asyncio.run(send()), server.received()) == (0, [json.loads(text)])


def test_the_end_of_the_servers_output_is_none_however_often_it_is_read(server, tmp_path):
    server.play({"exit": 0})

    async def read() -> tuple[str | None, str | None]:
        async with running(server, tmp_path) as process:
            return await next_text(process), await next_text(process)

    assert asyncio.run(read()) == (None, None)


def test_output_without_a_content_length_ends_the_output_and_says_why(server, tmp_path):
    server.play({"raw": "Warning: something\r\n\r\n"}, {"wait_for": str(server.gate(NEVER))})

    async def read() -> tuple[str | None, str | None]:
        async with running(server, tmp_path) as process:
            return await next_text(process), process.output_problem

    assert asyncio.run(read()) == (None, "a message without Content-Length")


def test_a_content_length_that_is_not_a_number_ends_the_output_and_says_why(server, tmp_path):
    server.play({"raw": "Content-Length: many\r\n\r\n"}, {"wait_for": str(server.gate(NEVER))})

    async def read() -> str | None:
        async with running(server, tmp_path) as process:
            await next_text(process)
            return process.output_problem

    assert asyncio.run(read()) == "a Content-Length that is not a number: many"


def test_a_message_that_is_not_utf8_ends_the_output_and_says_why(server, tmp_path):
    """The fake writes its text as UTF-8, so `\\xff` is two bytes and the one the header counts
    is the first of them: a body that does not decode."""
    server.play({"raw": "Content-Length: 1\r\n\r\n\xff"}, {"wait_for": str(server.gate(NEVER))})

    async def read() -> str | None:
        async with running(server, tmp_path) as process:
            await next_text(process)
            return process.output_problem

    assert asyncio.run(read()) == "a message that is not UTF-8"


def test_a_message_longer_than_4_mib_is_refused_before_its_body_is_read(server, tmp_path):
    """The header alone ends the output; the body, which never comes, is not waited for."""
    server.play(
        {"raw": f"Content-Length: {MESSAGE_LIMIT + 1}\r\n\r\n"},
        {"wait_for": str(server.gate(NEVER))},
    )

    async def read() -> tuple[str | None, str | None]:
        async with running(server, tmp_path) as process:
            return await next_text(process), process.output_problem

    assert asyncio.run(read()) == (None, "a message over 4 MiB")


def test_a_message_of_exactly_4_mib_is_read(server, tmp_path):
    empty = notification("padded", {"padding": ""})
    padding = MESSAGE_LIMIT - len(json.dumps(empty))
    server.play({"send": notification("padded", {"padding": "x" * padding})})

    async def read() -> int:
        async with running(server, tmp_path) as process:
            return len((await next_text(process) or "").encode())

    assert asyncio.run(read()) == MESSAGE_LIMIT


# output nobody reads


def test_output_left_unread_over_the_limit_ends_the_output(server, tmp_path, monkeypatch):
    monkeypatch.setattr(language_server, "UNREAD_LIMIT", 100_000)
    big = notification("big", {"text": "x" * 30_000})
    server.play(*({"send": big} for _ in range(8)), {"wait_for": str(server.gate(NEVER))})

    async def lag() -> str | None:
        async with running(server, tmp_path) as process:
            await asyncio.wait_for(process.backlog.wait(), WAIT_S)
            return await next_text(process)

    assert asyncio.run(lag()) is None


def test_output_that_is_read_as_it_comes_is_never_a_backlog(server, tmp_path, monkeypatch):
    monkeypatch.setattr(language_server, "UNREAD_LIMIT", 100_000)
    big = notification("big", {"text": "x" * 30_000})
    server.play(*({"send": big} for _ in range(20)))

    async def read_all() -> tuple[int, bool]:
        async with running(server, tmp_path) as process:
            texts = [await next_text(process) for _ in range(20)]
            return len([text for text in texts if text]), process.backlog.is_set()

    assert asyncio.run(read_all()) == (20, False)


# exit and standard error


def test_the_servers_exit_code_is_the_one_a_shell_reports(server, tmp_path):
    server.play({"exit": 3})

    async def code() -> int:
        async with running(server, tmp_path) as process:
            return await asyncio.wait_for(process.exited(), WAIT_S)

    assert asyncio.run(code()) == 3


def test_a_signal_that_ended_the_server_counts_as_128_plus_its_number(server, tmp_path):
    server.play({"wait_for": str(server.gate(NEVER))})

    async def code() -> int:
        async with running(server, tmp_path) as process:
            eventually(server.calls, bool)
            os.kill(process.pid, signal.SIGKILL)
            return await asyncio.wait_for(process.exited(), WAIT_S)

    assert asyncio.run(code()) == SIGKILL_EXIT


@pytest.mark.parametrize(
    ("lines", "last"),
    [
        ([{"err": "first"}, {"err": "Error: Cannot find module"}], "Error: Cannot find module"),
        ([{"err": "Error: boom"}, {"err": ""}], "Error: boom"),
        ([], ""),
    ],
    ids=["the last one", "not a blank one", "none"],
)
def test_the_last_line_of_standard_error_is_kept_once_the_output_ends(
    server, tmp_path, lines, last
):
    server.play(*lines, {"exit": 1})

    async def last_line() -> str:
        async with running(server, tmp_path) as process:
            await next_text(process)
            return process.last_error

    assert asyncio.run(last_line()) == last


# starting


def test_the_server_runs_in_the_directory_it_was_given(server, tmp_path):
    (tmp_path / "root").mkdir()
    server.play({"exit": 0})

    async def run() -> None:
        async with running(server, tmp_path / "root") as process:
            await asyncio.wait_for(process.exited(), WAIT_S)

    asyncio.run(run())
    assert Path(server.calls()[0]["cwd"]).resolve() == (tmp_path / "root").resolve()


def test_a_command_that_is_not_there_cannot_start(tmp_path):
    async def start() -> None:
        await ServerProcess.start(("cstudy-no-such-server", "--stdio"), tmp_path, QUICK)

    with pytest.raises(ServerStartError) as refused:
        asyncio.run(start())
    assert str(refused.value) == "cstudy-no-such-server not found"


def test_a_directory_that_is_not_there_cannot_start(server, tmp_path):
    async def start() -> None:
        await ServerProcess.start(server.arguments, tmp_path / "missing", QUICK)

    with pytest.raises(ServerStartError, match=r"no such directory: .*missing"):
        asyncio.run(start())


def test_the_catalog_command_runs_node_on_the_servers_script(tmp_path):
    arguments = LanguageServerCommand().arguments(BASEDPYRIGHT, tmp_path / ".cs" / "lsp")
    assert arguments == ("node", f"{tmp_path}/.cs/lsp/{BASEDPYRIGHT.script}", "--stdio")


def test_a_replacement_command_runs_in_place_of_the_catalogs(tmp_path):
    command = LanguageServerCommand(("fake", "--stdio"))
    assert command.arguments(BASEDPYRIGHT, tmp_path) == ("fake", "--stdio")


# the stop sequence


def stopped(server: ScriptedServer, directory: Path, ready: bool = True) -> tuple[float, int]:
    """How long the stop sequence of a server takes, once it played its script (a script that
    waits for a message never does: `ready` false), and the exit code the server ended with."""

    async def stop() -> tuple[float, int]:
        process = await ServerProcess.start(server.arguments, directory, QUICK)
        eventually(server.ready if ready else server.calls, bool)
        begun = time.monotonic()
        await process.stop()
        return time.monotonic() - begun, await asyncio.wait_for(process.exited(), WAIT_S)

    return asyncio.run(stop())


def test_stopping_asks_for_shutdown_and_then_exit(server, tmp_path):
    server.play()
    _took, code = stopped(server, tmp_path)
    assert (server.methods(), code) == (["shutdown", "exit"], 0)


def test_shutdown_is_a_request_with_an_id_of_cstudys_and_exit_is_a_notification(server, tmp_path):
    server.play()
    stopped(server, tmp_path)
    shutdown, exit_message = server.received()
    assert (shutdown["id"], "id" in exit_message) == ("cstudy-shutdown", False)


def test_exit_waits_for_the_answer_to_shutdown(server, tmp_path):
    server.play(
        {"await": "shutdown"}, {"wait_for": str(server.gate("answer"))}, {"send": SHUTDOWN_ANSWER}
    )

    async def stop() -> tuple[list[str], list[str]]:
        process = await ServerProcess.start(server.arguments, tmp_path, QUICK)
        stopping = asyncio.create_task(process.stop())
        while server.methods() != ["shutdown"]:
            await asyncio.sleep(0.01)
        await asyncio.sleep(QUICK.shutdown_wait_s / 3)
        before = server.methods()
        server.gate("answer").touch()
        await asyncio.wait_for(stopping, WAIT_S)
        return before, server.methods()

    assert asyncio.run(stop()) == (["shutdown"], ["shutdown", "exit"])


def test_exit_comes_after_a_while_when_shutdown_goes_unanswered(server, tmp_path):
    server.play({"ignore": ["shutdown"]})
    took, _code = stopped(server, tmp_path)
    assert (server.methods(), took >= QUICK.shutdown_wait_s) == (["shutdown", "exit"], True)


def test_a_server_that_ignores_exit_ends_when_its_standard_input_closes(server, tmp_path):
    server.play({"ignore": ["exit"]})
    _took, code = stopped(server, tmp_path)
    assert (server.methods(), code) == (["shutdown", "exit"], 0)


def test_a_server_that_ignores_all_that_gets_sigterm_after_3_s(server, tmp_path):
    server.play({"ignore": ["shutdown", "exit", "eof"]})
    took, code = stopped(server, tmp_path)
    assert (code, took >= QUICK.terminate_after_s) == (SIGTERM_EXIT, True)


def test_a_server_that_ignores_sigterm_too_gets_sigkill_2_s_later(server, tmp_path):
    server.play({"ignore": ["shutdown", "exit", "eof", "SIGTERM"]})
    took, code = stopped(server, tmp_path)
    assert (code, took >= QUICK.terminate_after_s + QUICK.kill_after_s) == (SIGKILL_EXIT, True)


def test_a_process_the_server_left_in_its_group_is_ended_after_the_server_exits(server, tmp_path):
    pid_file = tmp_path / "sleeper.pid"
    server.play({"spawn_sleeper": str(pid_file)})
    try:
        took, code = stopped(server, tmp_path)
        assert (code, gone(pid_file), took >= QUICK.terminate_after_s + QUICK.kill_after_s) == (
            0,
            True,
            True,
        )
    finally:
        kill(pid_file)


def test_the_group_of_a_server_that_exited_by_itself_is_still_cleaned_up(server, tmp_path):
    pid_file = tmp_path / "sleeper.pid"
    server.play({"spawn_sleeper": str(pid_file)}, {"exit": 0})

    async def stop() -> bool:
        process = await ServerProcess.start(server.arguments, tmp_path, QUICK)
        await asyncio.wait_for(process.exited(), WAIT_S)
        left_behind = is_alive(int(pid_file.read_text()))
        await process.stop()
        return left_behind

    try:
        assert (asyncio.run(stop()), gone(pid_file)) == (True, True)
    finally:
        kill(pid_file)


def test_nothing_is_sent_to_a_server_that_already_exited(server, tmp_path):
    server.play({"exit": 0})

    async def stop() -> None:
        process = await ServerProcess.start(server.arguments, tmp_path, QUICK)
        await asyncio.wait_for(process.exited(), WAIT_S)
        await process.stop()

    asyncio.run(stop())
    assert server.received() == []


def test_messages_written_while_the_server_stops_are_read_and_dropped(server, tmp_path):
    server.play(
        {"await": "shutdown"},
        {"send": notification("noise")},
        {"send": answer(7)},
        {"send": SHUTDOWN_ANSWER},
    )
    stopped(server, tmp_path, ready=False)
    assert server.methods() == ["shutdown", "exit"]


# a server that reads nothing


@dataclass
class DeafStop:
    took: float
    code: int
    waiting: int
    """Sends still waiting for the server once the stop returned."""


def stop_of_a_deaf_server(server: ScriptedServer, directory: Path) -> DeafStop:
    """Stops a server that reads no input while messages it never read wait in the stream, which
    is what leaves a `drain` waiting: the reviewer's proof of a stop that never ends."""

    async def stop() -> DeafStop:
        process = await ServerProcess.start(server.arguments, directory, QUICK)
        eventually(server.ready, bool)
        sends = [asyncio.create_task(process.send("x" * MIB)) for _ in range(3)]
        await asyncio.sleep(0.2)
        begun = time.monotonic()
        try:
            await asyncio.wait_for(process.stop(), STOP_BOUND_S)
        finally:
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
        took = time.monotonic() - begun
        _, waiting = await asyncio.wait(sends, timeout=WAIT_S)
        return DeafStop(took, await asyncio.wait_for(process.exited(), WAIT_S), len(waiting))

    return asyncio.run(stop())


def test_a_server_that_reads_no_input_still_gets_sigterm_when_the_deadline_comes(server, tmp_path):
    server.play({"deaf": True})
    stopped = stop_of_a_deaf_server(server, tmp_path)
    assert (stopped.code, stopped.took >= QUICK.terminate_after_s) == (SIGTERM_EXIT, True)


def test_a_server_that_reads_no_input_and_ignores_sigterm_gets_sigkill_2_s_later(server, tmp_path):
    server.play({"deaf": True}, {"ignore": ["SIGTERM"]})
    stopped = stop_of_a_deaf_server(server, tmp_path)
    assert (stopped.code, stopped.took >= QUICK.terminate_after_s + QUICK.kill_after_s) == (
        SIGKILL_EXIT,
        True,
    )


def test_the_sends_that_wait_for_a_server_that_reads_nothing_end_when_it_is_stopped(
    server, tmp_path
):
    server.play({"deaf": True})
    assert stop_of_a_deaf_server(server, tmp_path).waiting == 0
