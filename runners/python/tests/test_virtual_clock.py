"""The virtual clock of Python projects: `cs_support.virtual_clock`'s event loop, its helpers and
its pytest plugin (docs/specs/runners.md#virtual-clock-and-stress-in-project-jobs)."""

import asyncio
import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

from cs_support.virtual_clock import DeadlockError, advance, now, run, settle

PLUGIN_TIMEOUT_SECONDS = 60


async def _sleep_then_read(seconds: float) -> int:
    await asyncio.sleep(seconds)
    return now()


def test_the_clock_starts_at_zero():
    assert run(_now()) == 0


async def _now() -> int:
    return now()


def test_a_sleep_moves_the_clock_without_taking_real_time():
    started = time.perf_counter()
    assert run(_sleep_then_read(3600)) == 3_600_000
    assert time.perf_counter() - started < 1


def test_each_timer_fires_at_its_own_time_along_a_chain_of_awaits():
    async def chain() -> list[int]:
        stamps: list[int] = []
        for _ in range(3):
            await asyncio.sleep(0.01)
            stamps.append(now())
        return stamps

    assert run(chain()) == [10, 20, 30]


def test_advance_fires_the_timers_due_on_the_way_and_settles():
    async def scenario() -> list[str]:
        log: list[str] = []

        async def note(name: str, seconds: float) -> None:
            await asyncio.sleep(seconds)
            log.append(f"{name}@{now()}")

        asyncio.get_running_loop().create_task(note("late", 0.03))
        asyncio.get_running_loop().create_task(note("early", 0.01))
        await advance(20)
        log.append(f"advanced@{now()}")
        await advance(20)
        return log

    assert run(scenario()) == ["early@10", "advanced@20", "late@30"]


def test_settle_runs_every_task_that_can_run_until_each_waits():
    async def scenario() -> list[str]:
        log: list[str] = []

        async def steps() -> None:
            log.append("started")
            await asyncio.sleep(0)
            log.append("resumed")
            await asyncio.Event().wait()

        asyncio.get_running_loop().create_task(steps())
        await settle()
        return log

    assert run(scenario()) == ["started", "resumed"]


def test_a_task_that_waits_while_nothing_can_run_is_a_deadlock_at_the_virtual_time():
    async def scenario() -> None:
        await advance(2000)
        await asyncio.get_running_loop().create_future()

    with pytest.raises(DeadlockError) as raised:
        run(scenario())
    assert (raised.value.milliseconds, str(raised.value)) == (
        2000,
        "deadlock: every task waits and no timer is due, at 2000 ms",
    )


def test_a_deadlock_is_reported_at_once():
    started = time.perf_counter()
    with pytest.raises(DeadlockError):
        run(asyncio.Event().wait())
    assert time.perf_counter() - started < 1


def test_a_wait_for_a_thread_is_no_deadlock():
    async def scenario() -> int:
        await asyncio.to_thread(time.sleep, 0.01)
        return now()

    assert run(scenario()) == 0


def test_the_clock_stands_still_while_a_thread_works_for_the_loop():
    async def scenario() -> str:
        try:
            await asyncio.wait_for(asyncio.to_thread(time.sleep, 0.05), timeout=0.01)
        except TimeoutError:
            return "timed out"
        return f"finished at {now()} ms"

    assert run(scenario()) == "finished at 0 ms"


def test_a_thread_that_finished_lets_the_clock_move_again():
    async def scenario() -> int:
        await asyncio.to_thread(time.sleep, 0)
        await asyncio.sleep(5)
        return now()

    assert run(scenario()) == 5000


def test_timeouts_fire_on_the_virtual_clock():
    async def scenario() -> tuple[str, int]:
        try:
            await asyncio.wait_for(asyncio.Event().wait(), timeout=30)
        except TimeoutError:
            return ("timed out", now())
        return ("finished", now())

    assert run(scenario()) == ("timed out", 30_000)


async def _race(names: str) -> str:
    """Tasks that wake at the same instant, in the order they woke."""
    woke: list[str] = []

    async def wake(name: str) -> None:
        await asyncio.sleep(0.01)
        woke.append(name)

    await asyncio.gather(*(wake(name) for name in names))
    return "".join(woke)


def test_timers_due_at_the_same_instant_fire_in_an_order_the_seed_decides():
    orders = {run(_race("abcdef"), seed=seed) for seed in range(10)}
    assert len(orders) > 1


def test_the_same_seed_gives_the_same_order():
    assert len({run(_race("abcdef"), seed=3) for _ in range(5)}) == 1


def test_seed_zero_is_the_default():
    assert run(_race("abcdef")) == run(_race("abcdef"), seed=0)


def test_the_helpers_refuse_a_loop_without_the_virtual_clock():
    with pytest.raises(RuntimeError, match="only on the virtual clock"):
        asyncio.run(_now())


PLUGIN_TESTS = """
import asyncio

from cs_support.virtual_clock import advance, now


async def test_waits_take_no_real_time() -> None:
    await asyncio.sleep(60)
    await advance(500)
    assert now() == 60_500


async def test_deadlocks() -> None:
    await asyncio.Event().wait()


def test_plain_tests_still_run() -> None:
    assert now is not None


async def test_with_a_fixture(tmp_path) -> None:
    assert tmp_path.is_dir()
"""


def test_the_pytest_plugin_runs_async_tests_on_the_virtual_clock(tmp_path: Path):
    """As the runner hosts pytest: plugin autoloading off and the plugin named with `-p`."""
    (tmp_path / "test_clock.py").write_text(textwrap.dedent(PLUGIN_TESTS), encoding="utf-8")
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "cs_support.virtual_clock",
            "-p",
            "no:cacheprovider",
            "-q",
            "-rA",
            str(tmp_path),
        ],
        cwd=tmp_path,
        env=os.environ | {"PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1", "COLUMNS": "200"},
        capture_output=True,
        text=True,
        timeout=PLUGIN_TIMEOUT_SECONDS,
        check=False,
    )
    summary = [
        line for line in process.stdout.splitlines() if line.startswith(("PASSED", "FAILED"))
    ]
    assert sorted(summary) == [
        "FAILED test_clock.py::test_deadlocks - cs_support.virtual_clock.DeadlockError: "
        "deadlock: every task waits and no timer is due, at 0 ms",
        "PASSED test_clock.py::test_plain_tests_still_run",
        "PASSED test_clock.py::test_waits_take_no_real_time",
        "PASSED test_clock.py::test_with_a_fixture",
    ]
