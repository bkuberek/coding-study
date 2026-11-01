"""Scheduler yields of the threads model (docs/specs/runners.md#perturbation)."""

import ctypes
import os
import random
import select
import sys
import threading
import time
from collections.abc import Callable

import pytest

from cs_runner.perturbation import SLEEP_INTERVAL_SECONDS, scheduler_yields, worker_thread
from cs_runner.request import Granularity, Perturbation

PR_GET_TIMERSLACK = 30
BEFORE_THE_INTERVAL = SLEEP_INTERVAL_SECONDS / 2


class _Calls:
    """Records the system calls a yield makes, on a clock that moves only when told to."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.made: list[str] = []
        self.now = 0.0
        monkeypatch.setattr(select, "select", self._select)
        monkeypatch.setattr(time, "sleep", lambda _seconds: self.made.append("sleep"))
        monkeypatch.setattr(os, "sched_yield", lambda: self.made.append("sched_yield"))
        monkeypatch.setattr(time, "perf_counter", lambda: self.now)

    def _select(self, *_args: object) -> tuple[list[object], list[object], list[object]]:
        self.made.append("release")
        return [], [], []


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> _Calls:
    return _Calls(monkeypatch)


def on_a_new_thread(action: Callable[[], None]) -> None:
    """Each test yields on a thread of its own, which has not slept yet."""
    thread = threading.Thread(target=action)
    thread.start()
    thread.join()


def test_a_threads_first_yield_sleeps(calls):
    on_a_new_thread(lambda: scheduler_yields(1))
    assert calls.made == ["sleep"]


def test_yields_within_the_sleep_interval_only_release_the_gil(calls):
    on_a_new_thread(lambda: scheduler_yields(3))
    assert calls.made == ["sleep", "release", "release"]


def test_a_yield_just_before_the_sleep_interval_ends_only_releases_the_gil(calls):
    def yields() -> None:
        scheduler_yields(1)
        calls.now += BEFORE_THE_INTERVAL
        scheduler_yields(1)

    on_a_new_thread(yields)
    assert calls.made == ["sleep", "release"]


def test_a_yield_sleeps_again_once_the_sleep_interval_passed(calls):
    def yields() -> None:
        scheduler_yields(1)
        calls.now += SLEEP_INTERVAL_SECONDS
        scheduler_yields(2)

    on_a_new_thread(yields)
    assert calls.made == ["sleep", "sleep", "release"]


def test_each_thread_keeps_its_own_sleep_interval(calls):
    on_a_new_thread(lambda: scheduler_yields(1))
    on_a_new_thread(lambda: scheduler_yields(1))
    assert calls.made == ["sleep", "sleep"]


@pytest.mark.skipif(sys.platform != "linux", reason="the timer slack is a Linux setting")
def test_a_linux_worker_sleeps_without_timer_slack():
    slack: list[int] = []

    def work() -> None:
        with worker_thread(random.Random(0), Perturbation(0.0, 1, Granularity.NONE)):
            slack.append(ctypes.CDLL(None).prctl(PR_GET_TIMERSLACK, 0, 0, 0, 0))

    on_a_new_thread(work)
    assert slack == [1]
