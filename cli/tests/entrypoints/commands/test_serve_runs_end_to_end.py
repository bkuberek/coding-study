"""Runs through a real `cstudy serve` and the real CLI (docs/specs/web-ui.md#runs): a test run of a
single-file problem, the project pilot's tests and its reference's submission, which opens level
2, a cancel that leaves no test process behind, and a server stopped while a run goes on.

The workspace shares the session's practice workspace's toolchains, so the pilot's suite runs
with the real pytest."""

import shutil
import signal
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from tests.helpers import CATALOG_PROBLEMS
from tests.scripted_runs import Frame, eventually, is_alive
from tests.serve_page import RUN_SECONDS, opened_page
from tests.serve_process import running_server, served_environment
from tests.workspaces import workspace_like

pytestmark = pytest.mark.slow

PROJECT = "bank-project-python"
REFERENCE = CATALOG_PROBLEMS / "0249-bank-project-python" / "solutions" / "reference"
SLOW_TEST_ID = "tests/test_slow.py::test_slow"
SLOW_TEST = """import os
import time
from pathlib import Path


def test_slow():
    Path({pid_file!r}).write_text(str(os.getpid()))
    time.sleep(120)
"""


def cstudy(workspace: Path, *arguments: str) -> None:
    subprocess.run(
        [sys.executable, "-m", "coding_study", *arguments],
        env=served_environment(workspace),
        cwd=workspace,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=True,
        timeout=RUN_SECONDS,
    )


@pytest.fixture(scope="module")
def workspace(practice_workspace: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = workspace_like(practice_workspace, tmp_path_factory.mktemp("runs") / "workspace")
    cstudy(root, "start", "two-sum", "--lang", "python", "--no-open")
    cstudy(root, "start", PROJECT, "--no-open")
    return root


def with_slow_test(workspace: Path) -> Path:
    """Adds a test that writes its process id to the file returned, then sleeps."""
    pid_file = workspace.parent / "slow-test.pid"
    pid_file.unlink(missing_ok=True)
    slow_test = workspace / "projects" / PROJECT / "tests" / "test_slow.py"
    slow_test.write_text(SLOW_TEST.format(pid_file=str(pid_file)))
    return pid_file


def without_slow_test(workspace: Path) -> None:
    (workspace / "projects" / PROJECT / "tests" / "test_slow.py").unlink(missing_ok=True)


@dataclass
class Played:
    streams: dict[str, list[Frame]] = field(default_factory=dict[str, list[Frame]])
    slow_test_pid: int = 0
    restarted: int = 0
    """The status of a run asked for right after the cancelled one closed."""
    printed: list[str] = field(default_factory=list[str])


@pytest.fixture(scope="module")
def played(workspace: Path) -> Played:
    seen = Played()
    with running_server(workspace) as server:
        page = opened_page(server)
        seen.streams["single file"] = page.played(page.started("two-sum"))
        seen.streams["project test"] = page.played(page.started(PROJECT))
        pid_file = with_slow_test(workspace)
        run_id = page.started(PROJECT)
        stream = page.stream(run_id)
        cancelled = [*_until_slow_test_starts(stream)]
        seen.slow_test_pid = int(eventually(lambda: _read(pid_file), bool))
        page.cancel(run_id)
        seen.streams["cancelled"] = [*cancelled, *stream]
        without_slow_test(workspace)
        restarted = page.start(PROJECT)
        seen.restarted = restarted.status_code
        page.played(restarted.json()["id"])
        shutil.copytree(REFERENCE, workspace / "projects" / PROJECT, dirs_exist_ok=True)
        seen.streams["reference submit"] = page.played(page.started(PROJECT, "submit"))
        page.client.close()
        _exit_code, seen.printed = server.stop(signal.SIGINT)
    return seen


def _until_slow_test_starts(stream: Iterator[Frame]) -> Iterator[Frame]:
    for frame in stream:
        yield frame
        if frame.event == "test_start" and frame.data["id"] == SLOW_TEST_ID:
            return


def _read(path: Path) -> str:
    return path.read_text() if path.exists() else ""


def names(frames: list[Frame]) -> list[str]:
    return [frame.event for frame in frames]


def of_type(frames: list[Frame], event_type: str) -> list[dict[str, object]]:
    return [frame.data for frame in frames if frame.event == event_type]


def test_a_single_file_run_streams_its_cases(played):
    events = names(played.streams["single file"])
    assert (events[0], "case_result" in events, events[-2:]) == (
        "run_start",
        True,
        ["run_end", "closed"],
    )


def test_a_single_file_run_closes_with_the_exit_code_of_its_run_end(played):
    frames = played.streams["single file"]
    (run_end,) = of_type(frames, "run_end")
    assert frames[-1].data["exit_code"] == run_end["exit_code"]


def test_a_project_run_streams_its_tests(played):
    events = names(played.streams["project test"])
    assert {"test_start", "test_result"} <= set(events)


def test_a_cancelled_run_ends_interrupted(played):
    (run_end,) = of_type(played.streams["cancelled"], "run_end")
    assert run_end["outcome"] == "interrupted"


def test_a_cancelled_run_closes_with_exit_130(played):
    closed = played.streams["cancelled"][-1]
    assert (closed.event, closed.data["exit_code"], closed.data["signal"]) == ("closed", 130, None)


def test_a_cancel_leaves_no_test_process_behind(played):
    assert not eventually(lambda: is_alive(played.slow_test_pid), lambda alive: not alive)


def test_a_run_asked_for_once_the_cancelled_one_closed_starts(played):
    assert played.restarted == 201


def test_the_references_submission_opens_level_2(played):
    (opened,) = of_type(played.streams["reference submit"], "level_unlocked")
    assert opened["level"] == 2


def test_the_server_printed_a_line_per_run(played):
    runs = [line.split(None, 1)[1] for line in played.printed if line.startswith("run ")]
    assert [line.split(" · ")[:2] for line in runs] == [
        ["test two-sum", "python"],
        ["test bank-project-python", "failed"],
        ["test bank-project-python", "interrupted"],
        ["test bank-project-python", "failed"],
        ["submit bank-project-python", "passed"],
    ]


def test_stopping_the_server_stops_its_runs(workspace):
    pid_file = with_slow_test(workspace)
    try:
        with running_server(workspace) as server:
            page = opened_page(server)
            stream = page.stream(page.started(PROJECT))
            _started = [*_until_slow_test_starts(stream)]
            pid = int(eventually(lambda: _read(pid_file), bool))
            exit_code, _lines = server.stop(signal.SIGINT)
            page.client.close()
    finally:
        without_slow_test(workspace)
    alive = eventually(lambda: is_alive(pid), lambda alive: not alive)
    assert (exit_code, alive) == (130, False)
