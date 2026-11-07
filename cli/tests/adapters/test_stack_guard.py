"""The guard that takes a stack down when `cstudy` dies, with a stand-in for `docker`."""

import os
import signal
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

from coding_study.adapters.stack_guard import StackGuard, one_off_filters
from coding_study.domain.sandbox import LABEL_KIND, LABEL_PROJECT
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


def wait_for_down(path: Path) -> str:
    """The `down` the stand-in heard, the last thing a guard runs on Docker."""
    deadline = time.monotonic() + GENEROUS_WAIT_S
    while time.monotonic() < deadline:
        if path.exists() and " down" in path.read_text():
            return path.read_text().splitlines()[-1]
        time.sleep(POLL_S)
    raise AssertionError(f"no down written to {path}")


def test_releasing_the_guard_takes_nothing_down(docker_log):
    guard = StackGuard("s", removes_volumes=True, environment=environment_for(docker_log))

    guard.release()

    assert not docker_log.exists()


def test_a_guard_whose_owner_is_gone_takes_a_test_stack_down_with_its_volumes(docker_log):
    guard = StackGuard(
        "cstudy-t-1-a", removes_volumes=True, environment=environment_for(docker_log)
    )

    guard._pipe.close()

    assert wait_for_down(docker_log) == "compose -p cstudy-t-1-a down -v"
    guard._process.wait()


def test_a_guard_keeps_a_dev_stacks_volume(docker_log):
    guard = StackGuard("cstudy-d-r", removes_volumes=False, environment=environment_for(docker_log))

    guard._pipe.close()

    assert wait_for_down(docker_log) == "compose -p cstudy-d-r down"
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
    assert docker_log.read_text().splitlines()[-1] == "compose -p s down -v"


def answering_ps_with(docker_log: Path, found: str) -> None:
    """The stand-in `docker` answers `docker ps` with `found`."""
    script = docker_log.parent / "bin" / "docker"
    script.write_text(script.read_text() + f'[ "$1" = ps ] && echo "{found}"\nexit 0\n')


def test_a_guard_removes_a_stacks_one_offs_before_its_down(docker_log):
    """`down` leaves a one-off whose client died, and with it the network."""
    answering_ps_with(docker_log, "abc123")
    guard = StackGuard("s", removes_volumes=True, environment=environment_for(docker_log))

    guard._pipe.close()
    guard._process.wait(GENEROUS_WAIT_S)

    assert docker_log.read_text().splitlines() == [
        "ps -aq " + " ".join(one_off_filters("s")),
        "rm -f -v abc123",
        "compose -p s down -v",
    ]


def test_a_guard_with_no_one_off_to_remove_removes_none(docker_log):
    guard = StackGuard("s", removes_volumes=True, environment=environment_for(docker_log))

    guard._pipe.close()
    guard._process.wait(GENEROUS_WAIT_S)

    assert not [line for line in docker_log.read_text().splitlines() if line.startswith("rm")]


def test_a_guard_runs_docker_outside_the_folder_you_ran_cstudy_in(
    docker_log, tmp_path, monkeypatch
):
    """Compose reads `.env` from its current folder when `-f` is absent, as in a guard's `down`."""
    answer = tmp_path / "where"
    script = docker_log.parent / "bin" / "docker"
    script.write_text(f'#!/bin/sh\npwd > "{answer}"\necho "$@" >> "{docker_log}"\n')
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    guard = StackGuard("s", removes_volumes=True, environment=environment_for(docker_log))

    guard._pipe.close()
    guard._process.wait(GENEROUS_WAIT_S)

    assert Path(answer.read_text().strip()).resolve() != elsewhere.resolve()


def test_one_offs_are_found_by_cstudys_labels():
    filters = one_off_filters("s")

    assert f"label={LABEL_PROJECT}=s" in filters
    assert f"label={LABEL_KIND}" in filters


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

    assert wait_for_down(docker_log) == "compose -p killed down -v"
