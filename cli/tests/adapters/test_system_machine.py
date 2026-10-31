import os

import pytest

from coding_study.adapters import system_machine
from coding_study.adapters.system_machine import SETTLE_POLL_SECONDS, SystemMachine
from coding_study.domain.bench_records import PowerSource

AC_REPORT = "Now drawing from 'AC Power'\n -InternalBattery-0 (id=1)\t100%; charged\n"
BATTERY_REPORT = "Now drawing from 'Battery Power'\n -InternalBattery-0 (id=1)\t80%\n"


def answering(outputs: dict[str, str | None]):
    def output(command):
        return outputs.get(command[0])

    return output


@pytest.mark.parametrize(
    ("report", "power"),
    [
        (AC_REPORT, PowerSource.AC),
        (BATTERY_REPORT, PowerSource.BATTERY),
        (None, PowerSource.UNKNOWN),
    ],
)
def test_the_power_source_comes_from_pmset(monkeypatch, report, power):
    monkeypatch.setattr(system_machine, "_output", answering({"pmset": report}))
    assert SystemMachine().snapshot().power is power


def test_the_cpu_comes_from_sysctl(monkeypatch):
    monkeypatch.setattr(system_machine, "_output", answering({"sysctl": "Apple M3 Pro\n"}))
    assert SystemMachine().snapshot().cpu == "Apple M3 Pro"


def test_without_sysctl_the_cpu_still_has_a_name(monkeypatch):
    monkeypatch.setattr(system_machine, "_output", answering({}))
    assert SystemMachine().snapshot().cpu


def test_the_core_count_is_positive(monkeypatch):
    monkeypatch.setattr(system_machine, "_output", answering({}))
    assert SystemMachine().snapshot().cores >= 1


class FakeTime:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


BUSY_LOAD = float(os.cpu_count() or 1)
"""Above half the cores."""


def settling_with(monkeypatch, *loads: float) -> FakeTime:
    """Settles a machine on AC power whose snapshots show `loads`, the last one repeating."""
    remaining = list(loads)
    monkeypatch.setattr(system_machine, "_output", answering({"pmset": AC_REPORT}))
    monkeypatch.setattr(
        system_machine, "_load", lambda: remaining.pop(0) if len(remaining) > 1 else remaining[0]
    )
    return FakeTime()


def test_settling_a_quiet_machine_does_not_wait(monkeypatch):
    time = settling_with(monkeypatch, 0.0)
    SystemMachine(time.sleep, time.monotonic).settle(60)
    assert time.sleeps == []


def test_settling_polls_until_the_load_drops(monkeypatch):
    time = settling_with(monkeypatch, BUSY_LOAD, BUSY_LOAD, 0.0)
    SystemMachine(time.sleep, time.monotonic).settle(60)
    assert time.sleeps == [SETTLE_POLL_SECONDS, SETTLE_POLL_SECONDS]


def test_settling_gives_up_at_the_timeout(monkeypatch):
    time = settling_with(monkeypatch, BUSY_LOAD)
    SystemMachine(time.sleep, time.monotonic).settle(2 * SETTLE_POLL_SECONDS + 2)
    assert time.sleeps == [SETTLE_POLL_SECONDS, SETTLE_POLL_SECONDS, 2]
