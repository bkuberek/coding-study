"""docs/specs/runners.md#invocation: `cstudy` processes share `.cs/runs/`, and none removes the
run of a process that is still alive."""

import os
import re
from collections.abc import Iterator
from pathlib import Path

import pytest

from coding_study.adapters.run_directories import (
    ABANDONED_AFTER_SECONDS,
    KEPT_RUNS,
    RunDirectories,
)
from tests.run_folders import DAY_SECONDS, ended_pid, run_folder, running_process

OWN_PID = 4242
"""Not a running process: what a process keeps of its own runs does not depend on it."""


@pytest.fixture
def runs(tmp_path: Path) -> Path:
    return tmp_path / "runs"


@pytest.fixture
def other_pid() -> Iterator[int]:
    """Another `cstudy`, running."""
    with running_process() as pid:
        yield pid


def directories(runs: Path, pid: int = OWN_PID) -> RunDirectories:
    return RunDirectories(runs, owner=lambda: pid)


def names(runs: Path) -> set[str]:
    return {path.name for path in runs.iterdir()}


def test_names_a_run_for_the_process_that_makes_it(runs):
    created = RunDirectories(runs).create()
    assert re.fullmatch(rf"\d{{8}}-\d{{6}}-\d{{6}}-p{os.getpid()}-[a-z0-9_]{{8}}", created.name)
    assert created.is_dir()


def test_keeps_the_newest_runs_of_its_own(runs):
    created = [directories(runs).create() for _ in range(KEPT_RUNS + 5)]
    assert names(runs) == {path.name for path in created[-KEPT_RUNS:]}


def test_another_process_making_many_runs_leaves_a_live_run_alone(runs, other_pid):
    first = directories(runs, other_pid)
    second = directories(runs)
    long_run = first.create()
    (long_run / "request-5.json").write_text("{}")
    for _ in range(KEPT_RUNS + 10):
        second.create()
    assert (long_run / "request-5.json").is_file()
    assert len(names(runs)) == KEPT_RUNS + 1


def test_removes_the_runs_of_a_process_that_ended(runs):
    ended = run_folder(runs, ended_pid())
    directories(runs).sweep()
    assert not ended.exists()


def test_removes_the_runs_of_a_process_that_ended_whatever_their_age(runs):
    fresh = run_folder(runs, ended_pid(), number=1, age_seconds=0)
    old = run_folder(runs, ended_pid(), number=2, age_seconds=3 * DAY_SECONDS)
    directories(runs).sweep()
    assert not fresh.exists()
    assert not old.exists()


def test_removes_a_run_of_a_live_process_after_a_day(runs, other_pid):
    """The pid may belong to another process by now."""
    abandoned = run_folder(runs, other_pid, number=1, age_seconds=ABANDONED_AFTER_SECONDS + 60)
    recent = run_folder(runs, other_pid, number=2, age_seconds=ABANDONED_AFTER_SECONDS - 3600)
    directories(runs).sweep()
    assert not abandoned.exists()
    assert recent.is_dir()


def test_keeps_the_runs_of_a_live_process_however_many_there_are(runs, other_pid):
    kept = [run_folder(runs, other_pid, number=index) for index in range(KEPT_RUNS + 5)]
    directories(runs).sweep()
    assert all(path.is_dir() for path in kept)


def test_removes_a_run_without_a_pid_only_after_a_day(runs):
    """The form of an earlier release: nobody to ask whether it is still running."""
    recent = run_folder(runs, None, number=1, age_seconds=60)
    abandoned = run_folder(runs, None, number=2, age_seconds=ABANDONED_AFTER_SECONDS + 60)
    directories(runs).sweep()
    assert recent.is_dir()
    assert not abandoned.exists()


def test_does_not_count_the_runs_of_other_processes_against_its_own(runs, other_pid):
    own = [run_folder(runs, OWN_PID, number=index) for index in range(KEPT_RUNS)]
    theirs = [run_folder(runs, other_pid, number=100 + index) for index in range(5)]
    directories(runs).sweep()
    assert all(path.is_dir() for path in own + theirs)


def test_leaves_what_is_not_a_run_folder_alone(runs, tmp_path):
    runs.mkdir()
    old = 3 * DAY_SECONDS
    stack = run_folder(runs, None, age_seconds=old).rename(runs / "cstudy-g-123-abcdef")
    numbered = run_folder(runs, None, number=1, age_seconds=old).rename(runs / "00000000-000001")
    beyond_a_pid = run_folder(runs, None, number=2, age_seconds=old).rename(
        runs / "20200101-000000-000002-p99999999999-abcd1234"
    )
    file = runs / "20200101-000000-000003-abcd1234"
    file.write_text("not a folder")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    link = runs / f"20200101-000000-000004-p{ended_pid()}-abcd1234"
    link.symlink_to(elsewhere, target_is_directory=True)
    directories(runs).sweep()
    for path in (stack, numbered, beyond_a_pid, file, elsewhere):
        assert path.exists()
    assert link.is_symlink()
