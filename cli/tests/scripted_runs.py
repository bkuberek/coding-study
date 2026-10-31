"""Scripted children for the streaming tests of the web UI (docs/specs/web-ui.md#testing): golden
`--events` lines, the script `tests/scripted_child.py` plays, and a reader of server-sent events.
"""

import json
import os
import signal
import sys
import time
from collections.abc import Callable, Iterable, Iterator
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from coding_study.entrypoints.web.children import ChildCommand
from coding_study.entrypoints.web.runs import ChildTiming

SCRIPTED_CHILD = Path(__file__).with_name("scripted_child.py")
QUICK = ChildTiming(terminate_after_s=0.4, kill_after_s=0.4, keep_alive_s=30, drain_s=0.3)
"""A cancel ladder of a fraction of a second, and no keep-alive in a short test's stream."""
WAIT_S = 10.0
POLL_S = 0.01


def event(event_type: str, **fields: Any) -> str:
    return json.dumps({"type": event_type, "version": 1, **fields})


RUN_START = event(
    "run_start",
    command="test",
    slug="two-sum",
    language="python",
    attempt_id=1,
    mode="new",
    levels=None,
    kind="function",
    track="dsa",
    timer=None,
    time_limit=None,
    planned={
        "cases": 2,
        "visible": 2,
        "hidden": 0,
        "generated": 0,
        "oracle_inputs": 0,
        "stress": None,
    },
)
CASE_START = event("case_start", id="ex1", visible=True, level=None)
CASE_RESULT = event(
    "case_result",
    id="ex1",
    visible=True,
    generated=False,
    status="pass",
    duration_ns=41000,
    level=None,
)
SUMMARY = {"slug": "two-sum", "tally": {"total": 2, "passed": 2}, "duration_s": 0.94}
RUN_END = event("run_end", outcome="passed", exit_code=0, message=None, summary=SUMMARY)
INTERRUPTED = event("run_end", outcome="interrupted", exit_code=130, message=None, summary=None)
PASSING_RUN = (RUN_START, CASE_START, CASE_RESULT, RUN_END)


def outs(*lines: str) -> list[dict[str, object]]:
    return [{"out": line} for line in lines]


def answers_interrupt(exit_code: int = 130) -> dict[str, object]:
    """The step that makes a child stop as `cstudy test --events` does on SIGINT."""
    return {"on": {"SIGINT": [{"out": INTERRUPTED}, {"exit": exit_code}]}}


@dataclass(frozen=True)
class Script:
    """The steps of every child a test's server starts, and what each child was called with."""

    path: Path

    def play(self, *steps: dict[str, object]) -> None:
        self.path.write_text(json.dumps(steps), encoding="utf-8")

    @property
    def child(self) -> ChildCommand:
        return ChildCommand(interpreter=(sys.executable, str(SCRIPTED_CHILD), str(self.path)))

    def calls(self) -> list[dict[str, Any]]:
        calls = self.path.with_suffix(".calls")
        if not calls.exists():
            return []
        return [json.loads(line) for line in calls.read_text(encoding="utf-8").splitlines()]

    def arguments(self) -> list[str]:
        """The `cstudy` arguments of the last child, after `--workspace <root>`, once it ran."""
        return eventually(self.calls, bool)[-1]["arguments"][2:]

    def pid(self) -> int:
        """The process id of the last child, once it ran."""
        return eventually(self.calls, bool)[-1]["pid"]

    def gate(self, name: str) -> Path:
        """A file a `wait_for` step waits on; the test creates it to let the child go on."""
        return self.path.with_name(name)


@dataclass(frozen=True)
class Frame:
    event: str
    data: Any
    id: int | None


def frames(body: str) -> list[Frame]:
    """The messages of a whole server-sent event stream."""
    return list(read_frames(body.splitlines()))


def read_frames(lines: Iterable[str]) -> Iterator[Frame]:
    """Each message as its blank line ends it, without the comment lines."""
    fields: dict[str, str] = {}
    for line in lines:
        if line:
            if not line.startswith(":"):
                name, _, value = line.partition(": ")
                fields[name] = value
            continue
        if fields:
            identity = fields.get("id")
            data = json.loads(fields["data"])
            yield Frame(fields["event"], data, None if identity is None else int(identity))
        fields = {}


def eventually[Value](read: Callable[[], Value], done: Callable[[Value], bool]) -> Value:
    """`read()` once `done` holds for it; fails after WAIT_S."""
    deadline = time.monotonic() + WAIT_S
    while True:
        value = read()
        if done(value):
            return value
        if time.monotonic() > deadline:
            raise AssertionError(f"still {value!r} after {WAIT_S} s")
        time.sleep(POLL_S)


def is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def gone(pid_file: Path) -> bool:
    """Whether the process whose pid the file holds has exited, waiting for it a while."""
    pid = int(eventually(pid_file.read_text, bool) if pid_file.exists() else "0")
    if not pid:
        return False
    try:
        eventually(lambda: is_alive(pid), lambda alive: not alive)
    except AssertionError:
        return False
    return True


def kill(pid_file: Path) -> None:
    if pid_file.exists():
        with suppress(ProcessLookupError):
            os.kill(int(pid_file.read_text()), signal.SIGKILL)


def lines_of(frames_found: list[Frame], event_type: str) -> Iterator[Any]:
    return (frame.data for frame in frames_found if frame.event == event_type)
