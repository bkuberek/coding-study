"""Widening thread interleavings during stress runs (docs/specs/runners.md#perturbation).

Between ops, a worker yields with probability `yield_probability`, 1 to `max_yields` times. In the
threads model the runner also lowers the switch interval and, through `sys.monitoring`, yields
the same way before lines (or instructions) of the target file that worker threads execute. A
monitoring callback cannot await, so the async model only yields between ops.
"""

import ctypes
import math
import random
import select
import sys
import threading
import time
from collections.abc import Generator
from contextlib import contextmanager
from types import CodeType

from cs_runner.request import Granularity, Perturbation

SWITCH_INTERVAL_SECONDS = 1e-5
SLEEP_INTERVAL_SECONDS = 1e-4
"""A thread's yields sleep at most once in this long; the others only release the GIL."""
SHORTEST_SLEEP_SECONDS = 1e-6
PR_SET_TIMERSLACK = 29
"""Linux `prctl` option: the slack the kernel may add to the calling thread's sleeps."""
SHORTEST_TIMER_SLACK_NS = 1
TOOL_ID = 3
TOOL_NAME = "cs-stress"

_worker = threading.local()
"""`rng` and `perturb` are set on worker threads only; `slept_at` on any thread that yielded."""


def yield_count(rng: random.Random, perturb: Perturbation) -> int:
    """How many scheduler yields to make now: usually none."""
    if rng.random() >= perturb.yield_probability:
        return 0
    return 1 + rng.randrange(perturb.max_yields)


def scheduler_yields(count: int) -> None:
    """Each yield releases the GIL. A thread's first yield, and its first one after each sleep
    interval, sleeps for the shortest time the OS allows instead: the CPU is free meanwhile, so a
    waiting worker that the OS was not running takes the GIL, even on a busy machine, where
    releases alone let the yielding worker keep it
    (docs/specs/runners.md#python-yields-give-up-the-cpu).

    `os.sched_yield()` handed the GIL over too, but gave up the thread's turn whenever another
    process wanted the CPU: a whole time slice at every yield on Linux, a scheduler quantum now
    and then on macOS. On a busy machine correct runs of yield-heavy cases stalled.
    """
    for _ in range(count):
        if _slept_recently():
            _release_gil()
        else:
            _sleep_briefly()


def _slept_recently() -> bool:
    slept_at: float = getattr(_worker, "slept_at", -math.inf)
    return time.perf_counter() - slept_at < SLEEP_INTERVAL_SECONDS


def _release_gil() -> None:
    """Releases the GIL for a system call that returns at once."""
    select.select([], [], [], 0)


def _sleep_briefly() -> None:
    time.sleep(SHORTEST_SLEEP_SECONDS)
    _worker.slept_at = time.perf_counter()


def _shorten_sleeps() -> None:
    """Linux pads each sleep of the thread by its timer slack, 50 µs by default, so a yield's
    sleep would take ten times what it does on macOS."""
    if sys.platform == "linux":
        ctypes.CDLL(None).prctl(PR_SET_TIMERSLACK, SHORTEST_TIMER_SLACK_NS, 0, 0, 0)


@contextmanager
def worker_thread(rng: random.Random, perturb: Perturbation) -> Generator[None]:
    """Marks the current thread as a worker, so injected yields draw from its PRNG and sleep
    as briefly as the OS allows."""
    _worker.rng, _worker.perturb = rng, perturb
    _shorten_sleeps()
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
