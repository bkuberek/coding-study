"""What else hears the workspace's file changes besides the tabs' streams
(docs/specs/web-ui.md#notifications): a code-intelligence session passes them to its language
server, so a listener hears each one with the root and whether the file is new."""

import asyncio

import pytest

from coding_study.application.attempt_changes import AttemptChanged, FileChanged, ProgressChanged
from coding_study.entrypoints.web.notifications import Notifications

SAVED = FileChanged(3, "bank/bank.py", "ab", "projects/bank-project-python")
CREATED = FileChanged(3, "bank/ledger.py", "cd", "projects/bank-project-python", created=True)


def test_a_listener_hears_each_file_change_in_order():
    heard: list[FileChanged] = []
    hub = Notifications()
    hub.on_file_changed(heard.append)
    hub.notice(SAVED)
    hub.notice(CREATED)
    assert heard == [SAVED, CREATED]


@pytest.mark.parametrize("change", [AttemptChanged(3, "bank-project-python"), ProgressChanged()])
def test_a_listener_hears_nothing_else(change):
    heard: list[FileChanged] = []
    hub = Notifications()
    hub.on_file_changed(heard.append)

    async def notice() -> None:
        hub.notice(change)

    asyncio.run(notice())
    assert heard == []


def test_every_listener_hears_it():
    first: list[FileChanged] = []
    second: list[FileChanged] = []
    hub = Notifications()
    hub.on_file_changed(first.append)
    hub.on_file_changed(second.append)
    hub.notice(SAVED)
    assert (first, second) == ([SAVED], [SAVED])


def test_a_listener_that_stopped_listening_hears_no_more():
    heard: list[FileChanged] = []
    hub = Notifications()
    stop = hub.on_file_changed(heard.append)
    hub.notice(SAVED)
    stop()
    stop()
    hub.notice(CREATED)
    assert heard == [SAVED]


def test_a_listener_that_fails_neither_stops_the_others_nor_the_stream(capsys):
    heard: list[FileChanged] = []

    def failing(_change: FileChanged) -> None:
        raise RuntimeError("boom")

    hub = Notifications()
    hub.on_file_changed(failing)
    hub.on_file_changed(heard.append)
    hub.notice(SAVED)
    assert (heard, "boom" in capsys.readouterr().err) == ([SAVED], True)


def test_the_notice_is_still_published_to_the_streams():
    hub = Notifications()
    hub.on_file_changed(lambda _change: None)
    hub.notice(SAVED)

    async def first() -> str:
        return await asyncio.wait_for(anext(hub.frames(-1)), 5)

    frame = asyncio.run(first())
    assert ("event: file_changed" in frame, '"path": "bank/bank.py"' in frame) == (True, True)


def test_a_stopped_hub_tells_no_listener():
    heard: list[FileChanged] = []
    hub = Notifications()
    hub.on_file_changed(heard.append)
    hub.stop()
    hub.notice(SAVED)
    assert heard == []
