"""Notifications through a real `cstudy serve` (docs/specs/web-ui.md#notifications): a file of the
project pilot edited on disk, as an editor or the terminal would, reaches the notification stream as
`file_changed` with the file's SHA-256; an attempt started in the terminal reaches it as
`progress_changed`; and Ctrl-C stops the server while that stream is open, which ends the stream."""

import hashlib
import queue
import signal
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

import httpx2
import pytest

from tests.scripted_runs import Frame, read_frames
from tests.serve_process import RunningServer, running_server, served_environment
from tests.workspaces import workspace_like

pytestmark = pytest.mark.slow

PROJECT = "bank-project-python"
EDITED = "bank/bank.py"
COMMAND_SECONDS = 120
WAIT_SECONDS = 60
"""Generous: the machine running the slow tests is often loaded."""
RETRY_SECONDS = 2.0
"""How long one edit waits for its notice before the next edit, while the server's watch starts."""
STOP_SECONDS = 15
ENDED = None


def cstudy(workspace: Path, *arguments: str) -> None:
    subprocess.run(
        [sys.executable, "-m", "coding_study", *arguments],
        env=served_environment(workspace),
        cwd=workspace,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=True,
        timeout=COMMAND_SECONDS,
    )


@dataclass
class Stream:
    """A notification stream read in a thread of its own: each frame, then ENDED."""

    frames: "queue.Queue[Frame | None]" = field(default_factory=queue.Queue)

    def read(self, server: RunningServer) -> None:
        client = httpx2.Client(base_url=server.address, timeout=None)
        client.get(server.login_url)
        with client.stream("GET", "/api/v1/events") as response:
            for frame in read_frames(response.iter_lines()):
                self.frames.put(frame)
        self.frames.put(ENDED)

    def next_matching(self, matches: Callable[[Frame], bool], seconds: float) -> Frame | None:
        """The first frame that matches within `seconds`, skipping the others; None if none."""
        deadline = time.monotonic() + seconds
        while (left := deadline - time.monotonic()) > 0:
            try:
                frame = self.frames.get(timeout=left)
            except queue.Empty:
                return None
            if frame is None or matches(frame):
                return frame
        return None


@dataclass
class Seen:
    file_changed: Frame | None = None
    edited_sha256: str = ""
    progress_changed: Frame | None = None
    exit_code: int = 0
    stop_seconds: float = 0.0
    stream_ended: bool = False


@pytest.fixture(scope="module")
def workspace(practice_workspace: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = workspace_like(practice_workspace, tmp_path_factory.mktemp("notify") / "workspace")
    cstudy(root, "start", PROJECT, "--no-open")
    return root


@pytest.fixture(scope="module")
def seen(workspace: Path) -> Seen:
    found = Seen()
    edited = workspace / "projects" / PROJECT / EDITED
    with running_server(workspace) as server:
        stream = Stream()
        threading.Thread(target=stream.read, args=(server,), daemon=True).start()
        found.file_changed, found.edited_sha256 = _edit_until_notified(edited, stream)
        cstudy(workspace, "start", "two-sum", "--lang", "python", "--no-open")
        found.progress_changed = stream.next_matching(_named("progress_changed"), WAIT_SECONDS)
        started = time.monotonic()
        found.exit_code, _lines = server.stop(signal.SIGINT)
        found.stop_seconds = time.monotonic() - started
        found.stream_ended = stream.next_matching(lambda _frame: False, STOP_SECONDS) is ENDED
    return found


def _edit_until_notified(edited: Path, stream: Stream) -> tuple[Frame | None, str]:
    """Edits the file until its notice comes, since the server's watch may still be starting;
    the notice and the SHA-256 of the last edit."""
    deadline = time.monotonic() + WAIT_SECONDS
    original = edited.read_text()
    sha256 = ""
    for edit in range(1, sys.maxsize):
        text = f"{original}\n# edited on disk {edit}\n"
        edited.write_text(text)
        sha256 = hashlib.sha256(text.encode()).hexdigest()
        frame = stream.next_matching(_file_notice(sha256), RETRY_SECONDS)
        if frame is not None or time.monotonic() > deadline:
            return frame, sha256
    return None, sha256


def _named(event: str) -> Callable[[Frame], bool]:
    return lambda frame: frame.event == event


def _file_notice(sha256: str) -> Callable[[Frame], bool]:
    return lambda frame: frame.event == "file_changed" and frame.data["sha256"] == sha256


def test_a_file_edited_on_disk_reaches_the_stream(seen):
    assert seen.file_changed is not None


def test_the_notice_names_the_file_by_its_path_in_the_project(seen):
    assert seen.file_changed is not None
    assert seen.file_changed.data["path"] == EDITED


def test_an_attempt_started_in_the_terminal_reaches_the_stream_as_a_progress_change(seen):
    assert seen.progress_changed is not None


def test_ctrl_c_stops_the_server_with_a_notification_stream_open(seen):
    assert (seen.exit_code, seen.stop_seconds < STOP_SECONDS) == (130, True)


def test_ctrl_c_ends_the_notification_stream(seen):
    assert seen.stream_ended
