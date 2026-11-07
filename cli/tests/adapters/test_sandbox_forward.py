"""The forwarder, as a real process relaying to a real socket on this machine."""

import asyncio
import contextlib
import socket
import subprocess
import sys
from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from coding_study.adapters import sandbox_forward
from tests.waits import GENEROUS_WAIT_S

FORWARDER = Path(sandbox_forward.__file__)
STANDARD_LIBRARY_ONLY = ("asyncio", "signal", "sys", "collections.abc")


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


async def _answer(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    """Answers with what it read, once its client has closed its sending side."""
    received = await reader.read()
    writer.write(b"got:" + received)
    await writer.drain()
    writer.close()


@contextlib.asynccontextmanager
async def relay(listen: int, target: int) -> AsyncIterator[subprocess.Popen[bytes]]:
    process = subprocess.Popen(
        [sys.executable, "-I", str(FORWARDER), f"{listen}=127.0.0.1:{target}"]
    )
    try:
        deadline = asyncio.get_running_loop().time() + GENEROUS_WAIT_S
        while True:
            try:
                _, writer = await asyncio.open_connection("127.0.0.1", listen)
            except OSError:
                if asyncio.get_running_loop().time() > deadline:
                    raise
                await asyncio.sleep(0.02)
            else:
                writer.close()
                break
        yield process
    finally:
        process.terminate()
        process.wait(GENEROUS_WAIT_S)


def test_it_carries_a_request_and_its_answer_after_a_half_close():
    async def scenario() -> bytes:
        target = free_port()
        listen = free_port()
        server = await asyncio.start_server(_answer, "127.0.0.1", target)
        async with server, relay(listen, target):
            reader, writer = await asyncio.open_connection("127.0.0.1", listen)
            writer.write(b"ping")
            writer.write_eof()
            return await asyncio.wait_for(reader.read(), GENEROUS_WAIT_S)

    assert asyncio.run(scenario()) == b"got:ping"


def test_it_closes_a_client_when_the_target_is_down():
    async def scenario() -> bytes:
        listen = free_port()
        async with relay(listen, free_port()):
            reader, writer = await asyncio.open_connection("127.0.0.1", listen)
            data = await asyncio.wait_for(reader.read(), GENEROUS_WAIT_S)
            writer.close()
            return data

    assert asyncio.run(scenario()) == b""


def test_it_ends_at_once_on_sigterm():
    async def scenario() -> int | None:
        target = free_port()
        listen = free_port()
        async with relay(listen, target) as process:
            process.terminate()
            return await asyncio.to_thread(process.wait, GENEROUS_WAIT_S)

    assert asyncio.run(scenario()) == 0


@pytest.mark.parametrize("module", ["coding_study", "yaml", "typer"])
def test_it_imports_only_the_standard_library(module):
    assert f"import {module}" not in FORWARDER.read_text(encoding="utf-8")
