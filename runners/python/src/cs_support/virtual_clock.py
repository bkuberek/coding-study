"""The virtual clock of Python projects (docs/specs/runners.md#virtual-clock-and-stress-in-project-
jobs).

`VirtualClockLoop` is an asyncio event loop whose clock moves only while every task waits: when no
callback is ready, it jumps to the next timer instead of sleeping, so a wait of any length takes no
real time and a case gives the same result on every run. Timers due at the same instant fire in an
order that a seeded shuffle decides, since asyncio leaves that order undefined: seed 0 grades a
submission and runs your tests, and `cstudy verify` tries seeds 0 to 9 (D10), which catches an
expected value that depends on a tie.

When no callback is ready and no timer is due, every task waits for good: the loop raises
`DeadlockError`, which ends the case or the test at once. While a call that the loop handed to a
thread (`asyncio.to_thread`, `loop.run_in_executor`) runs, or a file or socket is registered, the
clock does not move: the loop waits for real until they wake it. A wait on what the loop cannot
see, such as a lock held by a thread or a busy loop, never lets the clock move either.

Code reads the time through the loop (`asyncio.get_running_loop().time()`, `asyncio.sleep`,
`asyncio.timeout`, `asyncio.wait_for`), never through `time.monotonic()` or `time.time()`, which
stay real.

The module is also a pytest plugin, which runs each `async def` test on a loop of its own with seed
0, as `cstudy submit` grades a case. Load it with `-p cs_support.virtual_clock`, as the starter's
`pyproject.toml` does in `addopts`, since `cstudy` turns plugin autoloading off. A test settles,
moves and reads the clock with `settle`, `advance` and `now`. Tasks still pending when a test ends
are cancelled, as `asyncio.run` does.
"""

import asyncio
import heapq
import inspect
import random
import selectors
from collections import deque
from collections.abc import Callable, Coroutine
from concurrent.futures import Executor
from typing import Any, cast

GRADING_SEED = 0
"""The seed of `cstudy submit` and of the pytest plugin."""
NANOSECONDS_PER_SECOND = 1_000_000_000
NANOSECONDS_PER_MILLISECOND = 1_000_000
MILLISECONDS_PER_SECOND = 1000
SAME_INSTANT_SECONDS = 1e-6
"""Timers due within this of each other fire as one instant: delays summed in floating point
(`0.1 + 0.2`) land a few units in the last place apart."""
_SELF_PIPE = 1
"""The selector's own registration: the loop's wake-up pipe for other threads."""


class DeadlockError(RuntimeError):
    """Every task waits and no timer is due: nothing can wake a task."""

    def __init__(self, milliseconds: int) -> None:
        super().__init__(f"deadlock: every task waits and no timer is due, at {milliseconds} ms")
        self.milliseconds = milliseconds


class VirtualClockLoop(asyncio.SelectorEventLoop):
    """An event loop on a virtual clock that starts at 0."""

    def __init__(self, seed: int = GRADING_SEED) -> None:
        self._now_ns = 0
        self._ties = random.Random(seed)
        self._outside_waits = 0
        """Calls running on threads for the loop, whose end wakes it."""
        self._clock_selector = _ClockSelector(self)
        super().__init__(self._clock_selector)

    def time(self) -> float:
        return self._now_ns / NANOSECONDS_PER_SECOND

    def now_ms(self) -> int:
        """The virtual milliseconds since the loop started."""
        return round(self._now_ns / NANOSECONDS_PER_MILLISECOND)

    async def settle(self) -> None:
        """Lets every task that can run do so, and every timer due now fire, until each task
        waits."""
        while self._ready_callbacks() or self._timer_due():
            await asyncio.sleep(0)

    async def advance(self, milliseconds: int) -> None:
        """Moves the clock forward; each timer due on the way fires at its own time, and the code
        settles after each."""
        await asyncio.sleep(milliseconds / MILLISECONDS_PER_SECOND)
        await self.settle()

    def run_in_executor[T, *Ts](
        self, executor: Executor | None, func: Callable[[*Ts], T], *args: *Ts
    ) -> asyncio.Future[T]:
        """The clock stands still until the call ends."""
        future = super().run_in_executor(executor, func, *args)
        self._outside_waits += 1
        future.add_done_callback(self._outside_wait_ended)
        return future

    async def shutdown_default_executor(self, timeout: float | None = None) -> None:
        """Waits for the executor's threads for real: its timeout must not fire on the virtual
        clock while they end."""
        self._outside_waits += 1
        try:
            await super().shutdown_default_executor(timeout)
        finally:
            self._outside_waits -= 1

    def idle(self, timeout: float | None) -> list[tuple[selectors.SelectorKey, int]]:
        """What the loop does when no callback is ready: it waits for real for what can wake it
        from outside, else jumps to the next timer, else reports a deadlock."""
        if self._waits_on_outside():
            return self._clock_selector.wait()
        if timeout is not None:
            self._now_ns += round(timeout * NANOSECONDS_PER_SECOND)
            return []
        raise DeadlockError(self.now_ms())

    def release_due_timers(self) -> None:
        """Moves the timers due now to the ready callbacks, those of one instant in the order of
        the seeded shuffle. The loop would move them in the order of its heap."""
        scheduled = self._timers()
        due: list[asyncio.TimerHandle] = []
        while scheduled and scheduled[0].when() < self.time() + SAME_INSTANT_SECONDS:
            handle = heapq.heappop(scheduled)
            if handle.cancelled():
                vars(self)["_timer_cancelled_count"] -= 1
            else:
                due.append(handle)
            object.__setattr__(handle, "_scheduled", False)
        self._ties.shuffle(due)
        self._ready_callbacks().extend(due)

    def _outside_wait_ended(self, _: asyncio.Future[Any]) -> None:
        self._outside_waits -= 1

    def _waits_on_outside(self) -> bool:
        """Whether a thread works for the loop, or the code registered a file or socket: either
        wakes the loop when it is done."""
        registered = len(self._clock_selector.get_map())
        return self._outside_waits > 0 or registered > _SELF_PIPE

    def _timer_due(self) -> bool:
        scheduled = self._timers()
        return bool(scheduled) and scheduled[0].when() < self.time() + SAME_INSTANT_SECONDS

    def _ready_callbacks(self) -> deque[asyncio.Handle]:
        return cast("deque[asyncio.Handle]", vars(self)["_ready"])

    def _timers(self) -> list[asyncio.TimerHandle]:
        return cast("list[asyncio.TimerHandle]", vars(self)["_scheduled"])


class _ClockSelector(selectors.DefaultSelector):
    """Polls without waiting, and lets the loop decide what an idle moment means."""

    def __init__(self, loop: VirtualClockLoop) -> None:
        super().__init__()
        self._loop = loop

    def select(self, timeout: float | None = None) -> list[tuple[selectors.SelectorKey, int]]:
        events = super().select(0)
        if not events and timeout != 0:
            events = self._loop.idle(timeout)
        self._loop.release_due_timers()
        return events

    def wait(self) -> list[tuple[selectors.SelectorKey, int]]:
        """Blocks until a thread or a file wakes the loop."""
        return super().select(None)


def run[T](main: Coroutine[Any, Any, T], *, seed: int = GRADING_SEED) -> T:
    """Runs `main` on a new `VirtualClockLoop`, as `asyncio.run` does; raises `DeadlockError` when
    it waits for good."""
    return asyncio.run(main, loop_factory=lambda: VirtualClockLoop(seed))


def now() -> int:
    """The virtual milliseconds since the case or test started."""
    return _running_clock().now_ms()


async def settle() -> None:
    """Lets every task run until each one waits, without moving the clock."""
    await _running_clock().settle()


async def advance(milliseconds: int) -> None:
    """Moves the clock forward, each timer due on the way firing at its own time, then settles."""
    await _running_clock().advance(milliseconds)


def _running_clock() -> VirtualClockLoop:
    loop = asyncio.get_running_loop()
    if not isinstance(loop, VirtualClockLoop):
        raise RuntimeError(
            "this helper runs only on the virtual clock: run the test with the pytest plugin "
            "`-p cs_support.virtual_clock`"
        )
    return loop


def pytest_pyfunc_call(pyfuncitem: Any) -> bool | None:
    """The pytest hook: an `async def` test runs on the virtual clock with the grading seed."""
    function = pyfuncitem.obj
    if not inspect.iscoroutinefunction(function):
        return None
    funcargs = pyfuncitem.funcargs
    arguments = {name: funcargs[name] for name in pyfuncitem._fixtureinfo.argnames}
    run(function(**arguments))
    return True
