"""pipeline-scheduler promises that its hidden cases catch the classic mistakes of a batch
scheduler: a run order with the wrong tie-break, dependencies counted twice, every leftover task
called a cycle, windows one day off or not clipped at day 0, skips that only see the same run,
attempts added up across reruns, scripts restarted or appended, staleness that misses a failed
input, plans that stop too early or take what was never written, and backfills that ignore the
cap, chain partitions within a round or start with the newest days. These tests replay every case
against a model of the scheduler written from the statement, which must give every expected
output, and against that model with one mistake planted at a time, which some hidden case must
fail. The model scans for the next task instead of keeping a heap, finds cycles from the
transitive closure, and grows plans and skips to a fixed point. A mistake that crashes fails its
case, as a thrown exception does in the grader."""

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0334-pipeline-scheduler"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]

Partition = tuple[str, int]


class Written:
    """One partition of the ledger."""

    def __init__(self) -> None:
        self.state = "missing"
        self.number = 0
        self.reads: dict[Partition, int] = {}
        self.script: list[str] = []


class Model:
    """The scheduler as the statement words it, one rule per method."""

    def __init__(self) -> None:
        self.tasks: dict[str, list[str]] = {}
        self.windows: dict[tuple[str, str], int] = {}
        self.retries: dict[str, int] = {}
        self.ledger: dict[Partition, Written] = {}
        self.counter = 0

    # --- level 1
    def add_task(self, name: str, deps: list[str]) -> bool:
        if name in self.tasks:
            return False
        self.tasks[name] = self.unique(deps)
        return True

    def unique(self, deps: list[str]) -> list[str]:
        return list(dict.fromkeys(deps))

    def known(self, task: str) -> list[str]:
        return [dep for dep in self.tasks[task] if dep in self.tasks]

    def reach(self) -> dict[str, set[str]]:
        closure = {task: set(self.known(task)) for task in self.tasks}
        grew = True
        while grew:
            grew = False
            for task in closure:
                more = set().union(*(closure[d] for d in closure[task])) - closure[task]
                if more:
                    closure[task] |= more
                    grew = True
        return closure

    def on_cycle(self, task: str, closure: dict[str, set[str]]) -> bool:
        return task in closure[task]

    def sort_problems(self, rows: list[list[str]]) -> list[list[str]]:
        return sorted(rows)

    def validate(self) -> list[list[str]]:
        rows = [
            ["unknown-dependency", task, dep]
            for task, deps in self.tasks.items()
            for dep in deps
            if dep not in self.tasks
        ]
        closure = self.reach()
        rows += [["cycle", task] for task in self.tasks if self.on_cycle(task, closure)]
        return self.sort_problems(rows)

    def pick(self, ready: list[str]) -> str:
        return min(ready)

    def order(self) -> list[str]:
        listed: list[str] = []
        while True:
            ready = [t for t in self.tasks if t not in listed and set(self.known(t)) <= set(listed)]
            if not ready:
                return listed
            listed.append(self.pick(ready))

    def run_order(self) -> list[str]:
        return [] if self.validate() else self.order()

    # --- level 2
    def set_window(self, task: str, dep: str, days: int) -> bool:
        if task not in self.tasks or dep not in self.tasks[task]:
            return False
        self.windows[(task, dep)] = days
        return True

    def window(self, task: str, dep: str) -> int:
        return self.windows.get((task, dep), 1)

    def first_day(self, day: int, width: int) -> int:
        return max(0, day - width + 1)

    def needs(self, task: str, day: int) -> list[Partition]:
        return [
            (dep, d)
            for dep in self.tasks[task]
            for d in range(self.first_day(day, self.window(task, dep)), day + 1)
        ]

    def part(self, task: str, day: int) -> Written:
        return self.ledger.setdefault((task, day), Written())

    def is_done(self, p: Partition) -> bool:
        return p in self.ledger and self.ledger[p].state == "done"

    def number_of(self, p: Partition) -> int:
        return self.ledger[p].number if self.is_done(p) else 0

    def write(self, task: str, day: int) -> None:
        self.counter += 1
        written = self.part(task, day)
        written.state = "done"
        written.number = self.counter
        written.reads = {p: self.number_of(p) for p in self.needs(task, day)}

    def mark_done(self, task: str, day: int) -> None:
        self.write(task, day)

    def ready_now(self, task: str, day: int) -> bool:
        return all(self.is_done(p) for p in self.needs(task, day))

    def order_names(self, names: list[str]) -> list[str]:
        return sorted(names)

    def runnable(self, day: int) -> list[str]:
        return self.order_names(
            [t for t in self.tasks if not self.is_done((t, day)) and self.ready_now(t, day)]
        )

    # --- level 3
    def set_retries(self, task: str, retries: int) -> None:
        self.retries[task] = retries

    def script(self, task: str, day: int, outcomes: list[str]) -> None:
        self.part(task, day).script = list(outcomes)

    def limit(self, task: str) -> int:
        return 1 + self.retries.get(task, 0)

    def next_outcome(self, task: str, day: int) -> str:
        script = self.part(task, day).script
        return script.pop(0) if script else "ok"

    def fail(self, task: str, day: int) -> None:
        self.part(task, day).state = "failed"

    def attempt(self, task: str, day: int) -> tuple[str, int]:
        for number in range(1, self.limit(task) + 1):
            if self.next_outcome(task, day) == "ok":
                self.write(task, day)
                return "success", number
        self.fail(task, day)
        return "failed", self.limit(task)

    def skip(self, task: str, day: int) -> None:
        pass

    def run_one(self, task: str, day: int) -> list[str]:
        if not self.ready_now(task, day):
            self.skip(task, day)
            return [task, "skipped", "0"]
        status, attempts = self.attempt(task, day)
        return [task, status, str(attempts)]

    def run(self, day: int) -> list[list[str]]:
        return [self.run_one(task, day) for task in self.run_order()]

    def status(self, task: str, day: int) -> str:
        return self.ledger[(task, day)].state if (task, day) in self.ledger else "missing"

    # --- level 4
    def is_stale(self, p: Partition) -> bool:
        if not self.is_done(p):
            return False
        return any(self.number_of(i) != seen for i, seen in self.ledger[p].reads.items())

    def stale(self, day: int) -> list[str]:
        return sorted(t for t in self.tasks if self.is_stale((t, day)))

    def joins_plan(self, p: Partition, planned: set[Partition]) -> bool:
        return self.is_done(p) and any(i in planned for i in self.needs(*p))

    def plan_set(self, task: str, from_day: int, to_day: int) -> set[Partition]:
        planned = {(task, d) for d in range(from_day, to_day + 1)}
        grew = True
        while grew:
            grew = False
            candidates = {(t, d) for t, d in self.ledger} - planned
            for p in sorted(candidates):
                if self.joins_plan(p, planned):
                    planned.add(p)
                    grew = True
        return planned

    def plan_key(self, p: Partition, rank: dict[str, int]) -> tuple[int, int]:
        return (p[1], rank[p[0]])

    def planned_in_order(self, task: str, from_day: int, to_day: int) -> list[Partition]:
        rank = {t: i for i, t in enumerate(self.run_order())}
        return sorted(self.plan_set(task, from_day, to_day), key=lambda p: self.plan_key(p, rank))

    def plan(self, task: str, from_day: int, to_day: int) -> list[list[str]]:
        return [[str(d), t] for t, d in self.planned_in_order(task, from_day, to_day)]

    def blocked(self, p: Partition, planned: set[Partition], results: dict) -> bool:
        for i in self.needs(*p):
            if i in planned:
                if i in results and results[i][1] != "success":
                    return True
            elif not self.is_done(i):
                return True
        return False

    def ready_in_backfill(self, p: Partition, planned: set[Partition], results: dict) -> bool:
        return all(
            results.get(i, (0, "", 0))[1] == "success" for i in self.needs(*p) if i in planned
        )

    def take(self, ready: list[Partition], cap: int) -> list[Partition]:
        return ready[:cap]

    def skip_round(self, round_number: int) -> int:
        return round_number

    def backfill(self, task: str, from_day: int, to_day: int, cap: int) -> list[list[str]]:
        plan = self.planned_in_order(task, from_day, to_day)
        planned = set(plan)
        results: dict[Partition, tuple[int, str, int]] = {}
        round_number = 0
        while len(results) < len(plan):
            round_number += 1
            changed = True
            while changed:
                changed = False
                for p in plan:
                    if p not in results and self.blocked(p, planned, results):
                        results[p] = (self.skip_round(round_number), "skipped", 0)
                        changed = True
            ready = [
                p for p in plan if p not in results and self.ready_in_backfill(p, planned, results)
            ]
            for p in self.take(ready, cap):
                results[p] = (round_number, *self.attempt(*p))
        rank = {t: i for i, t in enumerate(self.run_order())}
        rows = sorted(results.items(), key=lambda item: (item[1][0], item[0][1], rank[item[0][0]]))
        return [[str(r), str(d), t, status, str(n)] for (t, d), (r, status, n) in rows]


# ------------------------------------------------------------------ level 1 mistakes
class ReadyInAddOrder(Model):
    """Takes the ready task that was added first instead of the smallest name."""

    def pick(self, ready: list[str]) -> str:
        return ready[0]


class LevelByLevel(Model):
    """Lists all the tasks that are ready together, sorted, before looking again."""

    def order(self) -> list[str]:
        listed: list[str] = []
        while True:
            ready = [t for t in self.tasks if t not in listed and set(self.known(t)) <= set(listed)]
            if not ready:
                return listed
            listed += sorted(ready)


class DuplicateDependencyCountsTwice(Model):
    """Keeps a dependency listed twice, so the task waits for it twice."""

    def unique(self, deps: list[str]) -> list[str]:
        return list(deps)

    def order(self) -> list[str]:
        listed: list[str] = []
        while True:
            ready = [
                t
                for t in self.tasks
                if t not in listed
                and len(self.known(t)) == len(set(self.known(t)))
                and set(self.known(t)) <= set(listed)
            ]
            if not ready:
                return listed
            listed.append(min(ready))


class SecondAddReplaces(Model):
    """Lets a second add of a name replace its dependencies."""

    def add_task(self, name: str, deps: list[str]) -> bool:
        fresh = name not in self.tasks
        self.tasks[name] = self.unique(deps)
        return fresh


class LeftoversAreCycles(Model):
    """Reports every task the order could not list as on a cycle."""

    def validate(self) -> list[list[str]]:
        rows = [
            ["unknown-dependency", task, dep]
            for task, deps in self.tasks.items()
            for dep in deps
            if dep not in self.tasks
        ]
        listed = self.order()
        rows += [["cycle", task] for task in self.tasks if task not in listed]
        return sorted(rows)


class ProblemsSortedByTask(Model):
    """Sorts the problems by task first."""

    def sort_problems(self, rows: list[list[str]]) -> list[list[str]]:
        return sorted(rows, key=lambda row: (row[1], row[0], row[2:]))


class OrderDespiteProblems(Model):
    """Gives the partial order of an invalid pipeline."""

    def run_order(self) -> list[str]:
        return self.order()


# ------------------------------------------------------------------ level 2 mistakes
class WindowOneDayTooWide(Model):
    """Reads a window of n days as days d - n to d."""

    def first_day(self, day: int, width: int) -> int:
        return max(0, day - width)


class WindowEndsOnly(Model):
    """Checks only the first and the last day of a window."""

    def needs(self, task: str, day: int) -> list[Partition]:
        return [
            (dep, d)
            for dep in self.tasks[task]
            for d in sorted({self.first_day(day, self.window(task, dep)), day})
        ]


class WindowNotClipped(Model):
    """Lets a window need days before day 0, which never exist."""

    def first_day(self, day: int, width: int) -> int:
        return day - width + 1


class WindowForEveryDependency(Model):
    """Applies a task's window to all of its dependencies."""

    def window(self, task: str, dep: str) -> int:
        return max([w for (t, _), w in self.windows.items() if t == task], default=1)


class DoneIsStillRunnable(Model):
    """Lists a task as runnable even when its partition is done."""

    def runnable(self, day: int) -> list[str]:
        return sorted(t for t in self.tasks if self.ready_now(t, day))


class AnyWindowAccepted(Model):
    """Accepts a window on a pair that is not a dependency."""

    def set_window(self, task: str, dep: str, days: int) -> bool:
        self.windows[(task, dep)] = days
        return True


class RunnableInAddOrder(Model):
    """Lists runnable tasks in the order they were added."""

    def order_names(self, names: list[str]) -> list[str]:
        return names


# ------------------------------------------------------------------ level 3 mistakes
class SkipOnlyOnSameDayFailure(Model):
    """Skips a task only when a dependency failed in this run."""

    def run(self, day: int) -> list[list[str]]:
        failed: set[str] = set()
        rows = []
        for task in self.run_order():
            if any(dep in failed for dep in self.tasks[task]):
                rows.append([task, "skipped", "0"])
                failed.add(task)
                continue
            status, attempts = self.attempt(task, day)
            if status != "success":
                failed.add(task)
            rows.append([task, status, str(attempts)])
        return rows


class AttemptsAddUpAcrossRuns(Model):
    """Counts the attempts of earlier runs too."""

    def __init__(self) -> None:
        super().__init__()
        self.total: dict[Partition, int] = {}

    def attempt(self, task: str, day: int) -> tuple[str, int]:
        status, attempts = super().attempt(task, day)
        self.total[(task, day)] = self.total.get((task, day), 0) + attempts
        return status, self.total[(task, day)]


class FailedRerunKeepsTheOldData(Model):
    """Leaves a done partition done when its rerun fails."""

    def fail(self, task: str, day: int) -> None:
        if not self.is_done((task, day)):
            super().fail(task, day)


class ScriptRestartsEachRun(Model):
    """Throws away the outcomes a run did not use."""

    def attempt(self, task: str, day: int) -> tuple[str, int]:
        result = super().attempt(task, day)
        self.part(task, day).script = []
        return result


class ScriptAppends(Model):
    """Adds new outcomes after the unused ones instead of replacing them."""

    def script(self, task: str, day: int, outcomes: list[str]) -> None:
        self.part(task, day).script += list(outcomes)


class RetriesAreTotalAttempts(Model):
    """Makes at most `retries` attempts, at least one."""

    def limit(self, task: str) -> int:
        return max(1, self.retries.get(task, 0))


class RunsOnlyWhatIsNotDone(Model):
    """Leaves a done partition alone instead of rerunning it."""

    def run_one(self, task: str, day: int) -> list[str]:
        if self.is_done((task, day)):
            return [task, "skipped", "0"]
        return super().run_one(task, day)


class SkipForgetsThePartition(Model):
    """Marks a skipped partition as missing."""

    def skip(self, task: str, day: int) -> None:
        self.ledger.pop((task, day), None)


class RunInNameOrder(Model):
    """Runs the tasks in name order."""

    def run(self, day: int) -> list[list[str]]:
        return [self.run_one(task, day) for task in sorted(self.tasks)]


# ------------------------------------------------------------------ level 4 mistakes
class StaleOnlyWhenRewritten(Model):
    """Notices a rewritten input but not one that failed."""

    def is_stale(self, p: Partition) -> bool:
        if not self.is_done(p):
            return False
        return any(
            self.is_done(i) and self.number_of(i) != seen
            for i, seen in self.ledger[p].reads.items()
        )


class MarkDoneReadsNothing(Model):
    """Records no inputs for a partition marked done."""

    def mark_done(self, task: str, day: int) -> None:
        super().mark_done(task, day)
        self.part(task, day).reads = {}


class PlanStopsAtDirectDependents(Model):
    """Adds only the partitions that need the backfilled ones directly."""

    def plan_set(self, task: str, from_day: int, to_day: int) -> set[Partition]:
        planned = {(task, d) for d in range(from_day, to_day + 1)}
        direct = {p for p in self.ledger if p not in planned and self.joins_plan(p, planned)}
        return planned | direct


class PlanFollowsSameDayOnly(Model):
    """Ignores windows when it looks for the partitions that read a planned one."""

    def joins_plan(self, p: Partition, planned: set[Partition]) -> bool:
        return self.is_done(p) and any((dep, p[1]) in planned for dep in self.tasks[p[0]])


class PlanTakesWhatWasNeverWritten(Model):
    """Adds failed partitions that read a planned one."""

    def joins_plan(self, p: Partition, planned: set[Partition]) -> bool:
        return p in self.ledger and any(i in planned for i in self.needs(*p))


class PlanSortedByName(Model):
    """Orders a day's partitions by name instead of run order."""

    def plan_key(self, p: Partition, rank: dict[str, int]) -> tuple[int, int]:
        return (p[1], sorted(rank).index(p[0]))


class BackfillIgnoresTheCap(Model):
    """Runs every ready partition in each round."""

    def take(self, ready: list[Partition], cap: int) -> list[Partition]:
        return ready


class BackfillChainsWithinARound(Model):
    """Lets a partition run in the same round as the inputs it waits for."""

    def backfill(self, task: str, from_day: int, to_day: int, cap: int) -> list[list[str]]:
        plan = self.planned_in_order(task, from_day, to_day)
        planned = set(plan)
        results: dict[Partition, tuple[int, str, int]] = {}
        round_number = 0
        while len(results) < len(plan):
            round_number += 1
            started = 0
            for p in plan:
                if p in results:
                    continue
                if self.blocked(p, planned, results):
                    results[p] = (round_number, "skipped", 0)
                elif started < cap and self.ready_in_backfill(p, planned, results):
                    results[p] = (round_number, *self.attempt(*p))
                    started += 1
        rank = {t: i for i, t in enumerate(self.run_order())}
        rows = sorted(results.items(), key=lambda item: (item[1][0], item[0][1], rank[item[0][0]]))
        return [[str(r), str(d), t, status, str(n)] for (t, d), (r, status, n) in rows]


class BackfillSkipsARoundLate(Model):
    """Gives a skipped partition the round after the one it was found in."""

    def skip_round(self, round_number: int) -> int:
        return round_number + 1


class BackfillNewestFirst(Model):
    """Starts with the newest days when the cap holds partitions back."""

    def take(self, ready: list[Partition], cap: int) -> list[Partition]:
        return sorted(ready, key=lambda p: -p[1])[:cap]


class BackfillTrustsOutsideInputs(Model):
    """Runs a planned partition whose input outside the plan is missing."""

    def blocked(self, p: Partition, planned: set[Partition], results: dict) -> bool:
        return any(
            i in planned and i in results and results[i][1] != "success" for i in self.needs(*p)
        )


class BackfillWithoutRetries(Model):
    """Gives a backfilled partition one attempt, whatever its retries."""

    def backfill(self, task: str, from_day: int, to_day: int, cap: int) -> list[list[str]]:
        saved = dict(self.retries)
        self.retries = {}
        try:
            return super().backfill(task, from_day, to_day, cap)
        finally:
            self.retries = saved


MISTAKES: Sequence[type[Model]] = Model.__subclasses__()


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", op).lower()


def outputs(model_type: type[Model], case: Mapping[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor."""
    model = model_type()
    calls = zip(case["ops"][1:], case["args"][1:], strict=True)
    return [None, *(getattr(model, snake_case(op))(*arguments) for op, arguments in calls)]


def passes(model_type: type[Model], case: Mapping[str, Any]) -> bool:
    try:
        return outputs(model_type, case) == case["expected"]
    except (IndexError, KeyError, ValueError, TypeError):
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
