import os
import signal
import subprocess
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest

from coding_study.adapters import process_liveness
from coding_study.adapters.process_liveness import (
    OrphanGuard,
    _is_zombie,
    _started_from,
    is_alive,
    kill_processes_started_from,
)
from tests.process_table import (
    DyingCstudy,
    Process,
    kill_all,
    left_running,
    running_processes,
)

GRACE_SECONDS = 0.1
"""Short: a killed child of this test stays a zombie until the test waits for it."""
ENDED_BY_KILL = -signal.SIGKILL
SLEEP_FOR_A_MINUTE = "import time; time.sleep(60)"
GRACE_PERIOD_TO_SKIP_SECONDS = 5.0


# Processes left behind by a debug server that let go of its runner.


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

    monkeypatch.setattr(process_liveness.subprocess, "run", missing_ps)
    monkeypatch.setattr(process_liveness, "PROC_ROOT", tmp_path / "no-proc")
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
    monkeypatch.setattr(process_liveness.subprocess, "run", lambda *_a, **_k: listing)
    assert _started_from(scratch, tmp_path / "no-proc") == [42]


# The guard, which outlives a `cstudy` killed with SIGKILL.


@dataclass(frozen=True, slots=True)
class Guarded:
    """What tests/fixtures/dying_cstudy.py started under its guard, and what of it all, the guard
    included, still ran a moment after it was killed."""

    leader: int
    member: int
    from_scratch: int
    left: list[Process]


@pytest.fixture
def guarded(tmp_path: Path) -> Iterator[Guarded]:
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    cstudy = DyingCstudy("guard", scratch)
    _, leader, member, from_scratch = cstudy.said()
    left = left_running(cstudy.kill(), [scratch])
    yield Guarded(int(leader), int(member), int(from_scratch), left)
    kill_all(left)


def test_the_leader_of_a_watched_group_is_killed_when_cstudy_dies(guarded):
    assert not process_liveness.is_alive(guarded.leader)


def test_every_member_of_a_watched_group_is_killed_when_cstudy_dies(guarded):
    assert not process_liveness.is_alive(guarded.member)


def test_a_process_started_from_the_guarded_directory_is_killed_when_cstudy_dies(guarded):
    """A debug server's runner, in a group of its own."""
    assert not process_liveness.is_alive(guarded.from_scratch)


def test_the_guard_ends_too_when_cstudy_dies(guarded):
    assert guarded.left == []


@pytest.fixture
def sleeper() -> Iterator[subprocess.Popen[bytes]]:
    """A process leading a group of its own, as a runner does."""
    process = subprocess.Popen([sys.executable, "-c", SLEEP_FOR_A_MINUTE], start_new_session=True)
    yield process
    process.kill()
    process.wait()


def test_a_guard_leaves_its_group_alone_while_cstudy_lives(sleeper):
    with OrphanGuard() as guard:
        guard.watch(sleeper.pid)
        time.sleep(GRACE_SECONDS)
        assert is_running(sleeper)


def test_a_released_guard_leaves_its_group_alone(sleeper):
    with OrphanGuard() as guard:
        guard.watch(sleeper.pid)
    assert is_running(sleeper)


def test_watching_with_a_guard_someone_killed_is_no_error(sleeper):
    with OrphanGuard() as guard:
        (killed,) = (
            process
            for process in running_processes()
            if process.parent == os.getpid() and process_liveness.__file__ in process.command
        )
        os.kill(killed.pid, signal.SIGKILL)
        time.sleep(GRACE_SECONDS)
        guard.watch(sleeper.pid)


# A zombie is dead: nothing but its parent can still reap it.


def a_zombie(processes: list[subprocess.Popen[bytes]]) -> subprocess.Popen[bytes]:
    """A child that exited and that nobody waited for, which stays in the process table."""
    child = subprocess.Popen([sys.executable, "-c", "pass"], stdout=subprocess.PIPE)
    processes.append(child)
    assert child.stdout is not None
    child.stdout.read()
    time.sleep(0.1)
    return child


def test_a_zombie_is_not_alive(started):
    assert not is_alive(a_zombie(started).pid)


def test_a_running_process_is_alive(tmp_path, started):
    assert is_alive(start_in(tmp_path / "scratch", started).pid)


def test_a_process_that_is_gone_is_not_alive(started):
    child = a_zombie(started)
    child.wait()
    assert not is_alive(child.pid)


def test_the_cleanup_does_not_wait_the_grace_period_for_the_zombies_it_makes(tmp_path, started):
    """The test is the parent of what it kills, so the victim stays a zombie."""
    start_in(tmp_path / "scratch", started)
    begun = time.monotonic()
    kill_processes_started_from(tmp_path / "scratch", GRACE_PERIOD_TO_SKIP_SECONDS)
    assert time.monotonic() - begun < GRACE_PERIOD_TO_SKIP_SECONDS / 2


# Linux: the state is the first field after the command name in `/proc/<pid>/stat`.


def fake_stat(root: Path, pid: int, stat: str) -> Path:
    entry = root / str(pid)
    entry.mkdir(parents=True)
    (entry / "stat").write_text(stat)
    return root


def test_the_proc_state_z_is_a_zombie(tmp_path):
    proc = fake_stat(tmp_path / "proc", 5, "5 (python3) Z 1 5 5 0 -1 4228")
    assert _is_zombie(5, proc)


def test_the_proc_state_s_is_no_zombie(tmp_path):
    proc = fake_stat(tmp_path / "proc", 5, "5 (python3) S 1 5 5 0 -1 4228")
    assert not _is_zombie(5, proc)


def test_a_command_name_with_spaces_and_parentheses_does_not_hide_the_state(tmp_path):
    """The name can be `a) Z (b`; the state follows the last parenthesis."""
    proc = fake_stat(tmp_path / "proc", 5, "5 (a) Z (b) S 1 5 5 0 -1 4228")
    assert not _is_zombie(5, proc)


def test_a_process_with_no_proc_entry_is_no_zombie(tmp_path):
    (tmp_path / "proc").mkdir()
    assert not _is_zombie(5, tmp_path / "proc")
