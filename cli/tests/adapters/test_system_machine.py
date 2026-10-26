import pytest

from coding_study.adapters import system_machine
from coding_study.adapters.system_machine import SystemMachine
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
