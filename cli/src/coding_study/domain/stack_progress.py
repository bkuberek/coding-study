"""Where a service project's stack stands, as its progress notices tell it
(docs/specs/cli.md#event-stream).

A notice that moves the stack along names its stage. A terminal prints it as any other notice, and
`--events` adds the stage to its `output` event, so the Web UI shows the stack's state without
reading the words.
"""

from enum import StrEnum
from typing import Self

STARTING_TEXT = "starting the stack"
FAILED_TEXT = "the stack did not become ready"
STOPPED_TEXT = "the stack is down"


class StackStage(StrEnum):
    DOCKER = "docker"
    """Docker's engine was not running, and is starting."""
    PULLING = "pulling"
    INSTALLING = "installing"
    STARTING = "starting"
    READY = "ready"
    FAILED = "failed"
    STOPPED = "stopped"
    """Down, with nothing left behind: after a run, a failure or a cancel."""


class StackNotice(str):
    """A progress notice that names the stack's stage; it prints as its text."""

    stage: StackStage
    startup_s: float | None
    """Set on `ready`: the first clock, which no limit or result counts."""

    def __new__(cls, text: str, stage: StackStage, startup_s: float | None = None) -> Self:
        notice = super().__new__(cls, text)
        notice.stage = stage
        notice.startup_s = startup_s
        return notice


def stage_of(notice: str) -> StackStage | None:
    return notice.stage if isinstance(notice, StackNotice) else None


def ready_notice(startup_s: float) -> StackNotice:
    return StackNotice(
        f"the stack is ready after {startup_s:.1f} s, not counted", StackStage.READY, startup_s
    )
