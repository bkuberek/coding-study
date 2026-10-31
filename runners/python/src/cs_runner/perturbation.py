"""Widening thread interleavings during stress runs (docs/specs/runners.md#perturbation).

Between ops, a worker yields with probability `yield_probability`, 1 to `max_yields` times. In the
threads model the runner also lowers the switch interval and, through `sys.monitoring`, yields
the same way before lines (or instructions) of the target file that worker threads execute. A
monitoring callback cannot await, so the async model only yields between ops.
"""

import os
import random
import sys
import threading
from collections.abc import Generator
from contextlib import contextmanager
from types import CodeType

from cs_runner.request import Granularity, Perturbation

SWITCH_INTERVAL_SECONDS = 1e-5
TOOL_ID = 3
TOOL_NAME = "cs-stress"

_worker = threading.local()
"""`rng` and `perturb` are set on worker threads only."""


def yield_count(rng: random.Random, perturb: Perturbation) -> int:
    """How many scheduler yields to make now: usually none."""
    if rng.random() >= perturb.yield_probability:
        return 0
    return 1 + rng.randrange(perturb.max_yields)


def scheduler_yields(count: int) -> None:
    """Each yield releases the GIL and gives up the CPU. On a busy machine the yielding worker
    waits for its next turn, and a worker waiting for the GIL takes it meanwhile; on an idle one
    nothing else is ready on that core, and the call returns at once.

    `time.sleep(0)` released the GIL without giving up the CPU: on a busy machine a waiting
    worker was not running during that one system call, and every release restarted its wait,
    so it never asked for the GIL. The yielding worker kept it and could finish its script
    alone, and a racy reference passed whole runs (docs/specs/runners.md#perturbation).
    """
    for _ in range(count):
        os.sched_yield()


@contextmanager
def worker_thread(rng: random.Random, perturb: Perturbation) -> Generator[None]:
    """Marks the current thread as a worker, so injected yields draw from its PRNG."""
    _worker.rng, _worker.perturb = rng, perturb
    try:
        yield
    finally:
        del _worker.rng, _worker.perturb


@contextmanager
def thread_perturbation(perturb: Perturbation, target_file: str) -> Generator[None]:
    """For the duration of one threads-model run: the switch interval and injected yields."""
    previous_interval = sys.getswitchinterval()
    sys.setswitchinterval(SWITCH_INTERVAL_SECONDS)
    event = _monitoring_event(perturb.granularity)
    if event is not None:
        _start_monitoring(event, target_file)
    try:
        yield
    finally:
        if event is not None:
            _stop_monitoring(event)
        sys.setswitchinterval(previous_interval)


def _monitoring_event(granularity: Granularity) -> int | None:
    events = sys.monitoring.events
    match granularity:
        case Granularity.LINE:
            return events.LINE
        case Granularity.INSTRUCTION:
            return events.INSTRUCTION
        case Granularity.NONE:
            return None


def _start_monitoring(event: int, target_file: str) -> None:
    monitoring = sys.monitoring

    def maybe_yield(code: CodeType, _location: int) -> object:
        if code.co_filename != target_file:
            return monitoring.DISABLE
        rng: random.Random | None = getattr(_worker, "rng", None)
        if rng is not None:
            scheduler_yields(yield_count(rng, _worker.perturb))
        return None

    monitoring.use_tool_id(TOOL_ID, TOOL_NAME)
    monitoring.register_callback(TOOL_ID, event, maybe_yield)
    monitoring.set_events(TOOL_ID, event)
    monitoring.restart_events()


def _stop_monitoring(event: int) -> None:
    monitoring = sys.monitoring
    monitoring.set_events(TOOL_ID, monitoring.events.NO_EVENTS)
    monitoring.register_callback(TOOL_ID, event, None)
    monitoring.free_tool_id(TOOL_ID)
