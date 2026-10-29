"""`cstudy test --debug` against the real runners, with the least a debugger client does.

Marked `slow`: each test runs `cstudy test <file> --debug` as a real process in a copy of the
session's practice workspace (the content is the Phase 4 fixture `level-store`, or `two-sum` for
Go and Rust), waits for the ready line on standard error, checks that the run is still waiting
after the language's normal hello timeout, attaches a client and lets the run finish with a
verdict. Python attaches over DAP and stops at a breakpoint; Go too, through Delve; Rust with
lldb in batch mode (`gdb-remote`), Node over the inspector protocol, both also at a breakpoint;
the JVM only gets the JDWP handshake and a resume (a breakpoint there is covered by hand with
jdb, see docs/specs/runners.md#debug-mode). Every runner is killed when its test ends.
"""

import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import suppress
from pathlib import Path

import pytest
from typer.testing import CliRunner

from coding_study.adapters.languages.debug_servers import InstalledDebugServers, this_machine
from coding_study.domain.debugging import DebugSession
from coding_study.domain.layout import SOURCE_EXTENSIONS
from coding_study.domain.problem import Language
from coding_study.domain.runs import HELLO_TIMEOUT_MS
from coding_study.entrypoints import cli
from tests.debug_clients import (
    DapClient,
    JdwpClient,
    end_lldb_session,
    run_cdp_client,
    run_lldb_client,
)
from tests.helpers import REPOSITORY_ROOT, SCHEMAS_DIRECTORY
from tests.workspaces import workspace_like

pytestmark = pytest.mark.slow

runner = CliRunner()
PHASE4 = Path(__file__).resolve().parents[2] / "fixtures" / "phase4" / "problems"
SOLUTIONS = PHASE4 / "0001-level-store" / "solutions"
USER_FILES = {
    Language.PYTHON: ("python/practice/level_store.py", ""),
    Language.TYPESCRIPT: ("typescript/practice/level-store.ts", ""),
    Language.JAVA: (
        "jvm/java/src/main/java/practice/level_store/LevelStore.java",
        "package practice.level_store;\n\n",
    ),
    Language.KOTLIN: (
        "jvm/kotlin/src/main/kotlin/practice/level_store/LevelStore.kt",
        "package practice.level_store\n\n",
    ),
}
BREAKPOINT_LINES = {Language.PYTHON: 6, Language.TYPESCRIPT: 5}
"""The statement in `put`, in the reference solutions."""
TWO_SUM = REPOSITORY_ROOT / "problems" / "0001-two-sum"
TWO_SUM_FILES = {
    Language.GO: "go/practice/two_sum/two_sum.go",
    Language.RUST: "rust/practice/two_sum.rs",
}
TWO_SUM_BREAKPOINT_LINE = 6
"""The lookup in the loop of the hash-map references."""
RUST_NEVER_RETURNS = """pub fn two_sum(nums: Vec<i32>, target: i32) -> Vec<i32> {
    let _ = (nums, target);
    loop {
        std::thread::sleep(std::time::Duration::from_millis(50));
    }
}
"""
DEBUG_SERVERS = InstalledDebugServers(this_machine())
NO_DELVE = DEBUG_SERVERS.delve().path is None or shutil.which("go") is None
NO_LLDB = any(
    (
        DEBUG_SERVERS.lldb_server().path is None,
        shutil.which("lldb") is None,
        not shutil.which("cargo"),
    )
)
LAUNCH = "from coding_study.entrypoints.launcher import main; main()"
READY_TIMEOUT_SECONDS = 240
EXIT_TIMEOUT_SECONDS = 120
PASSED_LINE = "all passed (debug run: not recorded; cstudy test records the run)"


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


class DebuggedRun:
    """A `cstudy test --debug` process and what it printed."""

    def __init__(self, arguments: list[str], environment: dict[str, str], output: Path) -> None:
        self._stdout_path = output / "stdout.txt"
        self._stderr_path = output / "stderr.txt"
        with self._stdout_path.open("wb") as stdout, self._stderr_path.open("wb") as stderr:
            self._process = subprocess.Popen(
                [sys.executable, "-c", LAUNCH, "test", *arguments],
                stdout=stdout,
                stderr=stderr,
                env=environment,
                start_new_session=True,
            )

    @property
    def stdout(self) -> str:
        return self._stdout_path.read_text()

    @property
    def stderr(self) -> str:
        return self._stderr_path.read_text()

    def wait_for_ready_line(self, line: str) -> None:
        deadline = time.monotonic() + READY_TIMEOUT_SECONDS
        while line not in self.stderr.splitlines():
            if self._process.poll() is not None or time.monotonic() > deadline:
                pytest.fail(f"no ready line {line!r}; exit {self._process.poll()}:\n{self.stderr}")
            time.sleep(0.05)

    def is_waiting(self) -> bool:
        return self._process.poll() is None

    def finish(self) -> int:
        return self._process.wait(timeout=EXIT_TIMEOUT_SECONDS)

    def interrupt(self) -> None:
        self._process.send_signal(signal.SIGINT)

    def stop(self) -> None:
        """SIGTERM makes `cstudy` kill its runner; SIGKILL only if it does not end."""
        if self._process.poll() is not None:
            return
        self._process.send_signal(signal.SIGTERM)
        try:
            self._process.wait(timeout=30)
        except subprocess.TimeoutExpired:
            os.killpg(self._process.pid, signal.SIGKILL)
            self._process.wait()


@pytest.fixture(scope="module")
def content(tmp_path_factory: pytest.TempPathFactory) -> Path:
    content = tmp_path_factory.mktemp("debug-content")
    shutil.copytree(SCHEMAS_DIRECTORY, content / "schemas")
    shutil.copytree(PHASE4, content / "problems")
    (content / "runners").symlink_to(REPOSITORY_ROOT / "runners", target_is_directory=True)
    return content


@pytest.fixture(scope="module")
def root(tmp_path_factory: pytest.TempPathFactory, practice_workspace: Path) -> Path:
    return workspace_like(practice_workspace, tmp_path_factory.mktemp("debug") / "ws")


@pytest.fixture(scope="module")
def two_sum_content(tmp_path_factory: pytest.TempPathFactory) -> Path:
    content = tmp_path_factory.mktemp("debug-two-sum-content")
    shutil.copytree(SCHEMAS_DIRECTORY, content / "schemas")
    shutil.copytree(TWO_SUM, content / "problems" / TWO_SUM.name)
    (content / "runners").symlink_to(REPOSITORY_ROOT / "runners", target_is_directory=True)
    return content


@pytest.fixture(scope="module")
def compiled_root(tmp_path_factory: pytest.TempPathFactory, practice_workspace: Path) -> Path:
    """A workspace with the Go and Rust projects too."""
    root = workspace_like(practice_workspace, tmp_path_factory.mktemp("debug-compiled") / "ws")
    for project in TWO_SUM_FILES:
        shutil.copytree(practice_workspace / project, root / project)
    return root


@pytest.fixture
def environment(
    root: Path, content: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, str]:
    return cstudy_environment(root, content, tmp_path, monkeypatch)


def cstudy_environment(
    root: Path, content: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> dict[str, str]:
    """The environment of `cstudy`: this process's too, so `cstudy start` finds the workspace."""
    for name, value in (
        ("CSTUDY_CONTENT", content),
        ("CSTUDY_WORKSPACE", root),
        ("CSTUDY_CONFIG", tmp_path / "absent-config.toml"),
    ):
        monkeypatch.setenv(name, str(value))
    return dict(os.environ)


class Debugging:
    def __init__(self, environment: dict[str, str], tmp_path: Path) -> None:
        self._environment = environment
        self._tmp_path = tmp_path
        self._runs: list[DebuggedRun] = []

    def solved(self, language: Language) -> Path:
        """Starts the attempt and writes the reference solution; returns the user's file."""
        started = runner.invoke(cli.app, ["start", "level-store", "--lang", language, "--no-open"])
        assert started.exit_code == 0, started.output
        path, package = USER_FILES[language]
        file = Path(self._environment["CSTUDY_WORKSPACE"]) / path
        reference = SOLUTIONS / f"hash-map.{SOURCE_EXTENSIONS[language]}"
        file.write_text(package + reference.read_text())
        return file

    def solved_two_sum(self, language: Language) -> Path:
        """The same for two-sum, whose references declare the stub's package."""
        started = runner.invoke(cli.app, ["start", "two-sum", "--lang", language, "--no-open"])
        assert started.exit_code == 0, started.output
        file = Path(self._environment["CSTUDY_WORKSPACE"]) / TWO_SUM_FILES[language]
        reference = TWO_SUM / "solutions" / f"hash-map.{SOURCE_EXTENSIONS[language]}"
        file.write_text(reference.read_text())
        return file

    def start(self, file: Path, *options: str) -> DebuggedRun:
        output = self._tmp_path / f"run-{len(self._runs)}"
        output.mkdir()
        run = DebuggedRun([str(file), "--debug", *options], self._environment, output)
        self._runs.append(run)
        return run

    def stop_everything(self) -> None:
        for run in self._runs:
            run.stop()


@pytest.fixture
def debugged(environment: dict[str, str], tmp_path: Path) -> Iterator[Debugging]:
    debugging = Debugging(environment, tmp_path)
    yield debugging
    debugging.stop_everything()


@pytest.fixture
def compiled(
    compiled_root: Path, two_sum_content: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[Debugging]:
    environment = cstudy_environment(compiled_root, two_sum_content, tmp_path, monkeypatch)
    debugging = Debugging(environment, tmp_path)
    yield debugging
    debugging.stop_everything()


def processes_running_from(directory: Path) -> list[str]:
    """The processes whose command line names `directory`: the runner started from a binary there,
    and the debug server that was given its path."""
    listing = subprocess.run(
        ["ps", "-axww", "-o", "pid=,args="], capture_output=True, text=True, check=True
    ).stdout
    names = (str(directory), str(directory.resolve()))
    return [line.strip() for line in listing.splitlines() if any(name in line for name in names)]


def kill_going(processes: list[str]) -> None:
    """Whatever a failing test left running would spin on for good."""
    for process in processes:
        with suppress(ProcessLookupError):
            os.kill(int(process.split()[0]), signal.SIGKILL)


def private_binaries(root: Path, language: Language) -> Path:
    """Where each run of a compiled language starts its own copy of the runner."""
    return root / ".cs" / "build" / language.value / "run"


def hello_timeout_seconds(language: Language) -> float:
    return HELLO_TIMEOUT_MS[language] / 1000


def wait_longer_than_the_hello_timeout(language: Language, run: DebuggedRun) -> bool:
    """True when the runner is still waiting for the debugger after its hello timeout."""
    time.sleep(hello_timeout_seconds(language) + 0.5)
    return run.is_waiting()


def test_python_waits_for_debugpy_stops_at_a_breakpoint_and_gives_a_verdict(debugged):
    file = debugged.solved(Language.PYTHON)
    port = free_port()
    run = debugged.start(file, "--debug-port", str(port))
    run.wait_for_ready_line(DebugSession(Language.PYTHON, port).ready_line)
    assert wait_longer_than_the_hello_timeout(Language.PYTHON, run)
    client = DapClient(port)
    stopped_at = client.stop_at(file, BREAKPOINT_LINES[Language.PYTHON])
    client.finish(file)
    assert (Path(stopped_at[0]).resolve(), stopped_at[1], run.finish()) == (
        file.resolve(),
        BREAKPOINT_LINES[Language.PYTHON],
        0,
    )
    assert PASSED_LINE in run.stdout.splitlines()


def test_typescript_waits_for_the_inspector_stops_at_a_breakpoint_and_gives_a_verdict(debugged):
    file = debugged.solved(Language.TYPESCRIPT)
    port = free_port()
    run = debugged.start(file, "--debug-port", str(port))
    run.wait_for_ready_line(DebugSession(Language.TYPESCRIPT, port).ready_line)
    assert wait_longer_than_the_hello_timeout(Language.TYPESCRIPT, run)
    printed = run_cdp_client(port, file, BREAKPOINT_LINES[Language.TYPESCRIPT])
    assert (printed.startswith("STOP AT line 5 in put"), run.finish()) == (True, 0)
    assert PASSED_LINE in run.stdout.splitlines()


@pytest.mark.skipif(NO_DELVE, reason="go or dlv is not installed")
def test_go_waits_for_delve_stops_at_a_breakpoint_and_gives_a_verdict(compiled):
    file = compiled.solved_two_sum(Language.GO)
    port = free_port()
    run = compiled.start(file, "--debug-port", str(port))
    run.wait_for_ready_line(DebugSession(Language.GO, port).ready_line)
    assert wait_longer_than_the_hello_timeout(Language.GO, run)
    client = DapClient(port, {"mode": "remote"})
    stopped_at = client.stop_at(file, TWO_SUM_BREAKPOINT_LINE)
    client.run_to_end(file)
    assert (Path(stopped_at[0]).resolve(), stopped_at[1], run.finish()) == (
        file.resolve(),
        TWO_SUM_BREAKPOINT_LINE,
        0,
    )
    assert PASSED_LINE in run.stdout.splitlines()


@pytest.mark.skipif(NO_LLDB, reason="cargo, lldb or its debug server is not installed")
def test_rust_waits_for_the_lldb_server_stops_at_a_breakpoint_and_gives_a_verdict(compiled):
    file = compiled.solved_two_sum(Language.RUST)
    port = free_port()
    run = compiled.start(file, "--debug-port", str(port))
    run.wait_for_ready_line(DebugSession(Language.RUST, port).ready_line)
    assert wait_longer_than_the_hello_timeout(Language.RUST, run)
    printed = run_lldb_client(port, file, TWO_SUM_BREAKPOINT_LINE)
    assert "name = 'cs-runner-cases', stop reason = breakpoint 1.1" in printed
    assert f"at {file.name}:{TWO_SUM_BREAKPOINT_LINE}:" in printed
    assert run.finish() == 0
    assert PASSED_LINE in run.stdout.splitlines()


@pytest.mark.parametrize("language", [Language.JAVA, Language.KOTLIN])
def test_the_jvm_waits_for_jdwp_and_runs_after_the_handshake_and_a_resume(debugged, language):
    file = debugged.solved(language)
    port = free_port()
    run = debugged.start(file, "--debug-port", str(port))
    run.wait_for_ready_line(DebugSession(language, port).ready_line)
    assert wait_longer_than_the_hello_timeout(language, run)
    client = JdwpClient.connect(port)
    client.resume()
    assert run.finish() == 0
    client.close()
    assert PASSED_LINE in run.stdout.splitlines()


def test_the_jvm_connects_to_an_ide_that_starts_listening_late(debugged):
    file = debugged.solved(Language.JAVA)
    port = free_port()
    run = debugged.start(file, "--debug-connect", "--debug-port", str(port))
    run.wait_for_ready_line(DebugSession(Language.JAVA, port, connect=True).ready_line)
    time.sleep(2.5)
    client = JdwpClient.accept(port)
    client.resume()
    assert run.finish() == 0
    client.close()
    assert PASSED_LINE in run.stdout.splitlines()


def test_stopping_a_waiting_run_frees_the_debug_port(debugged):
    file = debugged.solved(Language.PYTHON)
    port = free_port()
    run = debugged.start(file, "--debug-port", str(port))
    run.wait_for_ready_line(DebugSession(Language.PYTHON, port).ready_line)
    run.interrupt()
    assert run.finish() == 130
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", port))


COMPILED_LANGUAGES = [
    pytest.param(
        Language.GO, marks=pytest.mark.skipif(NO_DELVE, reason="go or dlv is not installed")
    ),
    pytest.param(
        Language.RUST,
        marks=pytest.mark.skipif(NO_LLDB, reason="cargo, lldb or its debug server is missing"),
    ),
]


@pytest.mark.parametrize("language", COMPILED_LANGUAGES)
def test_stopping_a_compiled_run_that_waits_for_its_debug_server_frees_the_port(compiled, language):
    file = compiled.solved_two_sum(language)
    port = free_port()
    run = compiled.start(file, "--debug-port", str(port))
    run.wait_for_ready_line(DebugSession(language, port).ready_line)
    run.stop()
    assert run.finish() == 143
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", port))


@pytest.mark.parametrize("language", COMPILED_LANGUAGES)
def test_stopping_a_compiled_run_that_waits_for_its_debug_server_leaves_nothing_going(
    compiled, compiled_root, language
):
    file = compiled.solved_two_sum(language)
    port = free_port()
    run = compiled.start(file, "--debug-port", str(port))
    run.wait_for_ready_line(DebugSession(language, port).ready_line)
    run.stop()
    run.finish()
    going = processes_running_from(private_binaries(compiled_root, language))
    kill_going(going)
    assert going == []


@pytest.mark.skipif(NO_LLDB, reason="cargo, lldb or its debug server is not installed")
@pytest.mark.parametrize("ending", ["process detach", "process kill"])
def test_a_rust_run_leaves_nothing_going_when_the_debugger_ends_the_session(
    compiled, compiled_root, ending
):
    """`process detach` is how CodeLLDB ends an attach session: `debugserver` then exits, and
    the runner, which has no time limit under a debugger, would run its loop for good."""
    file = compiled.solved_two_sum(Language.RUST)
    file.write_text(RUST_NEVER_RETURNS)
    port = free_port()
    run = compiled.start(file, "--debug-port", str(port))
    run.wait_for_ready_line(DebugSession(Language.RUST, port).ready_line)
    end_lldb_session(port, ending)
    run.finish()
    going = processes_running_from(private_binaries(compiled_root, Language.RUST))
    kill_going(going)
    assert going == []


def test_a_port_in_use_is_reported_before_anything_starts(debugged):
    file = debugged.solved(Language.TYPESCRIPT)
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        busy = listener.getsockname()[1]
        run = debugged.start(file, "--debug-port", str(busy))
        assert run.finish() == 4
    assert f"port {busy} on 127.0.0.1 is already in use" in run.stderr
