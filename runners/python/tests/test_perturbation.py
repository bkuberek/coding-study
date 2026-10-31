"""Scheduler yields of the threads model (docs/specs/runners.md#perturbation)."""

import time

from cs_runner.perturbation import SWITCH_INTERVAL_SECONDS, scheduler_yields


def test_a_scheduler_yield_lasts_one_switch_interval():
    started = time.perf_counter()
    scheduler_yields(1)
    assert time.perf_counter() - started >= SWITCH_INTERVAL_SECONDS
