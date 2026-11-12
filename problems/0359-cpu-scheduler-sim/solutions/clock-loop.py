from collections import deque
from math import gcd


class _Core:
    """One CPU's record of a run: its segments, the last process it ran, its switches and the
    ticks it was busy."""

    def __init__(self) -> None:
        self.segments: list[list] = []
        self.last: str | None = None
        self.switches = 0
        self.busy = 0

    def run(self, pid: str, start: int, end: int) -> None:
        if self.segments and self.segments[-1][0] == pid and self.segments[-1][2] == start:
            self.segments[-1][2] = end
        else:
            if self.last is not None and self.last != pid:
                self.switches += 1
            self.segments.append([pid, start, end])
        self.last = pid
        self.busy += end - start


class _Run:
    """The result of the latest run: when each process first ran and finished, and the cores."""

    def __init__(self, pids: list[str], cores: int) -> None:
        self.pids = list(pids)
        self.first: dict[str, int] = {}
        self.done: dict[str, int] = {}
        self.cores = [_Core() for _ in range(cores)]
        self.migrations = 0
        self.makespan = 0

    def started(self, pid: str, time: int) -> None:
        self.first.setdefault(pid, time)

    def timelines(self) -> list[list[str]]:
        return [[f"{pid}:{start}-{end}" for pid, start, end in core.segments] for core in self.cores]


def _fraction(numerator: int, denominator: int) -> str:
    common = gcd(numerator, denominator)
    return f"{numerator // common}/{denominator // common}"


class CpuScheduler:
    """A workload of processes and the result of the latest run over it.

    First come, first served and shortest job first run each process to completion, so they jump
    from one completion to the next. Round robin, the feedback queue and the cores advance a clock
    one tick at a time and settle each tick in the order the statement fixes: the slice that ends,
    the arrivals, the process that goes back to its queue, a boost, a preemption, a dispatch and
    then a steal. One core records its segments, merging a slice that continues the one before.
    Round robin is the case of one core without stealing.
    """

    def __init__(self) -> None:
        self._pids: list[str] = []
        self._arrival: dict[str, int] = {}
        self._burst: dict[str, int] = {}
        self._run: _Run | None = None

    # Level 1
    def add_process(self, pid: str, arrival: int, burst: int) -> bool:
        if pid in self._arrival:
            return False
        self._pids.append(pid)
        self._arrival[pid] = arrival
        self._burst[pid] = burst
        return True

    def run_fcfs(self) -> list[str]:
        run = _Run(self._pids, 1)
        clock = 0
        for pid in self._by_arrival():
            start = max(clock, self._arrival[pid])
            clock = self._run_to_completion(run, pid, start)
        return self._keep(run, clock)[0]

    def run_sjf(self) -> list[str]:
        run = _Run(self._pids, 1)
        position = {pid: index for index, pid in enumerate(self._pids)}
        pending = list(self._pids)
        clock = 0
        while pending:
            ready = [pid for pid in pending if self._arrival[pid] <= clock]
            if not ready:
                clock = min(self._arrival[pid] for pid in pending)
                continue
            pid = min(ready, key=lambda p: (self._burst[p], self._arrival[p], position[p]))
            pending.remove(pid)
            clock = self._run_to_completion(run, pid, clock)
        return self._keep(run, clock)[0]

    def waiting_time(self, pid: str) -> int:
        turnaround = self.turnaround_time(pid)
        return -1 if turnaround == -1 else turnaround - self._burst[pid]

    def turnaround_time(self, pid: str) -> int:
        if self._run is None or pid not in self._run.done:
            return -1
        return self._run.done[pid] - self._arrival[pid]

    def average_waiting(self) -> str:
        return self._average(self.waiting_time)

    def average_turnaround(self) -> str:
        return self._average(self.turnaround_time)

    # Level 2
    def run_round_robin(self, quantum: int) -> list[str]:
        return self._round_robin(1, quantum, False)[0]

    def response_time(self, pid: str) -> int:
        if self._run is None or pid not in self._run.first:
            return -1
        return self._run.first[pid] - self._arrival[pid]

    def average_response(self) -> str:
        return self._average(self.response_time)

    def context_switches(self) -> int:
        if self._run is None:
            return -1
        return sum(core.switches for core in self._run.cores)

    # Level 3
    def run_mlfq(self, quanta: list[int], boost_period: int) -> list[str]:
        run = _Run(self._pids, 1)
        core = run.cores[0]
        remaining = dict(self._burst)
        arrivals = deque(self._by_arrival())
        queues: list[deque[str]] = [deque() for _ in quanta]
        level: dict[str, int] = {}
        used: dict[str, int] = {}
        running: str | None = None
        left = len(self._pids)
        clock = 0
        while True:
            demoted = None
            if running is not None:
                if remaining[running] == 0:
                    run.done[running] = clock
                    running = None
                    left -= 1
                elif used[running] == quanta[level[running]]:
                    level[running] = min(level[running] + 1, len(quanta) - 1)
                    used[running] = 0
                    demoted, running = running, None
            if left == 0:
                break
            while arrivals and self._arrival[arrivals[0]] == clock:
                pid = arrivals.popleft()
                level[pid], used[pid] = 0, 0
                queues[0].append(pid)
            if demoted is not None:
                queues[level[demoted]].append(demoted)
            if boost_period > 0 and clock > 0 and clock % boost_period == 0:
                merged: deque[str] = deque()
                for queue in queues:
                    merged.extend(queue)
                    queue.clear()
                queues[0] = merged
                for pid in [*merged, *([running] if running is not None else [])]:
                    level[pid], used[pid] = 0, 0
            if running is not None and any(queues[i] for i in range(level[running])):
                queues[level[running]].append(running)
                running = None
            if running is None:
                running = next((queue.popleft() for queue in queues if queue), None)
            if running is not None:
                run.started(running, clock)
                core.run(running, clock, clock + 1)
                remaining[running] -= 1
                used[running] += 1
            clock += 1
        return self._keep(run, clock)[0]

    # Level 4
    def run_multicore(self, cores: int, quantum: int, steal: bool) -> list[list[str]]:
        return self._round_robin(cores, quantum, steal)

    def utilization(self, core: int) -> str:
        if self._run is None or not 0 <= core < len(self._run.cores):
            return ""
        return _fraction(self._run.cores[core].busy, self._run.makespan)

    def migrations(self) -> int:
        return -1 if self._run is None else self._run.migrations

    # The clock loops
    def _round_robin(self, cores: int, quantum: int, steal: bool) -> list[list[str]]:
        run = _Run(self._pids, cores)
        remaining = dict(self._burst)
        arrivals = deque(self._by_arrival())
        queues: list[deque[str]] = [deque() for _ in range(cores)]
        running: list[str | None] = [None] * cores
        used = [0] * cores
        left = len(self._pids)
        clock = 0
        while True:
            expired: list[str | None] = [None] * cores
            for c in range(cores):
                pid = running[c]
                if pid is not None and remaining[pid] == 0:
                    run.done[pid] = clock
                    running[c] = None
                    left -= 1
                elif pid is not None and used[c] == quantum:
                    expired[c], running[c] = pid, None
            if left == 0:
                break
            while arrivals and self._arrival[arrivals[0]] == clock:
                load = [
                    len(queues[c]) + (running[c] is not None) + (expired[c] is not None)
                    for c in range(cores)
                ]
                queues[load.index(min(load))].append(arrivals.popleft())
            for c in range(cores):
                if expired[c] is not None:
                    queues[c].append(expired[c])
                if running[c] is None and queues[c]:
                    running[c], used[c] = queues[c].popleft(), 0
            for c in range(cores):
                if steal and running[c] is None:
                    victim = max(range(cores), key=lambda v: (len(queues[v]), -v))
                    if queues[victim]:
                        running[c], used[c] = queues[victim].pop(), 0
                        run.migrations += 1
            for c in range(cores):
                pid = running[c]
                if pid is not None:
                    run.started(pid, clock)
                    run.cores[c].run(pid, clock, clock + 1)
                    remaining[pid] -= 1
                    used[c] += 1
            clock += 1
        return self._keep(run, clock)

    def _run_to_completion(self, run: _Run, pid: str, start: int) -> int:
        end = start + self._burst[pid]
        run.started(pid, start)
        run.cores[0].run(pid, start, end)
        run.done[pid] = end
        return end

    def _by_arrival(self) -> list[str]:
        return sorted(self._pids, key=lambda pid: self._arrival[pid])

    def _keep(self, run: _Run, makespan: int) -> list[list[str]]:
        run.makespan = makespan
        self._run = run
        return run.timelines()

    def _average(self, metric) -> str:
        if self._run is None:
            return ""
        return _fraction(sum(metric(pid) for pid in self._run.pids), len(self._run.pids))
