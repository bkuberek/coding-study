"""The guard that takes a stack down when `cstudy` dies, with a stand-in for `docker`."""

import os
import signal
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

from coding_study.adapters.stack_guard import StackGuard
from tests.waits import GENEROUS_WAIT_S, POLL_S


@pytest.fixture
def docker_log(tmp_path: Path) -> Path:
    """Where a stand-in `docker` on `PATH` writes the arguments of each call."""
    log = tmp_path / "docker.log"
    bin_directory = tmp_path / "bin"
    bin_directory.mkdir()
    script = bin_directory / "docker"
    script.write_text(f'#!/bin/sh\necho "$@" >> "{log}"\n')
    script.chmod(0o755)
    return log


def environment_for(docker_log: Path) -> dict[str, str]:
    return {"PATH": f"{docker_log.parent / 'bin'}:{os.environ['PATH']}"}


def wait_for_text(path: Path) -> str:
    deadline = time.monotonic() + GENEROUS_WAIT_S
    while time.monotonic() < deadline:
        if path.exists() and path.read_text().strip():
            return path.read_text()
        time.sleep(POLL_S)
    raise AssertionError(f"nothing written to {path}")


def test_releasing_the_guard_takes_nothing_down(docker_log):
    guard = StackGuard("s", removes_volumes=True, environment=environment_for(docker_log))

    guard.release()

    assert not docker_log.exists()


def test_a_guard_whose_owner_is_gone_takes_a_test_stack_down_with_its_volumes(docker_log):
    guard = StackGuard(
        "cstudy-t-1-a", removes_volumes=True, environment=environment_for(docker_log)
    )

    guard._pipe.close()

    assert wait_for_text(docker_log) == "compose -p cstudy-t-1-a down -v\n"
    guard._process.wait()


def test_a_guard_keeps_a_dev_stacks_volume(docker_log):
    guard = StackGuard("cstudy-d-r", removes_volumes=False, environment=environment_for(docker_log))

    guard._pipe.close()

    assert wait_for_text(docker_log) == "compose -p cstudy-d-r down\n"
    guard._process.wait()


def test_a_guard_removes_the_runs_folder_after_the_down(docker_log, tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    (run / "stack.yaml").write_text("{}")
    guard = StackGuard(
        "s", removes_volumes=True, environment=environment_for(docker_log), run_directory=run
    )

    guard._pipe.close()
    guard._process.wait(GENEROUS_WAIT_S)

    assert not run.exists()
    assert docker_log.read_text() == "compose -p s down -v\n"


def test_a_guard_released_leaves_the_runs_folder(docker_log, tmp_path):
    run = tmp_path / "run"
    run.mkdir()
    guard = StackGuard(
        "s", removes_volumes=True, environment=environment_for(docker_log), run_directory=run
    )

    guard.release()

    assert run.exists()


def test_a_killed_owner_sets_the_guard_off(docker_log):
    """The whole point: SIGKILL gives `cstudy` no chance to clean up."""
    source = Path(__file__).parents[2] / "src"
    owner = subprocess.Popen(
        [
            sys.executable,
            "-c",
            textwrap.dedent(
                """\
                import sys, time
                from coding_study.adapters.stack_guard import StackGuard
                environment = {"PATH": sys.argv[1]}
                guard = StackGuard("killed", removes_volumes=True, environment=environment)
                print("ready", flush=True)
                time.sleep(600)
                """
            ),
            environment_for(docker_log)["PATH"],
        ],
        stdout=subprocess.PIPE,
        text=True,
        env={**os.environ, "PYTHONPATH": str(source)},
    )
    assert owner.stdout is not None
    assert owner.stdout.readline().strip() == "ready"

    os.kill(owner.pid, signal.SIGKILL)
    owner.wait()

    assert wait_for_text(docker_log) == "compose -p killed down -v\n"
