"""One test per outcome of a suite job, in the order the runner meets them: a pass, a hang that
the hang guard ends, an assertion failure, an exit that ends the runner, an exception and output.
After each hang or exit the suite restarts with the tests reported so far left out."""

import os

from probe.probe import Probe

EXIT_CODE = 3


def test_passes() -> None:
    assert Probe().ping() == "pong"


def test_hangs() -> None:
    while True:
        pass


def test_fails_an_assertion() -> None:
    assert Probe().ping() == "ping"


def test_ends_the_process() -> None:
    os._exit(EXIT_CODE)


def test_raises() -> None:
    raise RuntimeError("conformance failure")


def test_prints() -> None:
    print("conformance output")
