"""A stand-in for the `cstudy` a server starts as a child (docs/specs/web-ui.md#testing): it
replays a scripted stream and answers signals as the script says.

    python scripted_child.py <script.json> --workspace <root> [--content <root>] <command> ...

It appends its pid and arguments as one JSON line to `<script>.calls`, then plays the script's
steps in order, each an object with one key:

    {"out": "<line>"}          writes a line to standard output
    {"err": "<line>"}          writes a line to standard error
    {"wait_for": "<path>"}     waits until the file exists
    {"exit": <code>}           exits
    {"on": {"SIGINT": [<steps>] | "ignore", ...}}   plays the steps, or nothing, on a signal
    {"leave_behind": "<path>"} starts a process in its own process group that holds standard
                               output open and outlives it, and writes that process's pid
    {"spawn_sleeper": "<path>"} starts a process that ignores SIGINT and SIGTERM in this one's
                               process group, and writes its pid
    {"read_line": "<path>"}    reads a line of standard input and appends it to the file

After the last step it waits for signals. It imports the standard library only, so it starts
fast.
"""

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from types import FrameType

SLEEPER = (
    "import signal, time; signal.signal(signal.SIGINT, signal.SIG_IGN); "
    "signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(120)"
)
LEFT_BEHIND = "import time; time.sleep(120)"
POLL_S = 0.01


def main(script_path: str, arguments: list[str]) -> None:
    script = Path(script_path)
    with script.with_suffix(".calls").open("a", encoding="utf-8") as calls:
        calls.write(json.dumps({"pid": os.getpid(), "arguments": arguments}) + "\n")
    play(json.loads(script.read_text(encoding="utf-8")))
    while True:
        signal.pause()


def play(steps: list[dict[str, object]]) -> None:
    for step in steps:
        [(name, value)] = step.items()
        STEPS[name](value)


def out(line: object) -> None:
    print(line, flush=True)


def err(line: object) -> None:
    print(line, file=sys.stderr, flush=True)


def wait_for(path: object) -> None:
    while not Path(str(path)).exists():
        time.sleep(POLL_S)


def exit_with(code: object) -> None:
    sys.stdout.flush()
    os._exit(int(str(code)))


def on(handlers: object) -> None:
    assert isinstance(handlers, dict)
    for name, steps in handlers.items():
        number = signal.Signals[name]
        if steps == "ignore":
            signal.signal(number, signal.SIG_IGN)
        else:
            signal.signal(number, _player(steps))


def leave_behind(pid_path: object) -> None:
    process = subprocess.Popen(
        [sys.executable, "-c", LEFT_BEHIND], stdout=sys.stdout, start_new_session=True
    )
    Path(str(pid_path)).write_text(str(process.pid))


def spawn_sleeper(pid_path: object) -> None:
    process = subprocess.Popen(
        [sys.executable, "-c", SLEEPER], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    Path(str(pid_path)).write_text(str(process.pid))


def read_line(path: object) -> None:
    with Path(str(path)).open("a", encoding="utf-8") as lines:
        lines.write(sys.stdin.readline())


def _player(steps: list[dict[str, object]]):
    def handle(_number: int, _frame: FrameType | None) -> None:
        play(steps)

    return handle


STEPS = {
    "out": out,
    "err": err,
    "wait_for": wait_for,
    "exit": exit_with,
    "on": on,
    "leave_behind": leave_behind,
    "spawn_sleeper": spawn_sleeper,
    "read_line": read_line,
}

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
