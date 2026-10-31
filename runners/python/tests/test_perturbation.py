"""Scheduler yields of the threads model (docs/specs/runners.md#perturbation)."""

import os

from cs_runner.perturbation import scheduler_yields


def test_a_scheduler_yield_gives_up_the_cpu(monkeypatch):
    yields: list[None] = []
    monkeypatch.setattr(os, "sched_yield", lambda: yields.append(None))
    scheduler_yields(3)
    assert len(yields) == 3
