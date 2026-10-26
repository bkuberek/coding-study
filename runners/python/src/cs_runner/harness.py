"""Harness ops of stress runs: `@enter`, `@exit` and `@pause` (docs/specs/runners.md#harness-ops).

Probe sections measure the user's lock, not shared data: an exclusive entry while anyone is
inside, or a shared entry while an exclusive holder is inside, counts one violation.
"""

import threading
from collections.abc import Callable
from dataclasses import dataclass, field

from cs_runner.events import Section
from cs_runner.json_value import Json

ENTER = "@enter"
EXIT = "@exit"
PAUSE = "@pause"
EXCLUSIVE = "exclusive"
SHARED = "shared"

type Yielder = Callable[[int], None]
"""Yields to the scheduler `n` times, the way the run's model does."""


class HarnessError(Exception):
    """A harness op that cannot run, such as `@exit` without a matching `@enter`."""


@dataclass(slots=True)
class _Counters:
    shared: int = 0
    exclusive: int = 0
    entries: int = 0
    violations: int = 0
    max_occupancy: int = 0

    def enter(self, mode: str) -> None:
        if mode == EXCLUSIVE:
            self.violations += self.shared + self.exclusive > 0
            self.exclusive += 1
        else:
            self.violations += self.exclusive > 0
            self.shared += 1
        self.entries += 1
        self.max_occupancy = max(self.max_occupancy, self.shared + self.exclusive)

    def exit(self, mode: str) -> None:
        if mode == EXCLUSIVE:
            self.exclusive -= 1
        else:
            self.shared -= 1


class Sections:
    """One run's probe sections, created on first use, guarded by one lock."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, _Counters] = {}

    def enter(self, name: str, mode: str) -> None:
        with self._lock:
            self._counters.setdefault(name, _Counters()).enter(mode)

    def exit(self, name: str, mode: str) -> None:
        with self._lock:
            self._counters[name].exit(mode)

    def snapshot(self) -> dict[str, Section]:
        with self._lock:
            return {
                name: Section(counters.entries, counters.violations, counters.max_occupancy)
                for name, counters in self._counters.items()
            }


@dataclass(slots=True)
class WorkerHarness:
    """One worker's view of the harness: the sections it is inside, last entered first."""

    sections: Sections
    pause: Yielder
    _entered: dict[str, list[str]] = field(default_factory=dict[str, list[str]])

    def run(self, op: str, args: tuple[Json, ...]) -> None:
        if op == ENTER and len(args) == 2 and args[1] in (EXCLUSIVE, SHARED):
            name, mode = str(args[0]), str(args[1])
            self.sections.enter(name, mode)
            self._entered.setdefault(name, []).append(mode)
        elif op == EXIT and len(args) == 1:
            name = str(args[0])
            modes = self._entered.get(name)
            if not modes:
                raise HarnessError(f'@exit "{name}" without a matching @enter')
            self.sections.exit(name, modes.pop())
        elif op == PAUSE and len(args) == 1 and isinstance(args[0], int):
            self.pause(args[0])
        else:
            raise HarnessError(f"{op} cannot take {list(args)}")
