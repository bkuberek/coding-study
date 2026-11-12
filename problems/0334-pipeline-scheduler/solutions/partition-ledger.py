import heapq

DONE = "done"
FAILED = "failed"
MISSING = "missing"

Partition = tuple[str, int]


class PipelineScheduler:
    """Tasks and their dependencies form a graph. The order counts the unlisted dependencies of
    each task and keeps the ready names in a heap, so that the smallest ready name goes next.

    A ledger keyed by (task, day) records each partition's state. Every write gets a number, and
    the partition remembers the number of each input it read, which is all it takes to tell a
    stale partition and to find what a backfill must rerun. Runs and backfills share one attempt
    loop, which follows the scripted outcomes and the task's retries.
    """

    def __init__(self) -> None:
        self._deps: dict[str, list[str]] = {}
        self._windows: dict[tuple[str, str], int] = {}
        self._retries: dict[str, int] = {}
        self._scripts: dict[Partition, list[str]] = {}
        self._state: dict[Partition, str] = {}
        self._write: dict[Partition, int] = {}
        self._read: dict[Partition, dict[Partition, int]] = {}
        self._writes = 0

    # Level 1
    def add_task(self, name: str, deps: list[str]) -> bool:
        if name in self._deps:
            return False
        self._deps[name] = list(dict.fromkeys(deps))
        return True

    def validate(self) -> list[list[str]]:
        problems = [
            ["unknown-dependency", task, dep]
            for task, deps in self._deps.items()
            for dep in deps
            if dep not in self._deps
        ]
        order = self._kahn()
        if len(order) < len(self._deps):
            left = set(self._deps) - set(order)
            problems += [["cycle", task] for task in left if self._reaches_itself(task)]
        return sorted(problems)

    def run_order(self) -> list[str]:
        if self.validate():
            return []
        return self._kahn()

    # Level 2
    def set_window(self, task: str, dep: str, days: int) -> bool:
        if dep not in self._deps.get(task, []):
            return False
        self._windows[(task, dep)] = days
        return True

    def mark_done(self, task: str, day: int) -> None:
        self._store(task, day)

    def runnable(self, day: int) -> list[str]:
        return sorted(
            task
            for task in self._deps
            if self._state.get((task, day)) != DONE and self._inputs_done(task, day)
        )

    # Level 3
    def set_retries(self, task: str, retries: int) -> None:
        self._retries[task] = retries

    def script(self, task: str, day: int, outcomes: list[str]) -> None:
        self._scripts[(task, day)] = list(outcomes)

    def run(self, day: int) -> list[list[str]]:
        rows = []
        for task in self.run_order():
            if not self._inputs_done(task, day):
                rows.append([task, "skipped", "0"])
                continue
            attempts, succeeded = self._attempt(task, day)
            rows.append([task, "success" if succeeded else "failed", str(attempts)])
        return rows

    def status(self, task: str, day: int) -> str:
        return self._state.get((task, day), MISSING)

    # Level 4
    def stale(self, day: int) -> list[str]:
        return sorted(task for task in self._deps if self._is_stale((task, day)))

    def plan(self, task: str, from_day: int, to_day: int) -> list[list[str]]:
        return [[str(day), name] for name, day in self._plan(task, from_day, to_day)]

    def backfill(self, task: str, from_day: int, to_day: int, cap: int) -> list[list[str]]:
        plan = self._plan(task, from_day, to_day)
        planned = set(plan)
        outcome: dict[Partition, tuple[int, str, int]] = {}
        round_number = 0
        while len(outcome) < len(plan):
            round_number += 1
            # Inputs come before their users in plan order, so one pass settles every skip.
            for p in plan:
                if p not in outcome and self._blocked(p, planned, outcome):
                    outcome[p] = (round_number, "skipped", 0)
            ready = [
                p
                for p in plan
                if p not in outcome
                and all(
                    outcome.get(i, (0, "", 0))[1] == "success"
                    for i in self._inputs(*p)
                    if i in planned
                )
            ][:cap]
            for p in ready:
                attempts, succeeded = self._attempt(*p)
                outcome[p] = (round_number, "success" if succeeded else "failed", attempts)
        rank = {name: i for i, name in enumerate(self.run_order())}
        decided = sorted(
            outcome.items(), key=lambda item: (item[1][0], item[0][1], rank[item[0][0]])
        )
        return [[str(r), str(day), name, result, str(n)] for (name, day), (r, result, n) in decided]

    # The graph
    def _kahn(self) -> list[str]:
        waiting = {
            task: sum(dep in self._deps for dep in deps) for task, deps in self._deps.items()
        }
        users: dict[str, list[str]] = {task: [] for task in self._deps}
        for task, deps in self._deps.items():
            for dep in deps:
                if dep in users:
                    users[dep].append(task)
        heap = [task for task, count in waiting.items() if count == 0]
        heapq.heapify(heap)
        order = []
        while heap:
            task = heapq.heappop(heap)
            order.append(task)
            for user in users[task]:
                waiting[user] -= 1
                if waiting[user] == 0:
                    heapq.heappush(heap, user)
        return order

    def _reaches_itself(self, start: str) -> bool:
        seen: set[str] = set()
        stack = [dep for dep in self._deps[start] if dep in self._deps]
        while stack:
            task = stack.pop()
            if task == start:
                return True
            if task not in seen:
                seen.add(task)
                stack += [dep for dep in self._deps[task] if dep in self._deps]
        return False

    # The partitions
    def _inputs(self, task: str, day: int) -> list[Partition]:
        return [
            (dep, d)
            for dep in self._deps[task]
            for d in range(max(0, day - self._windows.get((task, dep), 1) + 1), day + 1)
        ]

    def _current(self, p: Partition) -> int:
        return self._write[p] if self._state.get(p) == DONE else 0

    def _inputs_done(self, task: str, day: int) -> bool:
        return all(self._state.get(i) == DONE for i in self._inputs(task, day))

    def _store(self, task: str, day: int) -> None:
        self._writes += 1
        p = (task, day)
        self._state[p] = DONE
        self._write[p] = self._writes
        self._read[p] = {i: self._current(i) for i in self._inputs(task, day)}

    def _attempt(self, task: str, day: int) -> tuple[int, bool]:
        script = self._scripts.get((task, day), [])
        for attempt in range(1, self._retries.get(task, 0) + 2):
            if (script.pop(0) if script else "ok") == "ok":
                self._store(task, day)
                return attempt, True
        self._state[(task, day)] = FAILED
        return self._retries.get(task, 0) + 1, False

    def _is_stale(self, p: Partition) -> bool:
        if self._state.get(p) != DONE:
            return False
        return any(self._current(i) != seen for i, seen in self._read[p].items())

    def _plan(self, task: str, from_day: int, to_day: int) -> list[Partition]:
        users: dict[str, list[str]] = {name: [] for name in self._deps}
        for name, deps in self._deps.items():
            for dep in deps:
                users[dep].append(name)
        planned = {(task, day) for day in range(from_day, to_day + 1)}
        frontier = list(planned)
        while frontier:
            upstream, day = frontier.pop()
            for user in users[upstream]:
                for later in range(day, day + self._windows.get((user, upstream), 1)):
                    p = (user, later)
                    if self._state.get(p) == DONE and p not in planned:
                        planned.add(p)
                        frontier.append(p)
        rank = {name: i for i, name in enumerate(self.run_order())}
        return sorted(planned, key=lambda p: (p[1], rank[p[0]]))

    def _blocked(self, p: Partition, planned: set[Partition], outcome: dict) -> bool:
        for i in self._inputs(*p):
            if i in planned:
                if i in outcome and outcome[i][1] != "success":
                    return True
            elif self._state.get(i) != DONE:
                return True
        return False
