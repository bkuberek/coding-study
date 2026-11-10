"""The runners these tests start, whose start a busy machine can slow past the few seconds a
learner's run allows them to say hello."""

from collections.abc import Iterator

import pytest

from coding_study.domain.runs import HELLO_TIMEOUT_MS
from tests.waits import GENEROUS_WAIT_S

MILLISECONDS_PER_SECOND = 1000


@pytest.fixture(scope="module", autouse=True)
def generous_runner_start() -> Iterator[None]:
    """Every language's hello timeout gets the generous wait on top, for the whole module, so a
    runner that a module-scoped fixture starts gets it too: how long a process takes to start on
    a loaded machine is a wait, never the budget a test is about. Adding the same wait to each
    keeps the languages' timeouts as far apart as they are, so a test that a launch takes its
    own language's timeout still tells them apart."""
    generous_ms = int(GENEROUS_WAIT_S * MILLISECONDS_PER_SECOND)
    with pytest.MonkeyPatch.context() as patch:
        for language, timeout_ms in tuple(HELLO_TIMEOUT_MS.items()):
            patch.setitem(HELLO_TIMEOUT_MS, language, timeout_ms + generous_ms)
        yield
