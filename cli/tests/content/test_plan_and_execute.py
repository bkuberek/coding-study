"""plan-and-execute promises that its hidden cases catch the classic mistakes of running a plan that
a model wrote: a plan that is trusted before it is checked, a cycle that is reported for the tasks
that only wait for it, an order that is only sorted, waves that start a task early or ignore the
cap, a retry count that is off by one, a failure that does not block what depends on it, a replan
that is not checked like a plan or that is tried more than once, and a budget that is checked after
the spending, charged task by task or reported with the wrong status. These tests replay every case
against a model of the runner written from the statement, which must give every expected output,
and against that model with one mistake planted at a time, which some hidden case must fail. A
mistake that crashes fails its case, as a thrown exception does in the grader. The model finds
cycles with a strongly connected components pass and the critical path by listing every chain, a
different route from the reference solutions."""

import itertools
import json
import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any, NamedTuple

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0329-plan-and-execute"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
SCRIPTED_CASES = [case for case in CASES if "ops" in case]
HIDDEN_CASES = [case for case in SCRIPTED_CASES if not case.get("visible", False)]

Row = list[str]


class Task(NamedTuple):
    id: str
    duration: int
    cost: int
    script: str
    output: str
    deps: tuple[str, ...]
    row: tuple[str, ...]


class Outcome:
    """What one run left behind."""

    def __init__(self) -> None:
        self.status: dict[str, str] = {}
        self.attempts: dict[str, int] = {}
        self.span: dict[str, tuple[int, int]] = {}
        self.tasks: dict[str, Task] = {}
        self.log: list[Row] = []
        self.applied = 0
        self.rejected = 0
        self.cost = 0
        self.steps = 0
        self.clock = 0
        self.stopped = "none"


class Model:
    """The runner as the statement words it. Plans are lists of tasks, every question is answered
    by scanning them, and a run is played attempt by attempt. Each mistake below overrides one
    hook."""

    ID = re.compile(r"[a-z0-9_]{1,20}")
    DIGITS = re.compile(r"[0-9]{1,4}")
    SCRIPT = re.compile(r"[SF]*")
    MIN_COLUMNS = 5
    MAX_DURATION = 1000
    MIN_DURATION = 1
    MAX_COST = 1000

    def __init__(self) -> None:
        self.plan: list[Task] = []
        self.replans: dict[str, list[list[str]]] = {}
        self.max_cost = -1
        self.max_steps = -1
        self.last: Outcome | None = None

    # ------------------------------------------------------------------ reading rows
    def number(self, text: str, low: int, high: int) -> int | None:
        if not self.DIGITS.fullmatch(text):
            return None
        value = int(text)
        return value if low <= value <= high else None

    def read(self, row: list[str]) -> Task | None:
        if len(row) < self.MIN_COLUMNS or not self.ID.fullmatch(row[0]):
            return None
        duration = self.number(row[1], self.MIN_DURATION, self.MAX_DURATION)
        cost = self.number(row[2], 0, self.MAX_COST)
        if duration is None or cost is None or not self.SCRIPT.fullmatch(row[3]):
            return None
        return Task(row[0], duration, cost, row[3], row[4], self.dependencies(row[5:]), tuple(row))

    def dependencies(self, ids: list[str]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(ids))

    def sort_errors(self, rows: list[Row]) -> list[Row]:
        return sorted(rows)

    def malformed_rows(self, rows: list[list[str]], read: list[Task | None]) -> list[Row]:
        return [["malformed-task", str(i)] for i, task in enumerate(read) if task is None]

    def duplicate_rows(self, tasks: list[Task]) -> list[Row]:
        ids = [t.id for t in tasks]
        return [["duplicate-id", i] for i in sorted({i for i in ids if ids.count(i) > 1})]

    def unknown_rows(self, tasks: list[Task]) -> list[Row]:
        known = {t.id for t in tasks}
        return [
            ["unknown-dependency", f"{t.id}>{d}"] for t in tasks for d in t.deps if d not in known
        ]

    def cycle_rows(self, tasks: list[Task]) -> list[Row]:
        graph = {t.id: [d for d in t.deps if d in {u.id for u in tasks}] for t in tasks}
        return [["cycle", ",".join(sorted(group))] for group in self.cyclic_groups(graph)]

    def cyclic_groups(self, graph: dict[str, list[str]]) -> list[list[str]]:
        """Strongly connected components with a cycle in them, by Tarjan's pass."""
        index: dict[str, int] = {}
        low: dict[str, int] = {}
        stack: list[str] = []
        on_stack: set[str] = set()
        groups: list[list[str]] = []
        counter = itertools.count()

        def visit(node: str) -> None:
            index[node] = low[node] = next(counter)
            stack.append(node)
            on_stack.add(node)
            for follower in graph[node]:
                if follower not in index:
                    visit(follower)
                    low[node] = min(low[node], low[follower])
                elif follower in on_stack:
                    low[node] = min(low[node], index[follower])
            if low[node] == index[node]:
                group = []
                while True:
                    member = stack.pop()
                    on_stack.discard(member)
                    group.append(member)
                    if member == node:
                        break
                if len(group) > 1 or node in graph[node]:
                    groups.append(group)

        for node in graph:
            if node not in index:
                visit(node)
        return groups

    def gates(self) -> bool:
        """Whether a stage that finds something ends the check."""
        return True

    def validate(self, rows: list[list[str]]) -> tuple[list[Row], list[Task]]:
        read = [self.read(row) for row in rows]
        tasks = [t for t in read if t is not None]
        stages = [
            self.malformed_rows(rows, read),
            self.duplicate_rows(tasks),
            self.unknown_rows(tasks) + self.cycle_rows(tasks),
        ]
        errors: list[Row] = []
        for found in stages:
            if found and self.gates():
                return self.sort_stage(found, stages.index(found)), []
            errors += found
        return (self.sort_errors(errors), []) if errors else ([], tasks)

    def sort_stage(self, found: list[Row], stage: int) -> list[Row]:
        return found if stage == 0 else self.sort_errors(found)

    # ------------------------------------------------------------------ level 1
    def set_plan(self, tasks: list[list[str]]) -> list[Row]:
        errors, parsed = self.validate(tasks)
        if not errors:
            self.plan = parsed
        return errors

    def pick(self, ready: list[str]) -> str:
        return min(ready)

    def sequence(self, tasks: list[Task]) -> list[str]:
        placed: list[str] = []
        left = {t.id: t for t in tasks}
        while left:
            ready = [i for i, t in left.items() if all(d in placed for d in t.deps)]
            if not ready:
                break
            chosen = self.pick(ready)
            placed.append(chosen)
            del left[chosen]
        return placed

    def order(self) -> list[str]:
        return self.sequence(self.plan)

    # ------------------------------------------------------------------ level 2
    def cap_for(self, cap: int) -> int:
        return cap

    def wave_members(self, ready: list[str], cap: int) -> list[str]:
        return sorted(ready)[: self.cap_for(cap)]

    def wave_end(self, ends: list[int]) -> int:
        return max(ends)

    def first_wave_number(self) -> int:
        return 1

    def waves(self, cap: int) -> list[list[tuple[str, int, int]]]:
        by_id = {t.id: t for t in self.plan}
        done: set[str] = set()
        clock = 0
        result: list[list[tuple[str, int, int]]] = []
        while len(done) < len(by_id):
            ready = [i for i, t in by_id.items() if i not in done and set(t.deps) <= done]
            members = self.wave_members(ready, cap)
            wave = [(i, clock, 0) for i in members]
            wave = [(i, s, s + by_id[i].duration) for i, s, _ in wave]
            result.append(wave)
            done.update(members)
            clock = self.wave_end([end for _, _, end in wave])
        return result

    def timeline(self, cap: int) -> list[Row]:
        number = self.first_wave_number()
        rows: list[Row] = []
        for offset, wave in enumerate(self.waves(cap)):
            rows += [[str(number + offset), i, str(s), str(e)] for i, s, e in wave]
        return rows

    def makespan(self, cap: int) -> int:
        waves = self.waves(cap)
        return self.wave_end([end for _, _, end in waves[-1]]) if waves else 0

    def chain_score(self, chain: list[str], by_id: dict[str, Task]) -> tuple[Any, ...]:
        return (-sum(by_id[i].duration for i in chain), chain)

    def chains_to(self, task_id: str, by_id: dict[str, Task]) -> list[list[str]]:
        deps = by_id[task_id].deps
        if not deps:
            return [[task_id]]
        return [[*chain, task_id] for d in deps for chain in self.chains_to(d, by_id)]

    def critical_path(self) -> list[str]:
        by_id = {t.id: t for t in self.plan}
        every = [chain for i in by_id for chain in self.chains_to(i, by_id)]
        return min(every, key=lambda chain: self.chain_score(chain, by_id)) if every else []

    # ------------------------------------------------------------------ level 3
    def set_replan(self, failed_id: str, tasks: list[list[str]]) -> bool:
        fresh = failed_id not in self.replans
        self.replans[failed_id] = tasks
        return fresh

    def allowed_attempts(self, max_retries: int) -> int:
        return 1 + max_retries

    def letter(self, script: str, attempt: int) -> str:
        if script == "":
            return "S"
        return script[min(attempt, len(script)) - 1]

    def span_end(self, start: int, attempts: int, duration: int) -> int:
        return start + attempts * duration

    def replan_check(self, out: Outcome, rows: list[list[str]]) -> list[Row]:
        kept = [list(out.tasks[i].row) for i in out.tasks if out.status[i] == "done"]
        errors, _ = self.validate(kept + rows)
        if errors:
            return errors
        return sorted(
            ["duplicate-id", r[0]]
            for r in rows
            if r[0] in out.status and out.status[r[0]] != "done"
        )

    def replaced_by_replan(self, out: Outcome) -> list[str]:
        return [i for i, s in out.status.items() if s == "pending"]

    def replan_wave(self, out: Outcome, wave: int, members: list[str], used: set[str]) -> None:
        for failed in sorted(members):
            if out.status[failed] != "failed" or failed not in self.replans:
                continue
            if failed in used and self.once_only():
                continue
            used.add(failed)
            rows = self.replans[failed]
            errors = self.replan_check(out, rows)
            if errors:
                out.rejected += 1
                out.log.append(
                    [self.wave_label(wave), failed, "rejected", f"{errors[0][0]}:{errors[0][1]}"]
                )
                if self.rejection_ends_turn():
                    return
                continue
            gone = self.replaced_by_replan(out)
            for i in gone:
                out.status[i] = "replaced"
            added = [t for t in (self.read(r) for r in rows) if t is not None]
            for task in added:
                out.tasks[task.id] = task
                out.status[task.id] = "pending"
                out.attempts[task.id] = 0
            out.applied += 1
            out.log.append(
                [
                    self.wave_label(wave),
                    failed,
                    "applied",
                    f"removed {len(gone)}, added {self.added_count(added)}",
                ]
            )
            if self.one_per_wave():
                return

    def once_only(self) -> bool:
        return True

    def one_per_wave(self) -> bool:
        return True

    def rejection_ends_turn(self) -> bool:
        return False

    def wave_label(self, wave: int) -> str:
        return str(wave)

    def added_count(self, added: list[Task]) -> int:
        return len(added)

    def fresh_outcome(self) -> Outcome:
        out = Outcome()
        for task in self.plan:
            out.tasks[task.id] = task
            out.status[task.id] = "pending"
            out.attempts[task.id] = 0
        return out

    def ready_ids(self, out: Outcome) -> list[str]:
        return [
            i
            for i, s in out.status.items()
            if s == "pending" and all(out.status[d] == "done" for d in out.tasks[i].deps)
        ]

    def refusal(self, out: Outcome, task: Task) -> str:
        if self.max_cost != -1 and self.over_cost(out.cost, task.cost, self.max_cost):
            return "cost"
        if self.max_steps != -1 and out.steps + 1 > self.max_steps:
            return "steps"
        return "none"

    def over_cost(self, spent: int, cost: int, limit: int) -> bool:
        return spent + cost > limit

    def run_wave(self, out: Outcome, members: list[str], max_retries: int) -> None:
        start = out.clock
        undecided = list(members)
        round_number = 0
        while undecided and out.stopped == "none":
            round_number += 1
            carry: list[str] = []
            for i in undecided:
                task = out.tasks[i]
                why = self.refusal(out, task)
                if why != "none":
                    out.stopped = why
                    break
                out.cost += task.cost
                out.steps += 1
                out.attempts[i] += 1
                if self.letter(task.script, out.attempts[i]) == "S":
                    out.status[i] = "done"
                elif out.attempts[i] >= self.allowed_attempts(max_retries):
                    out.status[i] = "failed"
                else:
                    carry.append(i)
            undecided = carry
        ends = []
        for i in members:
            if out.attempts[i] > 0:
                if out.status[i] == "pending":
                    out.status[i] = self.undecided_status()
                end = self.span_end(start, out.attempts[i], out.tasks[i].duration)
                out.span[i] = (start, end)
                ends.append(end)
        if ends:
            out.clock = self.clock_after(ends, out)

    def undecided_status(self) -> str:
        return "failed"

    def clock_after(self, ends: list[int], out: Outcome) -> int:
        return max(ends)

    def settle(self, out: Outcome) -> None:
        for i in self.sequence(list(out.tasks.values())):
            if out.status[i] == "pending":
                out.status[i] = self.leftover_status(out, i)

    def leftover_status(self, out: Outcome, task_id: str) -> str:
        lost = any(out.status[d] in ("failed", "blocked") for d in out.tasks[task_id].deps)
        return "blocked" if lost else "skipped"

    def execute(self, cap: int, max_retries: int) -> Outcome:
        out = self.fresh_outcome()
        used: set[str] = set()
        wave = 0
        while out.stopped == "none":
            ready = self.ready_ids(out)
            if not ready:
                break
            wave += 1
            members = self.wave_members(ready, cap)
            self.run_wave(out, members, max_retries)
            if out.stopped == "none" or self.replans_after_stop():
                self.replan_wave(out, wave, members, used)
        self.settle(out)
        return out

    def replans_after_stop(self) -> bool:
        return False

    def run(self, cap: int, max_retries: int) -> list[Row]:
        out = self.execute(cap, max_retries)
        self.last = out
        return self.run_rows(out)

    def run_rows(self, out: Outcome) -> list[Row]:
        rows = []
        for i in sorted(out.status):
            start, end = out.span.get(i, (None, None))
            rows.append(
                [
                    i,
                    out.status[i],
                    str(out.attempts[i]),
                    "" if start is None else str(start),
                    "" if end is None else str(end),
                ]
            )
        return rows

    def replan_log(self) -> list[Row]:
        return [] if self.last is None else list(self.last.log)

    # ------------------------------------------------------------------ level 4
    def set_budget(self, max_cost: int, max_steps: int) -> None:
        self.max_cost = max_cost
        self.max_steps = max_steps

    def ids_with(self, out: Outcome, status: str) -> list[str]:
        return sorted(i for i, s in out.status.items() if s == status)

    def result_ids(self, out: Outcome) -> list[str]:
        return self.ids_with(out, "done")

    def list_row(self, name: str, ids: list[str]) -> Row:
        return [name, *ids]

    def counts_row(self, out: Outcome) -> Row:
        return ["replans", str(out.applied), str(out.rejected)]

    def spent_row(self, out: Outcome) -> Row:
        return ["spent", str(out.cost), str(out.steps), str(out.clock)]

    def report(self) -> list[Row]:
        out = self.last
        if out is None:
            return []
        return [
            ["stopped", out.stopped],
            self.spent_row(out),
            self.list_row("done", self.ids_with(out, "done")),
            self.list_row("failed", self.ids_with(out, "failed")),
            self.list_row("blocked", self.ids_with(out, "blocked")),
            self.list_row("skipped", self.ids_with(out, "skipped")),
            self.list_row("replaced", self.ids_with(out, "replaced")),
            self.counts_row(out),
            ["results", *[f"{i}={out.tasks[i].output}" for i in self.result_ids(out)]],
        ]


# ------------------------------------------------------------------ level 1 mistakes
class StagesDoNotGate(Model):
    """Reports every stage together."""

    def gates(self) -> bool:
        return False


class MalformedRowsAreListedFromOne(Model):
    """Counts the rows of a plan from 1."""

    def malformed_rows(self, rows: list[list[str]], read: list[Task | None]) -> list[Row]:
        return [["malformed-task", str(i + 1)] for i, task in enumerate(read) if task is None]


class DuplicatesAreListedEachTime(Model):
    """Lists a duplicate once for every row that has it."""

    def duplicate_rows(self, tasks: list[Task]) -> list[Row]:
        ids = [t.id for t in tasks]
        return [["duplicate-id", i] for i in ids if ids.count(i) > 1]


class UnknownDependencyHasNoTask(Model):
    """Writes only the missing id."""

    def unknown_rows(self, tasks: list[Task]) -> list[Row]:
        known = {t.id for t in tasks}
        return [["unknown-dependency", d] for t in tasks for d in t.deps if d not in known]


class CycleIsListedPerTask(Model):
    """Writes one row for every task on a cycle."""

    def cycle_rows(self, tasks: list[Task]) -> list[Row]:
        graph = {t.id: [d for d in t.deps if d in {u.id for u in tasks}] for t in tasks}
        return [["cycle", member] for g in self.cyclic_groups(graph) for member in sorted(g)]


class CycleIncludesWhatWaitsForIt(Model):
    """Reports every task that cannot be placed."""

    def cycle_rows(self, tasks: list[Task]) -> list[Row]:
        known = {t.id for t in tasks}
        trimmed = [t._replace(deps=tuple(d for d in t.deps if d in known)) for t in tasks]
        stuck = sorted({t.id for t in trimmed} - set(self.sequence(trimmed)))
        return [["cycle", ",".join(stuck)]] if stuck else []


class SelfDependencyIsFine(Model):
    """Does not see a task that waits for itself."""

    def cycle_rows(self, tasks: list[Task]) -> list[Row]:
        known = {t.id for t in tasks}
        graph = {t.id: [d for d in t.deps if d in known and d != t.id] for t in tasks}
        return [["cycle", ",".join(sorted(g))] for g in self.cyclic_groups(graph)]


class CycleIdsKeepTheirOrder(Model):
    """Writes the ids of a cycle in the order they were found."""

    def cycle_rows(self, tasks: list[Task]) -> list[Row]:
        known = {t.id for t in tasks}
        graph = {t.id: [d for d in t.deps if d in known] for t in tasks}
        return [["cycle", ",".join(g)] for g in self.cyclic_groups(graph)]


class ErrorsAreNotSorted(Model):
    """Lists the errors of a stage as they were found."""

    def sort_errors(self, rows: list[Row]) -> list[Row]:
        return rows


class BadPlanIsInstalled(Model):
    """Installs a plan with errors."""

    def set_plan(self, tasks: list[list[str]]) -> list[Row]:
        errors, _ = self.validate(tasks)
        self.plan = [t for t in (self.read(r) for r in tasks) if t is not None]
        return errors


class UpperCaseIdsAreFine(Model):
    """Accepts capitals in an id."""

    ID = re.compile(r"[A-Za-z0-9_]{1,20}")


class LongIdsAreFine(Model):
    """Accepts an id of any length."""

    ID = re.compile(r"[a-z0-9_]+")


class ZeroDurationIsFine(Model):
    """Accepts a duration of 0."""

    MIN_DURATION = 0


class DurationHasNoUpperLimit(Model):
    """Accepts any duration of four digits."""

    MAX_DURATION = 9999


class CostHasNoUpperLimit(Model):
    """Accepts any cost of four digits."""

    MAX_COST = 9999


class NumbersMayHaveManyDigits(Model):
    """Accepts a number of any length."""

    DIGITS = re.compile(r"[0-9]+")


class ScriptMayBeLowerCase(Model):
    """Accepts s and f in a script."""

    SCRIPT = re.compile(r"[SFsf]*")


class OutputColumnIsOptional(Model):
    """Accepts a row of four columns."""

    MIN_COLUMNS = 4

    def read(self, row: list[str]) -> Task | None:
        return super().read([*row, ""] if len(row) == 4 else row)


class RepeatedDependencyCountsTwice(Model):
    """Keeps a dependency that is listed twice."""

    def dependencies(self, ids: list[str]) -> tuple[str, ...]:
        return tuple(ids)

    def sequence(self, tasks: list[Task]) -> list[str]:
        waiting = {t.id: list(t.deps) for t in tasks}
        placed: list[str] = []
        while waiting:
            free = [i for i, deps in waiting.items() if not deps]
            if not free:
                break
            chosen = min(free)
            placed.append(chosen)
            del waiting[chosen]
            for deps in waiting.values():
                if chosen in deps:
                    deps.remove(chosen)
        return placed


class OrderIsJustSorted(Model):
    """Sorts the ids and ignores the dependencies."""

    def sequence(self, tasks: list[Task]) -> list[str]:
        return sorted(t.id for t in tasks)


class OrderTakesTheLargestId(Model):
    """Takes the largest ready id."""

    def pick(self, ready: list[str]) -> str:
        return max(ready)


class OrderTakesTheOldestRow(Model):
    """Takes the first ready task in the order the rows were given."""

    def pick(self, ready: list[str]) -> str:
        position = {t.id: n for n, t in enumerate(self.plan)}
        return min(ready, key=lambda i: position.get(i, 0))


class OrderCompareIdsAsNumbers(Model):
    """Compares ids that look like numbers as numbers."""

    def pick(self, ready: list[str]) -> str:
        return min(ready, key=lambda i: (0, int(i), i) if i.isdigit() else (1, 0, i))


class EmptyPlanIsAnError(Model):
    """Refuses a plan with no task."""

    def set_plan(self, tasks: list[list[str]]) -> list[Row]:
        return [["malformed-task", "0"]] if not tasks else super().set_plan(tasks)


# ------------------------------------------------------------------ level 2 mistakes
class CapIsIgnored(Model):
    """Runs every ready task."""

    def cap_for(self, cap: int) -> int:
        return 1000


class CapCountsOneMore(Model):
    """Lets one task more than the cap through."""

    def cap_for(self, cap: int) -> int:
        return cap + 1


class WaveTakesTheLargestIds(Model):
    """Fills the cap from the end of the list."""

    def wave_members(self, ready: list[str], cap: int) -> list[str]:
        return sorted(ready)[::-1][:cap][::-1]


class WaveEndsWithTheFastest(Model):
    """Starts the next wave when the first task has ended."""

    def wave_end(self, ends: list[int]) -> int:
        return min(ends)


class TasksStartWhenTheirDependenciesEnd(Model):
    """Starts a task the moment its dependencies are over."""

    def waves(self, cap: int) -> list[list[tuple[str, int, int]]]:
        finished: dict[str, int] = {}
        by_id = {t.id: t for t in self.plan}
        done: set[str] = set()
        result: list[list[tuple[str, int, int]]] = []
        while len(done) < len(by_id):
            ready = [i for i, t in by_id.items() if i not in done and set(t.deps) <= done]
            members = sorted(ready)[:cap]
            wave = []
            for i in members:
                start = max([finished[d] for d in by_id[i].deps], default=0)
                wave.append((i, start, start + by_id[i].duration))
            for i, _, end in wave:
                finished[i] = end
            result.append(wave)
            done.update(members)
        return result


class WavesAreNumberedFromZero(Model):
    """Starts counting waves at 0."""

    def first_wave_number(self) -> int:
        return 0


class MakespanIsTheCriticalPath(Model):
    """Answers with the longest chain and ignores the waves."""

    def makespan(self, cap: int) -> int:
        by_id = {t.id: t for t in self.plan}
        return sum(by_id[i].duration for i in self.critical_path())


class MakespanIsTheSumOfDurations(Model):
    """Answers as if there were one worker, whatever the cap."""

    def makespan(self, cap: int) -> int:
        return sum(t.duration for t in self.plan)


class CriticalPathCountsTasks(Model):
    """Takes the chain with the most tasks."""

    def chain_score(self, chain: list[str], by_id: dict[str, Task]) -> tuple[Any, ...]:
        return (-len(chain), chain)


class CriticalPathTieTakesTheLargerIds(Model):
    """Breaks a tie in favour of the larger ids."""

    def chain_score(self, chain: list[str], by_id: dict[str, Task]) -> tuple[Any, ...]:
        return (-sum(by_id[i].duration for i in chain), [-ord(c) for i in chain for c in i])


class CriticalPathTieTakesTheShorterChain(Model):
    """Breaks a tie by the number of tasks first."""

    def chain_score(self, chain: list[str], by_id: dict[str, Task]) -> tuple[Any, ...]:
        return (-sum(by_id[i].duration for i in chain), len(chain), chain)


class CriticalPathTieTakesTheLongerChain(Model):
    """Breaks a tie in favour of the chain with more tasks."""

    def chain_score(self, chain: list[str], by_id: dict[str, Task]) -> tuple[Any, ...]:
        return (-sum(by_id[i].duration for i in chain), -len(chain), chain)


# ------------------------------------------------------------------ level 3 mistakes
class RetriesAreAttempts(Model):
    """Allows maxRetries attempts in all."""

    def allowed_attempts(self, max_retries: int) -> int:
        return max(max_retries, 1)


class OneRetryTooMany(Model):
    """Allows one attempt more than asked."""

    def allowed_attempts(self, max_retries: int) -> int:
        return max_retries + 2


class ScriptEndsMeanSuccess(Model):
    """Lets a task succeed once its script is used up."""

    def letter(self, script: str, attempt: int) -> str:
        return script[attempt - 1] if attempt <= len(script) else "S"


class EmptyScriptFails(Model):
    """Reads no script as a failure."""

    def letter(self, script: str, attempt: int) -> str:
        return "F" if script == "" else super().letter(script, attempt)


class SpanIgnoresRetries(Model):
    """Ends a task after one attempt's time."""

    def span_end(self, start: int, attempts: int, duration: int) -> int:
        return start + duration


class SpanHasNoWait(Model):
    """Ends a task after the time of the last attempt only."""

    def span_end(self, start: int, attempts: int, duration: int) -> int:
        return start + duration * min(attempts, 2)


class FailedTasksStillUnblock(Model):
    """Treats a failed task as finished for the tasks that wait for it."""

    def ready_ids(self, out: Outcome) -> list[str]:
        return [
            i
            for i, s in out.status.items()
            if s == "pending"
            and all(out.status[d] in ("done", "failed") for d in out.tasks[i].deps)
        ]


class LeftoversAreSkipped(Model):
    """Calls every task that never started skipped."""

    def leftover_status(self, out: Outcome, task_id: str) -> str:
        return "skipped"


class LeftoversAreBlocked(Model):
    """Calls every task that never started blocked."""

    def leftover_status(self, out: Outcome, task_id: str) -> str:
        return "blocked"


class FailedTaskIsReplaced(Model):
    """Marks the failed task itself as replaced."""

    def replaced_by_replan(self, out: Outcome) -> list[str]:
        return [i for i, s in out.status.items() if s in ("pending", "failed")]


class ReplanKeepsUnrelatedTasks(Model):
    """Replaces only the tasks that wait for the failed one, directly or not."""

    def replaced_by_replan(self, out: Outcome) -> list[str]:
        lost = {i for i, s in out.status.items() if s == "failed"}
        grew = True
        while grew:
            grew = False
            for i, s in out.status.items():
                if s == "pending" and i not in lost and any(d in lost for d in out.tasks[i].deps):
                    lost.add(i)
                    grew = True
        return [i for i in out.status if i in lost and out.status[i] == "pending"]


class ReplanIsCheckedAlone(Model):
    """Validates the rows of the replan without the done tasks."""

    def replan_check(self, out: Outcome, rows: list[list[str]]) -> list[Row]:
        return self.validate(rows)[0]


class ReplanIsNotChecked(Model):
    """Applies any replan that is made of tasks."""

    def replan_check(self, out: Outcome, rows: list[list[str]]) -> list[Row]:
        return []


class ReplanMayReuseIds(Model):
    """Lets a replan use an id that was in the run, if it is not done."""

    def replan_check(self, out: Outcome, rows: list[list[str]]) -> list[Row]:
        kept = [list(out.tasks[i].row) for i in out.tasks if out.status[i] == "done"]
        return self.validate(kept + rows)[0]


class ReplanIsTriedAgain(Model):
    """Tries a replan in every wave in which its task has failed."""

    def once_only(self) -> bool:
        return False

    def replan_wave(self, out: Outcome, wave: int, members: list[str], used: set[str]) -> None:
        super().replan_wave(out, wave, members, set())
        for i, s in list(out.status.items()):
            if s == "failed" and i in self.replans and i not in members:
                super().replan_wave(out, wave, [i], set())


class EveryFailureGetsItsReplan(Model):
    """Applies the replans of all failed tasks of a wave."""

    def one_per_wave(self) -> bool:
        return False


class RejectionEndsTheTurn(Model):
    """Stops looking at the other failures after a rejected replan."""

    def rejection_ends_turn(self) -> bool:
        return True


class ReplansAreTriedInReverse(Model):
    """Tries the failed tasks from the largest id."""

    def replan_wave(self, out: Outcome, wave: int, members: list[str], used: set[str]) -> None:
        for failed in sorted(members, reverse=True):
            super().replan_wave(out, wave, [failed], used)
            if out.applied:
                return


class LogWavesStartAtZero(Model):
    """Numbers the waves of the log from 0."""

    def wave_label(self, wave: int) -> str:
        return str(wave - 1)


class LogCountsAllTasks(Model):
    """Counts the done tasks as added."""

    def added_count(self, added: list[Task]) -> int:
        return len(added) + 1


class SetReplanAlwaysSaysNew(Model):
    """Answers true whenever a replan is registered."""

    def set_replan(self, failed_id: str, tasks: list[list[str]]) -> bool:
        super().set_replan(failed_id, tasks)
        return True


class SetReplanKeepsTheFirst(Model):
    """Ignores a second registration for an id."""

    def set_replan(self, failed_id: str, tasks: list[list[str]]) -> bool:
        if failed_id in self.replans:
            return False
        return super().set_replan(failed_id, tasks)


class RunChangesThePlan(Model):
    """Leaves the plan as the run ended."""

    def run(self, cap: int, max_retries: int) -> list[Row]:
        rows = super().run(cap, max_retries)
        assert self.last is not None
        self.plan = [t for t in self.last.tasks.values() if self.last.status[t.id] == "done"]
        return rows


class LogKeepsEarlierRuns(Model):
    """Adds the log of a run to the logs of the runs before it."""

    def __init__(self) -> None:
        super().__init__()
        self.history: list[Row] = []

    def run(self, cap: int, max_retries: int) -> list[Row]:
        rows = super().run(cap, max_retries)
        assert self.last is not None
        self.history += self.last.log
        return rows

    def replan_log(self) -> list[Row]:
        return list(self.history)


class RowsFollowTheRun(Model):
    """Lists the tasks in the order they ran."""

    def run_rows(self, out: Outcome) -> list[Row]:
        ranked = sorted(out.status, key=lambda i: (out.span.get(i, (10**9, 0))[0], i))
        by_id = {r[0]: r for r in super().run_rows(out)}
        return [by_id[i] for i in ranked]


class WaveEndIgnoresRetries(Model):
    """Ends a wave at the end of the first attempts."""

    def clock_after(self, ends: list[int], out: Outcome) -> int:
        return max(
            out.clock + t.duration
            for t in out.tasks.values()
            if t.id in out.span and out.span[t.id][0] == out.clock
        )


# ------------------------------------------------------------------ level 4 mistakes
class BudgetIsCheckedAfterwards(Model):
    """Pays for the attempt and then looks at the total."""

    def refusal(self, out: Outcome, task: Task) -> str:
        if self.max_cost != -1 and out.cost >= self.max_cost and out.steps > 0:
            return "cost"
        if self.max_steps != -1 and out.steps >= self.max_steps:
            return "steps"
        return "none"


class CostLimitIsExclusive(Model):
    """Refuses an attempt that reaches the limit."""

    def over_cost(self, spent: int, cost: int, limit: int) -> bool:
        return spent + cost >= limit


class StepsAreCheckedBeforeCost(Model):
    """Names the step limit first when both would refuse."""

    def refusal(self, out: Outcome, task: Task) -> str:
        if self.max_steps != -1 and out.steps + 1 > self.max_steps:
            return "steps"
        if self.max_cost != -1 and out.cost + task.cost > self.max_cost:
            return "cost"
        return "none"


class RefusalOnlySkipsThatAttempt(Model):
    """Goes on with the other attempts of the wave after a refusal."""

    def run_wave(self, out: Outcome, members: list[str], max_retries: int) -> None:
        start = out.clock
        undecided = list(members)
        reason = "none"
        while undecided:
            carry = []
            for i in undecided:
                task = out.tasks[i]
                why = self.refusal(out, task)
                if why != "none":
                    reason = why
                    continue
                out.cost += task.cost
                out.steps += 1
                out.attempts[i] += 1
                if self.letter(task.script, out.attempts[i]) == "S":
                    out.status[i] = "done"
                elif out.attempts[i] >= self.allowed_attempts(max_retries):
                    out.status[i] = "failed"
                else:
                    carry.append(i)
            undecided = carry
        ends = []
        for i in members:
            if out.attempts[i] > 0:
                if out.status[i] == "pending":
                    out.status[i] = "failed"
                end = start + out.attempts[i] * out.tasks[i].duration
                out.span[i] = (start, end)
                ends.append(end)
        if ends:
            out.clock = max(ends)
        out.stopped = reason


class AttemptsAreChargedTaskByTask(Model):
    """Gives each task all its attempts before the next task starts."""

    def run_wave(self, out: Outcome, members: list[str], max_retries: int) -> None:
        start = out.clock
        for i in members:
            task = out.tasks[i]
            while out.status[i] == "pending" and out.stopped == "none":
                why = self.refusal(out, task)
                if why != "none":
                    out.stopped = why
                    break
                out.cost += task.cost
                out.steps += 1
                out.attempts[i] += 1
                if self.letter(task.script, out.attempts[i]) == "S":
                    out.status[i] = "done"
                elif out.attempts[i] >= self.allowed_attempts(max_retries):
                    out.status[i] = "failed"
        ends = []
        for i in members:
            if out.attempts[i] > 0:
                if out.status[i] == "pending":
                    out.status[i] = "failed"
                end = start + out.attempts[i] * out.tasks[i].duration
                out.span[i] = (start, end)
                ends.append(end)
        if ends:
            out.clock = max(ends)


class ReplansHappenAfterAStop(Model):
    """Tries the replans of the stopped wave too."""

    def replans_after_stop(self) -> bool:
        return True


class StoppedTasksStayUnstarted(Model):
    """Leaves a task with a failed attempt unfinished when the run stops."""

    def undecided_status(self) -> str:
        return "pending"


class NothingWaitsForAnything(Model):
    """Calls a task that never started skipped when it waits for a skipped task, blocked when
    it waits for anything that is not done."""

    def leftover_status(self, out: Outcome, task_id: str) -> str:
        lost = any(out.status[d] != "done" for d in out.tasks[task_id].deps)
        return "blocked" if lost else "skipped"


class OnlyFailedMakesBlocked(Model):
    """Blocks only the tasks that wait directly for a failed task."""

    def leftover_status(self, out: Outcome, task_id: str) -> str:
        lost = any(out.status[d] == "failed" for d in out.tasks[task_id].deps)
        return "blocked" if lost else "skipped"


class ClockIgnoresTheStoppedWave(Model):
    """Leaves the clock where the last full wave put it."""

    def clock_after(self, ends: list[int], out: Outcome) -> int:
        return out.clock if out.stopped != "none" else max(ends)


class SpentCountsTheRefusedAttempt(Model):
    """Adds the refused attempt to the steps."""

    def spent_row(self, out: Outcome) -> Row:
        extra = 1 if out.stopped != "none" else 0
        return ["spent", str(out.cost), str(out.steps + extra), str(out.clock)]


class ResultsListEveryTask(Model):
    """Lists the outputs of failed tasks too."""

    def result_ids(self, out: Outcome) -> list[str]:
        return sorted(i for i, s in out.status.items() if s in ("done", "failed"))


class ReportIdsKeepRunOrder(Model):
    """Lists the ids of a group in the order the tasks ran."""

    def list_row(self, name: str, ids: list[str]) -> Row:
        return [name, *sorted(ids, reverse=True)]


class EmptyGroupsLeaveNoRow(Model):
    """Leaves out a group with no task."""

    def report(self) -> list[Row]:
        return [row for row in super().report() if row[0] in ("stopped", "spent") or len(row) > 1]


class RejectedCountsAsApplied(Model):
    """Counts a rejected replan as applied."""

    def counts_row(self, out: Outcome) -> Row:
        return ["replans", str(out.applied + out.rejected), str(out.rejected)]


class ReportBeforeAnyRunIsNotEmpty(Model):
    """Reports an empty run before the first one."""

    def report(self) -> list[Row]:
        if self.last is None:
            self.last = self.fresh_outcome()
        return super().report()


class ReportAddsUpRuns(Model):
    """Adds the spending of every run in the report."""

    def __init__(self) -> None:
        super().__init__()
        self.total = (0, 0)

    def run(self, cap: int, max_retries: int) -> list[Row]:
        rows = super().run(cap, max_retries)
        assert self.last is not None
        self.total = (self.total[0] + self.last.cost, self.total[1] + self.last.steps)
        return rows

    def spent_row(self, out: Outcome) -> Row:
        return ["spent", str(self.total[0]), str(self.total[1]), str(out.clock)]


class MinusOneMeansZero(Model):
    """Reads the limit -1 as a limit of 0."""

    def set_budget(self, max_cost: int, max_steps: int) -> None:
        self.max_cost = max(max_cost, 0) if max_cost < -1 else max_cost
        self.max_steps = max_steps

    def refusal(self, out: Outcome, task: Task) -> str:
        if self.max_cost == -1 and task.cost > 0 and out.steps >= 4:
            return "cost"
        return super().refusal(out, task)


class BudgetIsForgottenAfterARun(Model):
    """Resets the limits when a run has ended."""

    def run(self, cap: int, max_retries: int) -> list[Row]:
        rows = super().run(cap, max_retries)
        self.max_cost = self.max_steps = -1
        return rows


class StopReasonIsAlwaysCost(Model):
    """Names cost for every refusal."""

    def refusal(self, out: Outcome, task: Task) -> str:
        why = super().refusal(out, task)
        return "cost" if why != "none" else why


MISTAKES: Sequence[type[Model]] = [
    subclass for subclass in Model.__subclasses__() if subclass.__module__ == __name__
]


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", op).lower()


def outputs(model_type: Callable[[], Model], case: Mapping[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor."""
    model = model_type()
    calls = zip(case["ops"][1:], case["args"][1:], strict=True)
    return [None, *(getattr(model, snake_case(op))(*arguments) for op, arguments in calls)]


def passes(model_type: Callable[[], Model], case: Mapping[str, Any]) -> bool:
    try:
        return outputs(model_type, case) == case["expected"]
    except (IndexError, KeyError, ValueError, TypeError, RecursionError, AssertionError):
        return False


@pytest.mark.parametrize("case", SCRIPTED_CASES, ids=[case["id"] for case in SCRIPTED_CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert outputs(Model, case) == case["expected"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_every_level_has_visible_and_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in SCRIPTED_CASES if case["level"] == level]
        assert any(case.get("visible") for case in at_level)
        assert sum(not case.get("visible") for case in at_level) >= 2


def hidden_rows(op: str) -> list[list[str]]:
    return [
        row
        for case in HIDDEN_CASES
        for name, got in zip(case["ops"], case["expected"], strict=True)
        if name == op
        for row in got
    ]


def test_the_hidden_cases_reach_every_error_status_and_log_result():
    assert {row[0] for row in hidden_rows("setPlan")} == {
        "malformed-task",
        "duplicate-id",
        "unknown-dependency",
        "cycle",
    }
    assert {row[1] for row in hidden_rows("run")} == {
        "done",
        "failed",
        "blocked",
        "skipped",
        "replaced",
    }
    assert {row[2] for row in hidden_rows("replanLog")} == {"applied", "rejected"}
    assert {row[0] for row in hidden_rows("report")} == {
        "stopped",
        "spent",
        "done",
        "failed",
        "blocked",
        "skipped",
        "replaced",
        "replans",
        "results",
    }
    assert {row[1] for row in hidden_rows("report") if row[0] == "stopped"} == {
        "none",
        "cost",
        "steps",
    }
    rejected = {row[3].split(":")[0] for row in hidden_rows("replanLog") if row[2] == "rejected"}
    assert rejected >= {"unknown-dependency", "cycle", "malformed-task", "duplicate-id"}
