"""The Python runner under debugpy (docs/specs/runners.md#debug-mode)."""

import json
import socket
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest

from coding_study.adapters.languages.python.runner import (
    DEBUG_BOOTSTRAP,
    READY_MARKER,
    PythonRunner,
)
from coding_study.application.ports import Prepared, ProbeResult, UserCode
from coding_study.domain.debugging import DebugSession
from coding_study.domain.errors import RunnerStartError
from coding_study.domain.problem import Language
from coding_study.domain.runs import HELLO_TIMEOUT_MS
from tests.stub_contract import STUB_CASES

TWO_SUM = next(case.meta for case in STUB_CASES if case.name == "two-sum")
INTERPRETER = Path("python/.venv/bin/python")
SESSION = DebugSession(Language.PYTHON, 5678)
IMPORT_DEBUGPY = ("-c", "import debugpy")
IMPORTABLE = ProbeResult(0, "")


class FakeProbe:
    def __init__(self, result: ProbeResult | None = IMPORTABLE) -> None:
        self.result = result
        self.commands: list[tuple[str, ...]] = []

    def run(self, command: Sequence[str]) -> ProbeResult | None:
        self.commands.append(tuple(command))
        return self.result


@pytest.fixture
def root(tmp_path: Path) -> Path:
    interpreter = tmp_path / INTERPRETER
    interpreter.parent.mkdir(parents=True)
    interpreter.touch()
    return tmp_path


def prepare_debug(
    root: Path,
    session: DebugSession = SESSION,
    probe: FakeProbe | None = None,
    notices: list[str] | None = None,
) -> Prepared:
    runner = PythonRunner(root, probe or FakeProbe())
    result = runner.prepare(
        UserCode(TWO_SUM, debug=session), (notices if notices is not None else []).append
    )
    assert isinstance(result, Prepared)
    return result


def test_the_runner_starts_through_the_bootstrap_with_the_port(root):
    command = prepare_debug(root).launch.command
    assert command == (
        str(root / INTERPRETER),
        "-X",
        "frozen_modules=off",
        "-c",
        DEBUG_BOOTSTRAP,
        "5678",
    )


def test_the_port_of_the_session_is_the_bootstraps_argument(root):
    command = prepare_debug(root, DebugSession(Language.PYTHON, 6000)).launch.command
    assert command[-1] == "6000"


def test_the_launch_asks_for_the_ready_marker_the_bootstrap_prints(root):
    debug = prepare_debug(root).launch.debug
    assert debug is not None
    assert debug.ready_marker == READY_MARKER


def test_the_launch_announces_through_the_notice(root):
    notices: list[str] = []
    debug = prepare_debug(root, notices=notices).launch.debug
    assert debug is not None
    debug.announce("a line")
    assert notices == ["a line"]


def test_the_launch_carries_the_session(root):
    debug = prepare_debug(root).launch.debug
    assert debug is not None
    assert debug.session == SESSION


def test_the_runner_still_starts_in_the_python_workspace(root):
    assert prepare_debug(root).launch.cwd == root / "python"


def test_debugpy_is_asked_of_the_workspace_interpreter(root):
    probe = FakeProbe()
    prepare_debug(root, probe=probe)
    assert probe.commands == [(str(root / INTERPRETER), *IMPORT_DEBUGPY)]


@pytest.mark.parametrize("missing", [ProbeResult(1, "ModuleNotFoundError"), None])
def test_without_debugpy_the_error_names_the_fix(root, missing):
    with pytest.raises(RunnerStartError) as raised:
        prepare_debug(root, probe=FakeProbe(missing))
    assert str(raised.value) == (
        "cannot debug python: debugpy is not installed in python/.venv; "
        "run `uv add --dev debugpy --directory python`"
    )


def test_a_normal_run_does_not_ask_for_debugpy(root):
    probe = FakeProbe()
    PythonRunner(root, probe).prepare(UserCode(TWO_SUM), lambda _line: None)
    assert probe.commands == []


def test_a_port_in_use_is_an_environment_error(root):
    with socket.socket() as listener:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        busy = DebugSession(Language.PYTHON, listener.getsockname()[1])
        with pytest.raises(RunnerStartError, match="--debug-port"):
            prepare_debug(root, busy)


def test_the_debug_launch_keeps_the_python_hello_timeout(root):
    assert prepare_debug(root).launch.hello_timeout_ms == HELLO_TIMEOUT_MS[Language.PYTHON]


# The bootstrap itself, run by a real interpreter with stand-ins for debugpy and cs_runner.

FAKE_DEBUGPY = """
import sys


def listen(address):
    print(f"listen {address[0]}:{address[1]}", file=sys.stderr, flush=True)


def wait_for_client():
    print("wait_for_client", file=sys.stderr, flush=True)
"""
FAKE_RUNNER_MODULE = "import json, sys\nprint(json.dumps(sys.argv[1:]))\n"


@pytest.fixture
def stand_ins(tmp_path: Path) -> Path:
    modules = tmp_path / "modules"
    (modules / "cs_runner").mkdir(parents=True)
    (modules / "debugpy.py").write_text(FAKE_DEBUGPY)
    (modules / "cs_runner" / "__init__.py").write_text("")
    (modules / "cs_runner" / "__main__.py").write_text(FAKE_RUNNER_MODULE)
    return modules


def bootstrapped(stand_ins: Path, port: int = 6001) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        "-X",
        "frozen_modules=off",
        "-c",
        DEBUG_BOOTSTRAP,
        str(port),
        "--request",
        "r.json",
        "--out",
        "o.jsonl",
    ]
    environment = {"PYTHONPATH": str(stand_ins), "PATH": ""}
    return subprocess.run(
        command, capture_output=True, text=True, check=True, env=environment, timeout=30
    )


def test_the_bootstrap_listens_on_the_loopback_interface_only(stand_ins):
    assert bootstrapped(stand_ins).stderr.splitlines()[0] == "listen 127.0.0.1:6001"


def test_the_bootstrap_says_ready_after_listening_and_before_waiting(stand_ins):
    assert bootstrapped(stand_ins).stderr.splitlines() == [
        "listen 127.0.0.1:6001",
        READY_MARKER,
        "wait_for_client",
    ]


def test_the_bootstrap_hands_the_runner_its_own_arguments(stand_ins):
    output = bootstrapped(stand_ins).stdout
    assert json.loads(output) == ["--request", "r.json", "--out", "o.jsonl"]
