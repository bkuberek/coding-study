"""A real `cstudy serve` in a child process, for the slow tests of the web UI
(docs/specs/cli.md#cstudy-serve)."""

import os
import queue
import signal
import subprocess
import sys
import threading
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path

START_SECONDS = 90
"""Generous: the machine running the slow tests is often loaded."""
STOP_SECONDS = 30
URL_LABEL = "open"


@dataclass
class RunningServer:
    process: subprocess.Popen[str]
    login_url: str
    lines: "queue.Queue[str | None]" = field(default_factory=queue.Queue)
    environment: dict[str, str] = field(default_factory=dict[str, str])
    """The server's environment, for commands that must see the workspace as it does."""

    @property
    def address(self) -> str:
        return self.login_url.split("/?")[0]

    @property
    def port(self) -> int:
        return int(self.address.rsplit(":", 1)[1])

    def stop(self, signal_number: int) -> tuple[int, list[str]]:
        """The exit code and the lines printed after the URL."""
        self.process.send_signal(signal_number)
        exit_code = self.process.wait(STOP_SECONDS)
        return exit_code, list(iter(partial(self.lines.get, timeout=STOP_SECONDS), None))


def served_environment(workspace: Path) -> dict[str, str]:
    """The environment of a `cstudy` working on `workspace` with a config directory of its own."""
    return {
        **os.environ,
        "CSTUDY_WORKSPACE": str(workspace),
        "XDG_CONFIG_HOME": str(workspace.parent / "config"),
        "NO_COLOR": "1",
    }


@contextmanager
def running_server(
    workspace: Path,
    *arguments: str,
    ignore_interrupts: bool = False,
    variables: Mapping[str, str] | None = None,
) -> Iterator[RunningServer]:
    """`python -m coding_study serve`; with `ignore_interrupts`, started as a shell starts a
    background job, with SIGINT ignored; `variables` are added to its environment."""
    environment = {**served_environment(workspace), **(variables or {})}
    process = subprocess.Popen(
        [sys.executable, "-m", "coding_study", "serve", *arguments],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        env=environment,
        preexec_fn=_ignore_interrupts if ignore_interrupts else None,
    )
    lines: queue.Queue[str | None] = queue.Queue()
    threading.Thread(target=_read_lines, args=(process, lines), daemon=True).start()
    try:
        yield RunningServer(process, _login_url(lines), lines, environment)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()


def _read_lines(stream: "subprocess.Popen[str]", lines: "queue.Queue[str | None]") -> None:
    assert stream.stdout is not None
    for line in stream.stdout:
        lines.put(line.rstrip("\n"))
    lines.put(None)


def _ignore_interrupts() -> None:
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def _login_url(lines: "queue.Queue[str | None]") -> str:
    while (line := lines.get(timeout=START_SECONDS)) is not None:
        label, _, value = line.partition(" ")
        if label == URL_LABEL:
            return value.strip()
    raise AssertionError("cstudy serve printed no URL")
