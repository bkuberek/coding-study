"""The Rust runner's start, which a busy machine can slow past the 5 s a learner's run allows it to
say hello."""

import pytest

from coding_study.domain.problem import Language
from coding_study.domain.runs import HELLO_TIMEOUT_MS
from tests.waits import GENEROUS_WAIT_S

MILLISECONDS_PER_SECOND = 1000


@pytest.fixture(autouse=True)
def generous_runner_start(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every Rust runner a test starts gets the generous wait to say hello: how long a binary
    takes to start on a loaded machine is a wait, never the budget a test is about."""
    generous_ms = int(GENEROUS_WAIT_S * MILLISECONDS_PER_SECOND)
    monkeypatch.setitem(HELLO_TIMEOUT_MS, Language.RUST, generous_ms)
