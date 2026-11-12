"""cpu-scheduler-sim promises that its hidden cases catch the classic mistakes of simulating a CPU
scheduler: ties broken by name instead of arrival and the order added, a shortest-job-first that
preempts or waits for a job that has not arrived, times measured from zero instead of from the
arrival, a preempted process queued ahead of the arrivals of its tick, a feedback queue that
forgets the allotment a process has used or leaves the running process out of a boost, and a
multicore scheduler that counts load or steals work the wrong way. These tests replay every case
against a model of the scheduler written from the statement, which must give every expected
output, and against that model with one mistake planted at a time, which some hidden case must
fail. A mistake that crashes fails its case, as a thrown exception does in the grader."""

import json
import re
from collections.abc import Callable, Mapping, Sequence
from math import gcd
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0359-cpu-scheduler-sim"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]
RUNS = ("runFcfs", "runSjf", "runRoundRobin", "runMlfq", "runMulticore")

Tick = tuple[int, int, int]
"""One tick of a trace: the core, the index of the process that ran and the time."""


class Model:
    """The scheduler as the statement words it. Every policy is simulated one tick at a time and
    leaves a trace of which process ran on which core at which tick; the segments, the switches,
    the busy time and every per-process time are read back from the trace. Each mistake below
    overrides one rule."""

    def __init__(self) -> None:
        self.procs: list[tuple[str, int, int]] = []
        self.result: dict[str, Any] | None = None

    # --- level 1
    def add_process(self, pid: str, arrival: int, burst: int) -> bool:
        if any(p[0] == pid for p in self.procs):
            return False
        self.procs.append((pid, arrival, burst))
        return True

    def fcfs_key(self, i: int) -> tuple:
        return (self.procs[i][1], i)

    def sjf_key(self, i: int) -> tuple:
        return (self.procs[i][2], self.procs[i][1], i)

    def ready(self, left: list[int], t: int) -> list[int]:
        return [i for i in range(len(self.procs)) if left[i] > 0 and self.procs[i][1] <= t]

    def non_preemptive(self, key: Callable[[int], tuple]) -> list[str]:
        left = [p[2] for p in self.procs]
        trace: list[Tick] = []
        on = None
        t = 0
        while any(left):
            if on is not None and left[on] == 0:
                on = None
            if on is None:
                candidates = self.ready(left, t)
                on = min(candidates, key=key) if candidates else None
            if on is not None:
                trace.append((0, on, t))
                left[on] -= 1
            t += 1
        return self.record(trace, 1)[0]

    def run_fcfs(self) -> list[str]:
        return self.non_preemptive(self.fcfs_key)

    def run_sjf(self) -> list[str]:
        return self.non_preemptive(self.sjf_key)

    @property
    def run(self) -> dict[str, Any]:
        """The record of the latest run, for the methods that are only called after one."""
        assert self.result is not None
        return self.result

    def index(self, pid: str) -> int | None:
        if self.result is None:
            return None
        return next((i for i in range(self.result["n"]) if self.procs[i][0] == pid), None)

    def turnaround(self, i: int) -> int:
        return self.run["done"][i] - self.procs[i][1]

    def waiting(self, i: int) -> int:
        return self.turnaround(i) - self.procs[i][2]

    def response(self, i: int) -> int:
        return self.run["first"][i] - self.procs[i][1]

    def per_process(self, pid: str, metric: Callable[[int], int]) -> int:
        i = self.index(pid)
        return -1 if i is None else metric(i)

    def waiting_time(self, pid: str) -> int:
        return self.per_process(pid, self.waiting)

    def turnaround_time(self, pid: str) -> int:
        return self.per_process(pid, self.turnaround)

    def fraction(self, top: int, bottom: int) -> str:
        common = gcd(top, bottom)
        return f"{top // common}/{bottom // common}"

    def count(self) -> int:
        return self.run["n"]

    def average(self, metric: Callable[[int], int]) -> str:
        if self.result is None:
            return ""
        return self.fraction(sum(metric(i) for i in range(self.result["n"])), self.count())

    def average_waiting(self) -> str:
        return self.average(self.waiting)

    def average_turnaround(self) -> str:
        return self.average(self.turnaround)

    # --- the record of a run, read back from its trace
    def merges(self, segment: list, pid: str, t: int) -> bool:
        return segment[0] == pid and segment[2] == t

    def switch(self, last: str | None, pid: str, after_idle: bool) -> bool:
        return last is not None and last != pid

    def counts_switches_of(self, core: int) -> bool:
        return True

    def record(self, trace: list[Tick], cores: int, migrations: int = 0) -> list[list[str]]:
        segments: list[list[list]] = [[] for _ in range(cores)]
        switches = 0
        busy = [0] * cores
        last: list[str | None] = [None] * cores
        first: dict[int, int] = {}
        done: dict[int, int] = {}
        for core, i, t in sorted(trace, key=lambda tick: (tick[0], tick[2])):
            pid = self.procs[i][0]
            mine = segments[core]
            if mine and self.merges(mine[-1], pid, t):
                mine[-1][2] = t + 1
            else:
                after_idle = bool(mine) and mine[-1][2] != t
                if self.counts_switches_of(core):
                    switches += self.switch(last[core], pid, after_idle)
                mine.append([pid, t, t + 1])
            last[core] = pid
            busy[core] += 1
            first[i] = min(first.get(i, t), t)
            done[i] = max(done.get(i, 0), t + 1)
        self.result = {
            "n": len(self.procs),
            "first": first,
            "done": done,
            "switches": switches,
            "busy": busy,
            "end": max(done.values()),
            "migrations": migrations,
        }
        return [[f"{p}:{s}-{e}" for p, s, e in core] for core in segments]

    # --- level 2
    def run_round_robin(self, quantum: int) -> list[str]:
        return self.cores(1, quantum, False)[0]

    def response_time(self, pid: str) -> int:
        return self.per_process(pid, self.response)

    def average_response(self) -> str:
        return self.average(self.response)

    def context_switches(self) -> int:
        return -1 if self.result is None else self.result["switches"]

    def arrivals(self, t: int) -> list[int]:
        return sorted((i for i, p in enumerate(self.procs) if p[1] == t), key=self.fcfs_key)

    def settle(self, queue: list[int], arrived: list[int], back: int | None) -> None:
        """Puts the arrivals of a tick and the process whose quantum ended on a queue."""
        queue.extend(arrived)
        if back is not None:
            queue.append(back)

    def expired(self, used: int, quantum: int) -> bool:
        return used == quantum

    # --- level 3
    def demote(self, level: int, levels: int) -> int:
        return min(level + 1, levels - 1)

    def boost_clock(self, t: int, busy: int) -> int:
        """The time that decides whether a boost is due."""
        return t

    def boost_due(self, clock: int, period: int) -> bool:
        return period > 0 and clock > 0 and clock % period == 0

    def join_order(self, queues: list[list[int]]) -> list[list[int]]:
        return queues

    def boost(self, queues: list[list[int]], level: dict, used: dict, on: int | None) -> None:
        joined = [i for queue in self.join_order(queues) for i in queue]
        for queue in queues:
            queue.clear()
        queues[0].extend(joined)
        for i in [*joined, *([on] if on is not None else [])]:
            level[i], used[i] = 0, 0

    def preempts(self, queues: list[list[int]], mine: int) -> bool:
        return any(queues[i] for i in range(mine))

    def preempted(self, queues: list[list[int]], i: int, level: dict, used: dict) -> None:
        queues[level[i]].append(i)

    def run_mlfq(self, quanta: list[int], boost_period: int) -> list[str]:
        left = [p[2] for p in self.procs]
        queues: list[list[int]] = [[] for _ in quanta]
        level: dict[int, int] = {}
        used: dict[int, int] = {}
        trace: list[Tick] = []
        on = None
        busy = 0
        t = 0
        while any(left):
            back = None
            if on is not None and left[on] == 0:
                on = None
            elif on is not None and self.expired(used[on], quanta[level[on]]):
                level[on], used[on] = self.demote(level[on], len(quanta)), 0
                back, on = on, None
            arrived = self.arrivals(t)
            for i in arrived:
                level[i], used[i] = 0, 0
            queues[0].extend(arrived)
            if back is not None:
                queues[level[back]].append(back)
            if self.boost_due(self.boost_clock(t, busy), boost_period):
                self.boost(queues, level, used, on)
            if on is not None and self.preempts(queues, level[on]):
                self.preempted(queues, on, level, used)
                on = None
            if on is None:
                on = next((queue.pop(0) for queue in queues if queue), None)
            if on is not None:
                trace.append((0, on, t))
                left[on] -= 1
                used[on] += 1
                busy += 1
            t += 1
        return self.record(trace, 1)[0]

    # --- level 4
    def load(self, queues: list[list[int]], on: list, back: list, core: int) -> int:
        return len(queues[core]) + (on[core] is not None) + (back[core] is not None)

    def pick_core(self, queues: list[list[int]], on: list, back: list) -> int:
        loads = [self.load(queues, on, back, c) for c in range(len(queues))]
        return loads.index(min(loads))

    def victim(self, queues: list[list[int]], thief: int) -> int | None:
        best = None
        for c, queue in enumerate(queues):
            if queue and (best is None or len(queue) > len(queues[best])):
                best = c
        return best

    def take(self, queue: list[int]) -> int:
        return queue.pop()

    def may_steal(self, steal: bool) -> bool:
        return steal

    def cores(self, count: int, quantum: int, steal: bool) -> list[list[str]]:
        left = [p[2] for p in self.procs]
        queues: list[list[int]] = [[] for _ in range(count)]
        on: list[int | None] = [None] * count
        used = [0] * count
        trace: list[Tick] = []
        migrations = 0
        t = 0
        while any(left):
            back: list[int | None] = [None] * count
            for c in range(count):
                i = on[c]
                if i is not None and left[i] == 0:
                    on[c] = None
                elif i is not None and self.expired(used[c], quantum):
                    back[c], on[c] = i, None
            placed: list[list[int]] = [[] for _ in range(count)]
            for i in self.arrivals(t):
                pending = [q + p for q, p in zip(queues, placed, strict=True)]
                placed[self.pick_core(pending, on, back)].append(i)
            for c in range(count):
                self.settle(queues[c], placed[c], back[c])
                if on[c] is None and queues[c]:
                    on[c], used[c] = queues[c].pop(0), 0
            for c in range(count):
                if self.may_steal(steal) and on[c] is None:
                    v = self.victim(queues, c)
                    if v is not None:
                        on[c], used[c] = self.take(queues[v]), 0
                        migrations += 1
            for c in range(count):
                i = on[c]
                if i is not None:
                    trace.append((c, i, t))
                    left[i] -= 1
                    used[c] += 1
            t += 1
        return self.record(trace, count, migrations)

    def run_multicore(self, cores: int, quantum: int, steal: bool) -> list[list[str]]:
        return self.cores(cores, quantum, steal)

    def utilization(self, core: int) -> str:
        if self.result is None or not 0 <= core < len(self.result["busy"]):
            return ""
        return self.fraction(self.result["busy"][core], self.span(core))

    def span(self, core: int) -> int:
        return self.run["end"]

    def migrations(self) -> int:
        return -1 if self.result is None else self.result["migrations"]


# ------------------------------------------------------------------ level 1 mistakes
class TiesByName(Model):
    """Breaks a tie in arrival by the name of the process."""

    def fcfs_key(self, i: int) -> tuple:
        return (self.procs[i][1], self.procs[i][0])


class SjfTiesByAddOrder(Model):
    """Breaks a tie in burst by the order added, skipping the arrival."""

    def sjf_key(self, i: int) -> tuple:
        return (self.procs[i][2], i)


class SjfPreempts(Model):
    """Switches to a job with less work left the moment it arrives."""

    def run_sjf(self) -> list[str]:
        left = [p[2] for p in self.procs]
        trace: list[Tick] = []
        t = 0
        while any(left):
            ready = self.ready(left, t)
            if ready:
                i = min(ready, key=lambda j: (left[j], self.procs[j][1], j))
                trace.append((0, i, t))
                left[i] -= 1
            t += 1
        return self.record(trace, 1)[0]


class SjfWaitsForTheShortest(Model):
    """Picks the shortest unfinished job even before it has arrived, and waits for it."""

    def ready(self, left: list[int], t: int) -> list[int]:
        shortest = min((i for i in range(len(self.procs)) if left[i] > 0), key=self.sjf_key)
        return [shortest] if self.procs[shortest][1] <= t else []


class ArrivalMustBeEarlier(Model):
    """Leaves out a process that arrives at the very tick the CPU frees up."""

    def ready(self, left: list[int], t: int) -> list[int]:
        return [i for i in range(len(self.procs)) if left[i] > 0 and self.procs[i][1] < t]


class WaitingFromZero(Model):
    """Measures waiting from time 0 instead of from the arrival."""

    def waiting(self, i: int) -> int:
        return self.run["done"][i] - self.procs[i][2]


class TurnaroundIsCompletion(Model):
    """Reports the completion time as the turnaround time."""

    def turnaround(self, i: int) -> int:
        return self.run["done"][i]


class FractionNotReduced(Model):
    """Writes the sum over the count without reducing it."""

    def fraction(self, top: int, bottom: int) -> str:
        return f"{top}/{bottom}"


class WholeNumbersWithoutDenominator(Model):
    """Writes a whole average as a bare number."""

    def fraction(self, top: int, bottom: int) -> str:
        return super().fraction(top, bottom).removesuffix("/1")


class DuplicateReplaces(Model):
    """Lets a second process with the same name replace the first."""

    def add_process(self, pid: str, arrival: int, burst: int) -> bool:
        self.procs = [p for p in self.procs if p[0] != pid]
        self.procs.append((pid, arrival, burst))
        return True


class AveragesOverTheWorkload(Model):
    """Divides by the number of processes added so far, not the number in the run."""

    def count(self) -> int:
        return len(self.procs)


class NoRunGivesZero(Model):
    """Answers 0 before the first run."""

    def per_process(self, pid: str, metric: Callable[[int], int]) -> int:
        return 0 if self.result is None else super().per_process(pid, metric)


# ------------------------------------------------------------------ level 2 mistakes
class PreemptedBeforeArrivals(Model):
    """Queues the preempted process ahead of the processes that arrive at the same tick."""

    def settle(self, queue: list[int], arrived: list[int], back: int | None) -> None:
        if back is not None:
            queue.append(back)
        queue.extend(arrived)


class ArrivalsToTheFront(Model):
    """Puts a new arrival at the front of the queue."""

    def settle(self, queue: list[int], arrived: list[int], back: int | None) -> None:
        queue[:0] = arrived
        if back is not None:
            queue.append(back)


class SegmentPerQuantum(Model):
    """Starts a new segment, and counts a switch, every time a quantum ends."""

    def run_round_robin(self, quantum: int) -> list[str]:
        self.quantum = quantum
        return super().run_round_robin(quantum)

    def merges(self, segment: list, pid: str, t: int) -> bool:
        whole = getattr(self, "quantum", None)
        return super().merges(segment, pid, t) and (whole is None or t - segment[1] < whole)

    def switch(self, last: str | None, pid: str, after_idle: bool) -> bool:
        return last is not None


class IdleIsNoSwitch(Model):
    """Does not count a switch when the CPU was idle in between."""

    def switch(self, last: str | None, pid: str, after_idle: bool) -> bool:
        return super().switch(last, pid, after_idle) and not after_idle


class ResponseFromZero(Model):
    """Reports the first tick on the CPU as the response time."""

    def response(self, i: int) -> int:
        return self.run["first"][i]


class QuantumOffByOne(Model):
    """Lets a process run one tick past its quantum."""

    def expired(self, used: int, quantum: int) -> bool:
        return used > quantum


# ------------------------------------------------------------------ level 3 mistakes
class PreemptionResetsAllotment(Model):
    """Gives a preempted process a fresh allotment at its level."""

    def preempted(self, queues: list[list[int]], i: int, level: dict, used: dict) -> None:
        used[i] = 0
        super().preempted(queues, i, level, used)


class PreemptedToTheFront(Model):
    """Puts a preempted process at the front of its queue."""

    def preempted(self, queues: list[list[int]], i: int, level: dict, used: dict) -> None:
        queues[level[i]].insert(0, i)


class PreemptionDemotes(Model):
    """Moves a preempted process one queue down, as if it had used its allotment."""

    def preempted(self, queues: list[list[int]], i: int, level: dict, used: dict) -> None:
        level[i], used[i] = self.demote(level[i], len(queues)), 0
        super().preempted(queues, i, level, used)


class NoPreemptionOnArrival(Model):
    """Lets the running process finish its quantum before a higher queue runs."""

    def preempts(self, queues: list[list[int]], mine: int) -> bool:
        return False


class BoostLeavesTheRunningProcess(Model):
    """Boosts the queues but not the process on the CPU."""

    def boost(self, queues: list[list[int]], level: dict, used: dict, on: int | None) -> None:
        super().boost(queues, level, used, None)


class BoostKeepsAllotments(Model):
    """Moves every process to the top queue but keeps the allotment it has used."""

    def boost(self, queues: list[list[int]], level: dict, used: dict, on: int | None) -> None:
        kept = dict(used)
        super().boost(queues, level, used, on)
        used.update(kept)


class BoostJoinsBottomFirst(Model):
    """Joins the queues from the lowest priority up."""

    def join_order(self, queues: list[list[int]]) -> list[list[int]]:
        return queues[::-1]


class BoostOneTickLate(Model):
    """Boosts one tick after each multiple of the period."""

    def boost_clock(self, t: int, busy: int) -> int:
        return t - 1


class BoostOnTheBusyClock(Model):
    """Counts the boost period in busy ticks, so idle time delays the boosts."""

    def boost_clock(self, t: int, busy: int) -> int:
        return busy


class BottomQueueRunsToCompletion(Model):
    """Never takes a process off the CPU at the lowest level."""

    def run_mlfq(self, quanta: list[int], boost_period: int) -> list[str]:
        return super().run_mlfq([*quanta[:-1], 10**9], boost_period)


# ------------------------------------------------------------------ level 4 mistakes
class LoadIgnoresTheRunningProcess(Model):
    """Compares the queue lengths and leaves out the process on the CPU."""

    def load(self, queues: list[list[int]], on: list, back: list, core: int) -> int:
        return len(queues[core]) + (back[core] is not None)


class LoadIgnoresTheExpiredProcess(Model):
    """Forgets the process whose quantum ended at this tick when it counts load."""

    def load(self, queues: list[list[int]], on: list, back: list, core: int) -> int:
        return len(queues[core]) + (on[core] is not None)


class TieToTheHighestCore(Model):
    """Breaks a tie in load by taking the highest core."""

    def pick_core(self, queues: list[list[int]], on: list, back: list) -> int:
        loads = [self.load(queues, on, back, c) for c in range(len(queues))]
        return max(c for c in range(len(loads)) if loads[c] == min(loads))


class CoresInTurn(Model):
    """Deals the arrivals to the cores in turn, whatever their load."""

    def cores(self, count: int, quantum: int, steal: bool) -> list[list[str]]:
        self.dealt = 0
        return super().cores(count, quantum, steal)

    def pick_core(self, queues: list[list[int]], on: list, back: list) -> int:
        self.dealt += 1
        return (self.dealt - 1) % len(queues)


class StealFromTheFront(Model):
    """Takes the process at the front of the victim's queue."""

    def take(self, queue: list[int]) -> int:
        return queue.pop(0)


class VictimTieToTheHighestCore(Model):
    """Breaks a tie between victims by taking the highest core."""

    def victim(self, queues: list[list[int]], thief: int) -> int | None:
        best = None
        for c, queue in enumerate(queues):
            if queue and (best is None or len(queue) >= len(queues[best])):
                best = c
        return best


class VictimIsTheNextCore(Model):
    """Looks only at the next core around the ring."""

    def victim(self, queues: list[list[int]], thief: int) -> int | None:
        neighbour = (thief + 1) % len(queues)
        return neighbour if queues[neighbour] else None


class AlwaysSteals(Model):
    """Steals even when stealing is off."""

    def may_steal(self, steal: bool) -> bool:
        return True


class UtilizationOverOwnSpan(Model):
    """Divides a core's busy time by the end of its own last segment."""

    def span(self, core: int) -> int:
        lines = self.run["lines"][core]
        return int(lines[-1].rsplit("-", 1)[1]) if lines else 1

    def record(self, trace: list[Tick], cores: int, migrations: int = 0) -> list[list[str]]:
        lines = super().record(trace, cores, migrations)
        self.run["lines"] = lines
        return lines


class SwitchesOfTheFirstCoreOnly(Model):
    """Counts the switches of core 0 and forgets the other cores."""

    def counts_switches_of(self, core: int) -> bool:
        return core == 0


MISTAKES: Sequence[type[Model]] = Model.__subclasses__()


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", op).lower()


def outputs(model_type: type[Model], case: Mapping[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor."""
    model = model_type()
    calls = zip(case["ops"][1:], case["args"][1:], strict=True)
    return [None, *(getattr(model, snake_case(op))(*arguments) for op, arguments in calls)]


def passes(model_type: type[Model], case: Mapping[str, Any]) -> bool:
    try:
        return outputs(model_type, case) == case["expected"]
    except (IndexError, KeyError, ValueError, TypeError, ZeroDivisionError):
        return False


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert outputs(Model, case) == case["expected"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_every_level_has_two_visible_and_two_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in CASES if case["level"] == level]
        assert sum(bool(case.get("visible")) for case in at_level) >= 2
        assert sum(not case.get("visible") for case in at_level) >= 2


def test_every_run_has_at_least_one_process():
    for case in CASES:
        added = 0
        for op, got in zip(case["ops"], case["expected"], strict=True):
            added += op == "addProcess" and got is True
            assert op not in RUNS or added > 0, case["id"]
