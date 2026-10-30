import signal
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

from coding_study.adapters import debug_process
from coding_study.adapters.debug_process import (
    TAIL_LINES,
    DebugOutput,
    _started_from,
    kill_processes_started_from,
)
from coding_study.application.ports import DebugLaunch
from coding_study.domain.debugging import DebugSession
from coding_study.domain.problem import Language

READY = "agent is listening"
REFUSED = "connect failed"


def output_of(
    tmp_path: Path,
    *,
    connect: bool = False,
    ready: str = READY,
    refused: str = REFUSED,
    ready_file: Path | None = None,
) -> DebugOutput:
    session = DebugSession(Language.JAVA, 5005, connect)
    debug = DebugLaunch(session, lambda _line: None, ready, refused, ready_file)
    return DebugOutput(debug, tmp_path / "stdout.txt", tmp_path / "stderr.txt")


def append(path: Path, text: str) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(text)


def test_nothing_is_listening_before_the_runner_printed_anything(tmp_path):
    assert output_of(tmp_path).agent_listens() is False


@pytest.mark.parametrize("name", ["stdout.txt", "stderr.txt"])
def test_the_marker_is_found_on_either_stream(tmp_path, name):
    output = output_of(tmp_path)
    append(tmp_path / name, f"banner\n{READY} on 5005\n")
    assert output.agent_listens() is True


def test_a_marker_that_arrives_in_two_pieces_is_found(tmp_path):
    output = output_of(tmp_path)
    append(tmp_path / "stderr.txt", "agent is ")
    assert output.agent_listens() is False
    append(tmp_path / "stderr.txt", "listening\n")
    assert output.agent_listens() is True


def test_a_launch_without_a_ready_marker_never_listens(tmp_path):
    output = output_of(tmp_path, ready="")
    append(tmp_path / "stdout.txt", "anything\n")
    assert output.agent_listens() is False


def test_an_agent_listens_once_it_wrote_to_its_ready_file(tmp_path):
    ready_file = tmp_path / "debug-port"
    ready_file.write_bytes(b"")
    output = output_of(tmp_path, ready="", ready_file=ready_file)
    assert output.agent_listens() is False
    ready_file.write_bytes(b"12345\0")
    assert output.agent_listens() is True


def test_a_ready_file_that_does_not_exist_means_nothing_listens(tmp_path):
    output = output_of(tmp_path, ready="", ready_file=tmp_path / "removed")
    assert output.agent_listens() is False


def test_a_refused_connection_is_recognized_when_connecting(tmp_path):
    output = output_of(tmp_path, connect=True)
    append(tmp_path / "stderr.txt", f"ERROR: {REFUSED}: Connection refused\n")
    assert output.refused_connection() is True


def test_the_refusal_text_means_nothing_when_the_runner_listens(tmp_path):
    output = output_of(tmp_path, connect=False)
    append(tmp_path / "stderr.txt", f"ERROR: {REFUSED}\n")
    assert output.refused_connection() is False


def test_the_tail_has_standard_output_first_then_standard_error(tmp_path):
    output = output_of(tmp_path)
    append(tmp_path / "stdout.txt", "out 1\nout 2\n")
    append(tmp_path / "stderr.txt", "err 1\n")
    assert output.tail() == ("out 1", "out 2", "err 1")


def test_the_tail_keeps_the_last_lines_of_each_stream(tmp_path):
    output = output_of(tmp_path)
    append(tmp_path / "stderr.txt", "".join(f"line {number}\n" for number in range(TAIL_LINES + 5)))
    assert (output.tail()[0], output.tail()[-1], len(output.tail())) == (
        "line 5",
        f"line {TAIL_LINES + 4}",
        TAIL_LINES,
    )


# Processes left behind by a debug server that let go of its runner.

GRACE_SECONDS = 0.1
"""Short: a killed child of this test stays a zombie until the test waits for it."""
ENDED_BY_KILL = -signal.SIGKILL
SLEEP_FOR_A_MINUTE = "import time; time.sleep(60)"


@pytest.fixture
def started() -> Iterator[list[subprocess.Popen[bytes]]]:
    """Processes the test started, killed at the end whatever the test did."""
    processes: list[subprocess.Popen[bytes]] = []
    yield processes
    for process in processes:
        process.kill()
        process.wait()


def start_in(
    directory: Path, processes: list[subprocess.Popen[bytes]], *extra: str
) -> subprocess.Popen[bytes]:
    """A process whose executable is a file of `directory`, in a session of its own as the
    runner of `debugserver` is."""
    directory.mkdir(parents=True, exist_ok=True)
    binary = directory / "cs-runner"
    if not binary.exists():
        binary.symlink_to(sys.executable)
    process = subprocess.Popen(
        [str(binary), "-c", SLEEP_FOR_A_MINUTE, *extra], start_new_session=True
    )
    processes.append(process)
    return process


def is_running(process: subprocess.Popen[bytes]) -> bool:
    try:
        process.wait(timeout=GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        return True
    return False


def test_a_process_started_from_the_directory_is_killed(tmp_path, started):
    left_behind = start_in(tmp_path / "scratch", started)
    kill_processes_started_from(tmp_path / "scratch", GRACE_SECONDS)
    assert left_behind.wait(timeout=5) == ENDED_BY_KILL


def test_every_process_started_from_the_directory_is_killed(tmp_path, started):
    first = start_in(tmp_path / "scratch", started)
    second = start_in(tmp_path / "scratch", started)
    kill_processes_started_from(tmp_path / "scratch", GRACE_SECONDS)
    assert (first.wait(timeout=5), second.wait(timeout=5)) == (ENDED_BY_KILL, ENDED_BY_KILL)


def test_a_directory_with_a_space_in_its_name_is_matched(tmp_path, started):
    left_behind = start_in(tmp_path / "my workspace" / "scratch", started)
    kill_processes_started_from(tmp_path / "my workspace" / "scratch", GRACE_SECONDS)
    assert left_behind.wait(timeout=5) == ENDED_BY_KILL


def test_a_process_started_from_elsewhere_is_left_alone(tmp_path, started):
    other = subprocess.Popen([sys.executable, "-c", SLEEP_FOR_A_MINUTE])
    started.append(other)
    start_in(tmp_path / "scratch", started)
    kill_processes_started_from(tmp_path / "scratch", GRACE_SECONDS)
    assert is_running(other)


def test_a_sibling_directory_with_the_same_beginning_is_left_alone(tmp_path, started):
    """`run/1-ab` is no prefix of the directory `run/1-abc`."""
    neighbour = start_in(tmp_path / "run" / "1-abc", started)
    start_in(tmp_path / "run" / "1-ab", started)
    kill_processes_started_from(tmp_path / "run" / "1-ab", GRACE_SECONDS)
    assert is_running(neighbour)


def test_a_process_that_only_mentions_the_directory_is_left_alone(tmp_path, started):
    """A viewer of a file in the directory does not run anything from it."""
    mentioning = subprocess.Popen(
        [sys.executable, "-c", SLEEP_FOR_A_MINUTE, str(tmp_path / "scratch" / "log.txt")]
    )
    started.append(mentioning)
    start_in(tmp_path / "scratch", started)
    kill_processes_started_from(tmp_path / "scratch", GRACE_SECONDS)
    assert is_running(mentioning)


def test_a_launch_without_a_scratch_directory_has_nothing_to_kill(tmp_path, started):
    unrelated = start_in(tmp_path / "scratch", started)
    kill_processes_started_from(None, GRACE_SECONDS)
    assert is_running(unrelated)


def test_a_directory_nothing_ran_from_is_no_error(tmp_path):
    kill_processes_started_from(tmp_path / "never-created", GRACE_SECONDS)


def test_a_machine_without_ps_leaves_the_processes_alone_without_failing(
    monkeypatch, tmp_path, started
):
    def missing_ps(*_arguments, **_keywords):
        raise FileNotFoundError("ps")

    monkeypatch.setattr(debug_process.subprocess, "run", missing_ps)
    monkeypatch.setattr(debug_process, "PROC_ROOT", tmp_path / "no-proc")
    left_behind = start_in(tmp_path / "scratch", started)
    kill_processes_started_from(tmp_path / "scratch", GRACE_SECONDS)
    assert is_running(left_behind)


# Linux: BusyBox `ps` rejects `-x`, so the command lines come from `/proc/<pid>/cmdline`.


def fake_proc(root: Path, commands: dict[str, list[str]]) -> Path:
    """A `/proc` with one `cmdline` (NUL-terminated arguments) per entry, and files that are no
    process."""
    for name, arguments in commands.items():
        entry = root / name
        entry.mkdir(parents=True)
        (entry / "cmdline").write_bytes("".join(f"{argument}\0" for argument in arguments).encode())
    (root / "cpuinfo").write_text("not a process")
    return root


def test_the_proc_files_say_which_processes_started_from_the_directory(tmp_path):
    scratch = tmp_path / "scratch"
    proc = fake_proc(
        tmp_path / "proc",
        {
            "101": [f"{scratch}/cs-runner", "--flag"],
            "102": ["/usr/bin/python3", f"{scratch}/log.txt"],
            "103": [f"{scratch}2/cs-runner"],
            "104": [f"{scratch}/other-runner"],
        },
    )
    assert sorted(_started_from(scratch, proc)) == [101, 104]


def test_a_proc_command_in_a_directory_with_a_space_is_matched(tmp_path):
    scratch = tmp_path / "my workspace" / "scratch"
    proc = fake_proc(tmp_path / "proc", {"7": [f"{scratch}/cs-runner", "-c", "x"]})
    assert _started_from(scratch, proc) == [7]


def test_a_proc_entry_without_a_command_line_is_skipped(tmp_path):
    """A kernel thread or a zombie has an empty `cmdline`; one that exited meanwhile has none."""
    proc = fake_proc(tmp_path / "proc", {"5": [], "6": ["/bin/sleep"]})
    (proc / "9").mkdir()
    assert _started_from(tmp_path / "scratch", proc) == []


def test_a_machine_without_proc_asks_ps(monkeypatch, tmp_path):
    scratch = tmp_path / "scratch"
    listing = subprocess.CompletedProcess(
        [], 0, f"  42 {scratch}/cs-runner -c x\n  43 /bin/sleep\n"
    )
    monkeypatch.setattr(debug_process.subprocess, "run", lambda *_a, **_k: listing)
    assert _started_from(scratch, tmp_path / "no-proc") == [42]
