import heapq
import re
from dataclasses import dataclass

ID_PATTERN = re.compile(r"[a-z0-9_]{1,20}")
NUMBER_PATTERN = re.compile(r"[0-9]{1,4}")
SCRIPT_PATTERN = re.compile(r"[SF]*")
MIN_COLUMNS = 5
MAX_DURATION = 1000
MAX_COST = 1000
UNLIMITED = -1

PENDING = "pending"
DONE = "done"
FAILED = "failed"
BLOCKED = "blocked"
SKIPPED = "skipped"
REPLACED = "replaced"

Row = list[str]


@dataclass(frozen=True)
class Task:
    id: str
    duration: int
    cost: int
    script: str
    output: str
    deps: tuple[str, ...]
    row: tuple[str, ...]


def _number(text: str, low: int, high: int) -> int | None:
    if NUMBER_PATTERN.fullmatch(text) is None:
        return None
    value = int(text)
    return value if low <= value <= high else None


def _parse(row: list[str]) -> Task | None:
    if len(row) < MIN_COLUMNS or ID_PATTERN.fullmatch(row[0]) is None:
        return None
    duration = _number(row[1], 1, MAX_DURATION)
    cost = _number(row[2], 0, MAX_COST)
    if duration is None or cost is None or SCRIPT_PATTERN.fullmatch(row[3]) is None:
        return None
    return Task(
        row[0], duration, cost, row[3], row[4], tuple(dict.fromkeys(row[5:])), tuple(row)
    )


def _cycles(tasks: dict[str, Task]) -> list[Row]:
    """One row per group of tasks that wait for each other, found from what each task can reach."""
    reach: dict[str, set[str]] = {}
    for start in tasks:
        seen: set[str] = set()
        stack = [d for d in tasks[start].deps if d in tasks]
        while stack:
            node = stack.pop()
            if node not in seen:
                seen.add(node)
                stack.extend(d for d in tasks[node].deps if d in tasks)
        reach[start] = seen
    groups: set[tuple[str, ...]] = set()
    for task_id in tasks:
        if task_id in reach[task_id]:
            groups.add(
                tuple(sorted(o for o in reach[task_id] if task_id in reach[o] and o in reach[task_id]))
            )
    return [["cycle", ",".join(group)] for group in groups]


def validate(rows: list[list[str]]) -> tuple[list[Row], dict[str, Task]]:
    """The errors of a plan, and its tasks by id when there are none."""
    parsed = [_parse(row) for row in rows]
    malformed = [["malformed-task", str(i)] for i, task in enumerate(parsed) if task is None]
    if malformed:
        return malformed, {}
    tasks_in_order = [task for task in parsed if task is not None]
    counts: dict[str, int] = {}
    for task in tasks_in_order:
        counts[task.id] = counts.get(task.id, 0) + 1
    duplicates = sorted([["duplicate-id", i] for i, n in counts.items() if n > 1])
    if duplicates:
        return duplicates, {}
    tasks = {task.id: task for task in tasks_in_order}
    unknown = [
        ["unknown-dependency", f"{task.id}>{dep}"]
        for task in tasks_in_order
        for dep in task.deps
        if dep not in tasks
    ]
    errors = sorted(_cycles(tasks) + unknown)
    return errors, ({} if errors else tasks)


def _topological(tasks: dict[str, Task]) -> list[str]:
    waiting = {t: len(task.deps) for t, task in tasks.items()}
    dependents: dict[str, list[str]] = {t: [] for t in tasks}
    for t, task in tasks.items():
        for dep in task.deps:
            dependents[dep].append(t)
    ready = [t for t, n in waiting.items() if n == 0]
    heapq.heapify(ready)
    order: list[str] = []
    while ready:
        current = heapq.heappop(ready)
        order.append(current)
        for follower in dependents[current]:
            waiting[follower] -= 1
            if waiting[follower] == 0:
                heapq.heappush(ready, follower)
    return order


def _succeeds(script: str, attempt: int) -> bool:
    if script == "":
        return True
    return script[min(attempt, len(script)) - 1] == "S"


class _Execution:
    """One run: waves of the tasks that are ready, in order of id, at most `cap` at a time."""

    def __init__(
        self,
        tasks: dict[str, Task],
        replans: dict[str, list[list[str]]],
        cap: int,
        max_retries: int,
        max_cost: int,
        max_steps: int,
    ) -> None:
        self.tasks = dict(tasks)
        self.replans = replans
        self.cap = cap
        self.attempts_allowed = 1 + max_retries
        self.max_cost = max_cost
        self.max_steps = max_steps
        self.status = {t: PENDING for t in tasks}
        self.attempts = {t: 0 for t in tasks}
        self.span: dict[str, tuple[int, int]] = {}
        self.seen = set(tasks)
        self.tried: set[str] = set()
        self.log: list[Row] = []
        self.cost = 0
        self.steps = 0
        self.time = 0
        self.wave = 0
        self.stopped = "none"
        self.applied = 0
        self.rejected = 0

    def execute(self) -> None:
        while self.stopped == "none":
            ready = sorted(
                t
                for t, s in self.status.items()
                if s == PENDING and all(self.status[d] == DONE for d in self.tasks[t].deps)
            )
            if not ready:
                break
            self.wave += 1
            batch = ready[: self.cap]
            self.run_wave(batch)
            if self.stopped == "none":
                self.replan_after(batch)
        self.settle()

    def denial(self, task: Task) -> str:
        if self.max_cost != UNLIMITED and self.cost + task.cost > self.max_cost:
            return "cost"
        if self.max_steps != UNLIMITED and self.steps + 1 > self.max_steps:
            return "steps"
        return "none"

    def run_wave(self, batch: list[str]) -> None:
        start = self.time
        alive = list(batch)
        while alive and self.stopped == "none":
            undecided: list[str] = []
            for t in alive:
                task = self.tasks[t]
                reason = self.denial(task)
                if reason != "none":
                    self.stopped = reason
                    break
                self.cost += task.cost
                self.steps += 1
                self.attempts[t] += 1
                if _succeeds(task.script, self.attempts[t]):
                    self.status[t] = DONE
                elif self.attempts[t] == self.attempts_allowed:
                    self.status[t] = FAILED
                else:
                    undecided.append(t)
            else:
                alive = undecided
                continue
            break
        ends = []
        for t in batch:
            if self.attempts[t] > 0:
                if self.status[t] == PENDING:
                    self.status[t] = FAILED
                end = start + self.attempts[t] * self.tasks[t].duration
                self.span[t] = (start, end)
                ends.append(end)
        if ends:
            self.time = max(ends)

    def replan_after(self, batch: list[str]) -> None:
        for t in sorted(batch):
            if self.status[t] == FAILED and t in self.replans and t not in self.tried:
                self.tried.add(t)
                if self.try_replan(t):
                    return

    def try_replan(self, failed: str) -> bool:
        new_rows = self.replans[failed]
        kept_rows = [list(self.tasks[t].row) for t in self.tasks if self.status[t] == DONE]
        errors, merged = validate(kept_rows + new_rows)
        if not errors:
            new_ids = [row[0] for row in new_rows]
            errors = sorted(
                ["duplicate-id", i] for i in new_ids if i in self.seen and self.status.get(i) != DONE
            )
        if errors:
            self.rejected += 1
            self.log.append([str(self.wave), failed, "rejected", f"{errors[0][0]}:{errors[0][1]}"])
            return False
        removed = [t for t, s in self.status.items() if s == PENDING]
        for t in removed:
            self.status[t] = REPLACED
        added = [t for t in merged if t not in self.seen]
        for t in added:
            self.tasks[t] = merged[t]
            self.status[t] = PENDING
            self.attempts[t] = 0
        self.seen.update(added)
        self.applied += 1
        self.log.append(
            [str(self.wave), failed, "applied", f"removed {len(removed)}, added {len(added)}"]
        )
        return True

    def settle(self) -> None:
        """Tasks that never ran are blocked when a task they wait for did not finish, else skipped."""
        for t in _topological({t: self.tasks[t] for t in self.tasks}):
            if self.status[t] == PENDING:
                lost = any(self.status[d] in (FAILED, BLOCKED) for d in self.tasks[t].deps)
                self.status[t] = BLOCKED if lost else SKIPPED

    def rows(self) -> list[Row]:
        result = []
        for t in sorted(self.seen):
            start, end = self.span.get(t, (None, None))
            result.append(
                [
                    t,
                    self.status[t],
                    str(self.attempts[t]),
                    "" if start is None else str(start),
                    "" if end is None else str(end),
                ]
            )
        return result

    def report(self) -> list[Row]:
        def ids(status: str) -> list[str]:
            return sorted(t for t, s in self.status.items() if s == status)

        return [
            ["stopped", self.stopped],
            ["spent", str(self.cost), str(self.steps), str(self.time)],
            ["done", *ids(DONE)],
            ["failed", *ids(FAILED)],
            ["blocked", *ids(BLOCKED)],
            ["skipped", *ids(SKIPPED)],
            ["replaced", *ids(REPLACED)],
            ["replans", str(self.applied), str(self.rejected)],
            ["results", *[f"{t}={self.tasks[t].output}" for t in ids(DONE)]],
        ]


class PlanRunner:
    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._replans: dict[str, list[list[str]]] = {}
        self._max_cost = UNLIMITED
        self._max_steps = UNLIMITED
        self._last: _Execution | None = None

    # --- level 1
    def set_plan(self, tasks: list[list[str]]) -> list[list[str]]:
        errors, parsed = validate(tasks)
        if not errors:
            self._tasks = parsed
        return errors

    def order(self) -> list[str]:
        return _topological(self._tasks)

    # --- level 2
    def _waves(self, cap: int) -> list[list[tuple[str, int, int]]]:
        done: set[str] = set()
        waves: list[list[tuple[str, int, int]]] = []
        time = 0
        while len(done) < len(self._tasks):
            ready = sorted(
                t for t, task in self._tasks.items() if t not in done and set(task.deps) <= done
            )[:cap]
            wave = [(t, time, time + self._tasks[t].duration) for t in ready]
            waves.append(wave)
            done.update(ready)
            time = max(end for _, _, end in wave)
        return waves

    def timeline(self, cap: int) -> list[list[str]]:
        return [
            [str(number), t, str(start), str(end)]
            for number, wave in enumerate(self._waves(cap), start=1)
            for t, start, end in wave
        ]

    def makespan(self, cap: int) -> int:
        waves = self._waves(cap)
        return max(end for _, _, end in waves[-1]) if waves else 0

    def critical_path(self) -> list[str]:
        best: dict[str, tuple[int, list[str]]] = {}
        for t in _topological(self._tasks):
            task = self._tasks[t]
            before = [best[d] for d in task.deps]
            if before:
                total, chain = min(before, key=lambda b: (-b[0], b[1]))
            else:
                total, chain = 0, []
            best[t] = (total + task.duration, [*chain, t])
        if not best:
            return []
        return min(best.values(), key=lambda b: (-b[0], b[1]))[1]

    # --- level 3
    def set_replan(self, failed_id: str, tasks: list[list[str]]) -> bool:
        new = failed_id not in self._replans
        self._replans[failed_id] = [list(row) for row in tasks]
        return new

    def run(self, cap: int, max_retries: int) -> list[list[str]]:
        execution = _Execution(
            self._tasks, self._replans, cap, max_retries, self._max_cost, self._max_steps
        )
        execution.execute()
        self._last = execution
        return execution.rows()

    def replan_log(self) -> list[list[str]]:
        return [] if self._last is None else list(self._last.log)

    # --- level 4
    def set_budget(self, max_cost: int, max_steps: int) -> None:
        self._max_cost = max_cost
        self._max_steps = max_steps

    def report(self) -> list[list[str]]:
        return [] if self._last is None else self._last.report()
