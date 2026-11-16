import errno
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from coding_study.adapters import busy_binary
from coding_study.adapters.busy_binary import MAX_ATTEMPTS, start_when_not_busy
from coding_study.adapters.languages.bounded_process import BoundedProcess
from coding_study.adapters.languages.rust import project_suite
from coding_study.domain.errors import RunnerStartError


def busy() -> OSError:
    return OSError(errno.ETXTBSY, "Text file busy")


@pytest.fixture
def sleeps(monkeypatch) -> list[float]:
    waited: list[float] = []
    monkeypatch.setattr(busy_binary.time, "sleep", waited.append)
    return waited


def failing(errors: list[OSError], result: str = "started"):
    attempts: list[int] = []

    def start() -> str:
        attempts.append(1)
        if errors:
            raise errors.pop(0)
        return result

    return start, attempts


def test_a_busy_binary_is_started_once_it_is_free(sleeps):
    start, attempts = failing([busy(), busy()])
    assert start_when_not_busy(start) == "started"
    assert (len(attempts), sleeps) == (3, [0.01, 0.02])


def test_a_binary_that_stays_busy_fails_after_the_last_attempt(sleeps):
    start, attempts = failing([busy()] * 20)
    with pytest.raises(OSError, match="Text file busy") as raised:
        start_when_not_busy(start)
    assert raised.value.errno == errno.ETXTBSY
    assert len(attempts) == MAX_ATTEMPTS
    assert len(sleeps) == MAX_ATTEMPTS - 1
    assert max(sleeps) == busy_binary.MAX_DELAY_SECONDS
    assert 1.5 < sum(sleeps) < 2.5


def test_any_other_error_is_raised_at_once(sleeps):
    start, attempts = failing([OSError(errno.ENOENT, "No such file or directory")])
    with pytest.raises(FileNotFoundError):
        start_when_not_busy(start)
    assert (len(attempts), sleeps) == (1, [])


def test_the_runner_start_retries_a_busy_binary(monkeypatch, sleeps):
    started = []
    real = subprocess.Popen

    def popen(command, **options):
        started.append(command)
        if len(started) < 3:
            raise busy()
        return real(command, **options)

    monkeypatch.setattr(subprocess, "Popen", popen)
    completed = BoundedProcess("build", 10).run([sys.executable, "--version"], Path.cwd(), None)
    assert (completed.returncode, len(started)) == (0, 3)


def test_a_rust_test_binary_that_stays_busy_is_a_start_error(monkeypatch, sleeps):
    calls = []

    def popen(command, **options):
        calls.append(command)
        raise busy()

    monkeypatch.setattr(subprocess, "Popen", popen)
    with pytest.raises(RunnerStartError, match="Text file busy"):
        project_suite._start(
            ["./tests"], Path.cwd(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    assert len(calls) == MAX_ATTEMPTS


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="ETXTBSY is how Linux refuses")
def test_a_binary_held_open_by_a_forked_child_starts_once_the_child_has_executed(tmp_path):
    binary = tmp_path / "python-copy"
    shutil.copyfile(sys.executable, binary)
    binary.chmod(0o755)
    forked, announce = os.pipe()

    def hold_until_exec() -> None:
        os.write(announce, b"x")
        time.sleep(0.5)

    holder = threading.Thread(
        target=subprocess.run,
        args=([sys.executable, "--version"],),
        kwargs={"preexec_fn": hold_until_exec, "pass_fds": (announce,), "capture_output": True},
    )
    with binary.open("r+b"):
        holder.start()
        assert os.read(forked, 1) == b"x"
    os.close(forked)
    os.close(announce)
    # the forked child still holds the copy's write descriptor: executing it fails until it execs
    with pytest.raises(OSError, match="Text file busy") as direct:
        subprocess.run([str(binary), "--version"], capture_output=True)
    assert direct.value.errno == errno.ETXTBSY
    process = start_when_not_busy(
        lambda: subprocess.Popen([str(binary), "--version"], stdout=subprocess.PIPE)
    )
    output, _ = process.communicate()
    assert (process.returncode, output.startswith(b"Python")) == (0, True)
    holder.join()
