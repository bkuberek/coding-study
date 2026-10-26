"""The machine state a bench runs under (docs/specs/performance-analysis.md#environment-record).

macOS answers through `sysctl -n machdep.cpu.brand_string` and `pmset -g batt`; elsewhere the
CPU falls back to `platform.processor()` and the power source is unknown.
"""

import os
import platform
import subprocess
from collections.abc import Sequence

from coding_study.domain.bench_records import MachineState, PowerSource

CPU_COMMAND = ("sysctl", "-n", "machdep.cpu.brand_string")
POWER_COMMAND = ("pmset", "-g", "batt")
PROBE_TIMEOUT_SECONDS = 2.0
AC_MARKER = "'AC Power'"
BATTERY_MARKER = "'Battery Power'"


class SystemMachine:
    """`MachineProbe` for the machine `cstudy` runs on."""

    def snapshot(self) -> MachineState:
        return MachineState(_cpu(), _power(), _load(), os.cpu_count() or 1)


def _cpu() -> str:
    brand = _output(CPU_COMMAND)
    return brand.strip() if brand else platform.processor() or platform.machine()


def _power() -> PowerSource:
    report = _output(POWER_COMMAND) or ""
    if AC_MARKER in report:
        return PowerSource.AC
    if BATTERY_MARKER in report:
        return PowerSource.BATTERY
    return PowerSource.UNKNOWN


def _load() -> float | None:
    try:
        return os.getloadavg()[0]
    except OSError:
        return None


def _output(command: Sequence[str]) -> str | None:
    try:
        completed = subprocess.run(
            command, capture_output=True, text=True, timeout=PROBE_TIMEOUT_SECONDS, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return completed.stdout if completed.returncode == 0 else None
