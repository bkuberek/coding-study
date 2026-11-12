"""idempotent-converge promises that its hidden cases catch the classic mistakes of a convergence
tool: tasks that write without comparing, a run ordered host by host or sorted by name, a removed
package that leaves its service behind, a check that changes the hosts or ignores what earlier
tasks would have done, handlers run at once, twice or on a failed host, a failure that stops every
host or none, conditions that read text as numbers or let a missing fact pass, batches whose
handlers wait for the end, a run that stops too early or too late, and a summary that counts the
wrong things. These tests replay every case against a model of the tool written from the
statement, which must give every expected output, and against that model with one mistake planted
at a time, which some hidden case must fail. A mistake that crashes fails its case, as a thrown
exception does in the grader."""

import copy
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0342-idempotent-converge"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]
STATUSES = ("ok", "changed", "failed", "skipped")
NUMBER = re.compile(r"-?[0-9]+")


class Model:
    """The tool as the statement words it. A host is one flat map from (kind, target) to a
    value, a check runs on the real maps and puts a saved copy back afterwards, and a run first
    lists the (host, task) pairs it will visit. Each mistake below overrides one method."""

    def __init__(self) -> None:
        self.hosts: dict[str, dict[tuple[str, str], str]] = {}
        self.facts: dict[str, dict[str, str]] = {}
        self.tasks: list[tuple[str, str, str, str]] = []
        self.handlers: list[tuple[str, str, str, str]] = []
        self.links: set[tuple[str, str]] = set()
        self.conditions: dict[str, list[tuple[str, str, str]]] = {}
        self.size = 0
        self.counts: dict[str, dict[str, int]] = {}

    # --- level 1
    def add_host(self, host: str) -> bool:
        if host in self.hosts:
            return False
        self.hosts[host] = {}
        self.facts[host] = {}
        return True

    def set_state(self, host: str, kind: str, target: str, value: str) -> bool:
        if host not in self.hosts:
            return False
        self.put(self.hosts[host], kind, target, value)
        return True

    def add_task(self, name: str, kind: str, target: str, value: str) -> bool:
        if any(task[0] == name for task in self.tasks):
            return False
        self.tasks.append((name, kind, target, value))
        return True

    def put(self, resources: dict, kind: str, target: str, value: str) -> None:
        if kind == "file":
            resources[("file", target)] = value
        elif kind == "package" and value == "present":
            if ("package", target) not in resources:
                resources[("package", target)] = "present"
                resources[("service", target)] = self.fresh_service()
        elif kind == "package":
            resources.pop(("package", target), None)
            self.drop_service(resources, target)
        else:
            resources[("service", target)] = "running" if value == "restarted" else value

    def fresh_service(self) -> str:
        return "stopped"

    def drop_service(self, resources: dict, target: str) -> None:
        resources.pop(("service", target), None)

    def now(self, resources: dict, kind: str, target: str) -> str | None:
        if kind == "file":
            return resources.get(("file", target), "")
        if kind == "package":
            return resources.get(("package", target), "absent")
        if ("package", target) not in resources:
            return None
        return resources[("service", target)]

    def unchanged(self, before: str, value: str) -> bool:
        return before == value and value != "restarted"

    def act(self, resources: dict, kind: str, target: str, value: str) -> tuple[str, list[str]]:
        before = self.now(resources, kind, target)
        if before is None:
            return "failed", []
        if self.unchanged(before, value):
            return "ok", []
        self.put(resources, kind, target, value)
        return "changed", [before, value]

    def state(self, host: str) -> list[list[str]]:
        resources = self.hosts.get(host, {})
        return [[kind, target, value] for (kind, target), value in self.state_order(resources)]

    def state_order(self, resources: dict) -> list:
        return sorted(resources.items())

    def host_order(self, names: list[str]) -> list[str]:
        return names

    def schedule(self, batch: list[str]) -> list[tuple[str, tuple[str, str, str, str]]]:
        return [(host, task) for task in self.tasks for host in batch]

    def run(self) -> list[list[str]]:
        self.counts = {host: dict.fromkeys(STATUSES, 0) for host in self.hosts}
        return self.play(self.counts, with_diff=False)

    # --- level 2
    def check(self) -> list[list[str]]:
        saved = self.snapshot()
        try:
            return self.play({h: dict.fromkeys(STATUSES, 0) for h in self.hosts}, with_diff=True)
        finally:
            self.restore(saved)

    def snapshot(self) -> Any:
        return copy.deepcopy(self.hosts)

    def restore(self, saved: Any) -> None:
        self.hosts = saved

    def diff_of(self, status: str, diff: list[str]) -> list[str]:
        return diff if status == "changed" else []

    # --- level 3
    def add_handler(self, name: str, kind: str, target: str, value: str) -> bool:
        if any(handler[0] == name for handler in self.handlers):
            return False
        self.handlers.append((name, kind, target, value))
        return True

    def notifies(self, task: str, handler: str) -> bool:
        known_task = any(t[0] == task for t in self.tasks)
        known_handler = any(h[0] == handler for h in self.handlers)
        if not (known_task and known_handler) or (task, handler) in self.links:
            return False
        self.links.add((task, handler))
        return True

    def sends(self, status: str) -> bool:
        return status == "changed"

    def handler_queue(self, notified: list[str]) -> list[str]:
        return [h[0] for h in self.handlers if h[0] in notified]

    def stops_host(self, status: str) -> bool:
        return status == "failed"

    # --- level 4
    def set_fact(self, host: str, key: str, value: str) -> bool:
        if host not in self.hosts:
            return False
        new = key not in self.facts[host]
        self.facts[host][key] = value
        return new

    def only_if(self, task: str, fact: str, operator: str, value: str) -> bool:
        if all(t[0] != task for t in self.tasks):
            return False
        self.conditions.setdefault(task, []).append((fact, operator, value))
        return True

    def set_batch_size(self, size: int) -> bool:
        changed = size != self.size
        self.size = size
        return changed

    def holds(self, host: str, fact: str, operator: str, value: str) -> bool | None:
        if fact not in self.facts[host]:
            return None
        have = self.facts[host][fact]
        if operator in ("==", "!="):
            return (have == value) == (operator == "==")
        if not (NUMBER.fullmatch(have) and NUMBER.fullmatch(value)):
            return None
        a, b = int(have), int(value)
        return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[operator]

    def gate(self, host: str, task: str) -> str | None:
        """None to run the task, or the status it ends with instead."""
        for condition in self.conditions.get(task, []):
            result = self.holds(host, *condition)
            if result is None:
                return "failed"
            if not result:
                return "skipped"
        return None

    def batches(self) -> list[list[str]]:
        names = self.host_order(list(self.hosts))
        if self.size <= 0:
            return [names] if names else []
        return [names[i : i + self.size] for i in range(0, len(names), self.size)]

    def stop_after(self, batch: list[str], down: set[str]) -> bool:
        return all(host in down for host in batch)

    def handlers_per_batch(self) -> bool:
        return True

    def play(self, counts: dict, with_diff: bool) -> list[list[str]]:
        rows: list[list[str]] = []
        pending: list[tuple[list[str], dict, set]] = []
        for batch in self.batches():
            down: set[str] = set()
            notified: dict[str, list[str]] = {host: [] for host in batch}
            for host, (name, kind, target, value) in self.schedule(batch):
                if host in down:
                    continue
                status = self.gate(host, name)
                diff: list[str] = []
                if status is None:
                    status, diff = self.act(self.hosts[host], kind, target, value)
                if self.stops_host(status):
                    down.add(host)
                if self.sends(status):
                    notified[host] += [h for t, h in sorted(self.links) if t == name]
                counts[host][status] += 1
                rows.append(
                    [host, name, status, *(self.diff_of(status, diff) if with_diff else [])]
                )
            if self.handlers_per_batch():
                rows += self.run_handlers(batch, notified, down, counts, with_diff)
            else:
                pending.append((batch, notified, down))
            if self.stop_after(batch, down):
                break
        for batch, notified, down in pending:
            rows += self.run_handlers(batch, notified, down, counts, with_diff)
        return rows

    def run_handlers(self, batch, notified, down, counts, with_diff) -> list[list[str]]:
        rows = []
        table = {h[0]: h for h in self.handlers}
        names = sorted(
            {n for host in batch for n in self.handler_queue(notified[host])},
            key=lambda n: [h[0] for h in self.handlers].index(n),
        )
        for name in names:
            _, kind, target, value = table[name]
            for host in batch:
                if host in down or name not in self.handler_queue(notified[host]):
                    continue
                status, diff = self.act(self.hosts[host], kind, target, value)
                if self.stops_host(status):
                    down.add(host)
                counts[host][status] += 1
                rows.append(
                    [host, name, status, *(self.diff_of(status, diff) if with_diff else [])]
                )
        return rows

    def summary(self) -> list[list[str]]:
        return [[host, *(str(self.counted(host)[s]) for s in STATUSES)] for host in self.hosts]

    def counted(self, host: str) -> dict[str, int]:
        return self.counts.get(host, dict.fromkeys(STATUSES, 0))


# ------------------------------------------------------------------ level 1 mistakes
class HostByHost(Model):
    """Runs every task on one host before moving to the next host."""

    def schedule(self, batch: list[str]) -> list[tuple[str, tuple[str, str, str, str]]]:
        return [(host, task) for host in batch for task in self.tasks]


class HostsByName(Model):
    """Visits the hosts sorted by name."""

    def host_order(self, names: list[str]) -> list[str]:
        return sorted(names)


class TasksByName(Model):
    """Runs the tasks sorted by name."""

    def schedule(self, batch: list[str]) -> list[tuple[str, tuple[str, str, str, str]]]:
        return [(host, task) for task in sorted(self.tasks) for host in batch]


class FilesAlwaysWritten(Model):
    """Writes a file whatever its content."""

    def act(self, resources: dict, kind: str, target: str, value: str) -> tuple[str, list[str]]:
        if kind == "file":
            before = resources.get(("file", target), "")
            resources[("file", target)] = value
            return "changed", [before, value]
        return super().act(resources, kind, target, value)


class InstalledServiceRuns(Model):
    """Starts the service of a package as soon as it is installed."""

    def fresh_service(self) -> str:
        return "running"


class RemovalKeepsTheService(Model):
    """Leaves the service behind when its package is removed."""

    def drop_service(self, resources: dict, target: str) -> None:
        pass

    def now(self, resources: dict, kind: str, target: str) -> str | None:
        if kind == "service" and ("service", target) in resources:
            return resources[("service", target)]
        return super().now(resources, kind, target)

    def state_order(self, resources: dict) -> list:
        return sorted(
            (k, v)
            for k, v in resources.items()
            if k[0] != "service" or ("package", k[1]) in resources
        )


class ReinstallKeepsServiceState(Model):
    """Gives a package installed again the service state it had before its removal."""

    def __init__(self) -> None:
        super().__init__()
        self.memory: dict[str, str] = {}

    def drop_service(self, resources: dict, target: str) -> None:
        self.memory[target] = resources.get(("service", target), "stopped")
        super().drop_service(resources, target)

    def put(self, resources: dict, kind: str, target: str, value: str) -> None:
        installing = kind == "package" and value == "present"
        fresh = installing and ("package", target) not in resources
        super().put(resources, kind, target, value)
        if fresh and target in self.memory:
            resources[("service", target)] = self.memory[target]


class DuplicateTaskReplaces(Model):
    """Replaces a task added again under the same name."""

    def add_task(self, name: str, kind: str, target: str, value: str) -> bool:
        for index, task in enumerate(self.tasks):
            if task[0] == name:
                self.tasks[index] = (name, kind, target, value)
                return False
        return super().add_task(name, kind, target, value)


class StateOfAnUnknownHostCreatesIt(Model):
    """Adds the host when setState names one that does not exist."""

    def set_state(self, host: str, kind: str, target: str, value: str) -> bool:
        if host not in self.hosts:
            self.add_host(host)
        return super().set_state(host, kind, target, value)


class StateSortedIgnoringCase(Model):
    """Sorts the state without regard to case."""

    def state_order(self, resources: dict) -> list:
        return sorted(resources.items(), key=lambda kv: (kv[0][0], kv[0][1].lower()))


class StateSortedByTarget(Model):
    """Sorts the state by target first."""

    def state_order(self, resources: dict) -> list:
        return sorted(resources.items(), key=lambda kv: (kv[0][1], kv[0][0]))


class ContentIgnoresCase(Model):
    """Compares file contents without regard to case."""

    def unchanged(self, before: str, value: str) -> bool:
        return before.lower() == value.lower() and value != "restarted"


# ------------------------------------------------------------------ level 2 mistakes
class CheckChangesTheHosts(Model):
    """Runs the check on the real hosts and keeps the result."""

    def restore(self, saved: Any) -> None:
        pass


class CheckSeesOnlyTheRealHosts(Model):
    """Lets every task of a check look at the hosts as they were before the check."""

    def check(self) -> list[list[str]]:
        saved = copy.deepcopy(self.hosts)
        original = copy.deepcopy(self.hosts)
        real_act = self.act

        def act(resources: dict, kind: str, target: str, value: str) -> tuple[str, list[str]]:
            host = next(h for h, r in self.hosts.items() if r is resources)
            scratch = copy.deepcopy(original[host])
            return real_act(scratch, kind, target, value)

        self.act = act  # type: ignore[method-assign]
        try:
            return self.play({h: dict.fromkeys(STATUSES, 0) for h in self.hosts}, with_diff=True)
        finally:
            del self.act
            self.hosts = saved


class DiffBackwards(Model):
    """Puts the new value before the old one in a diff."""

    def diff_of(self, status: str, diff: list[str]) -> list[str]:
        return diff[::-1] if status == "changed" else []


class MissingFileShownAsAbsent(Model):
    """Shows a missing file as absent in a diff."""

    def diff_of(self, status: str, diff: list[str]) -> list[str]:
        found = super().diff_of(status, diff)
        return ["absent" if part == "" else part for part in found]


class OkRowsCarryADiff(Model):
    """Gives ok rows a diff of the value with itself."""

    def act(self, resources: dict, kind: str, target: str, value: str) -> tuple[str, list[str]]:
        status, diff = super().act(resources, kind, target, value)
        return status, diff or ([value, value] if status == "ok" else [])

    def diff_of(self, status: str, diff: list[str]) -> list[str]:
        return diff


# ------------------------------------------------------------------ level 3 mistakes
class HandlersRunAtOnce(Model):
    """Runs a handler right after the task that notifies it."""

    def play(self, counts: dict, with_diff: bool) -> list[list[str]]:
        rows: list[list[str]] = []
        table = {h[0]: h for h in self.handlers}
        for batch in self.batches():
            down: set[str] = set()
            for host, (name, kind, target, value) in self.schedule(batch):
                if host in down:
                    continue
                status = self.gate(host, name)
                diff: list[str] = []
                if status is None:
                    status, diff = self.act(self.hosts[host], kind, target, value)
                if status == "failed":
                    down.add(host)
                counts[host][status] += 1
                rows.append([host, name, status, *(diff if with_diff else [])])
                if status == "changed":
                    for t, h in sorted(self.links):
                        if t == name:
                            _, k, tg, v = table[h]
                            s, d = self.act(self.hosts[host], k, tg, v)
                            counts[host][s] += 1
                            rows.append([host, h, s, *(d if with_diff else [])])
            if self.stop_after(batch, down):
                break
        return rows


class HandlerOncePerNotification(Model):
    """Runs a handler once for every task that notified it."""

    def handler_queue(self, notified: list[str]) -> list[str]:
        return notified

    def run_handlers(self, batch, notified, down, counts, with_diff) -> list[list[str]]:
        rows = []
        table = {h[0]: h for h in self.handlers}
        for host in batch:
            for name in notified[host]:
                if host in down:
                    break
                _, kind, target, value = table[name]
                status, diff = self.act(self.hosts[host], kind, target, value)
                counts[host][status] += 1
                rows.append([host, name, status, *(diff if with_diff else [])])
        return rows


class HandlersInNotifyOrder(Model):
    """Runs the handlers in the order they were first notified."""

    def run_handlers(self, batch, notified, down, counts, with_diff) -> list[list[str]]:
        order: list[str] = []
        for host in batch:
            for name in notified[host]:
                if name not in order:
                    order.append(name)
        saved = self.handlers
        self.handlers = sorted(saved, key=lambda h: order.index(h[0]) if h[0] in order else 99)
        try:
            return super().run_handlers(batch, notified, down, counts, with_diff)
        finally:
            self.handlers = saved


class HandlersOnAFailedHost(Model):
    """Runs the notified handlers of a host that failed."""

    def run_handlers(self, batch, notified, down, counts, with_diff) -> list[list[str]]:
        return super().run_handlers(batch, notified, set(), counts, with_diff)


class OkTaskNotifies(Model):
    """Lets a task that changed nothing notify its handlers."""

    def sends(self, status: str) -> bool:
        return status in ("changed", "ok")


class FailureStopsEveryHost(Model):
    """Stops the whole run at the first failure."""

    def play(self, counts: dict, with_diff: bool) -> list[list[str]]:
        rows = super().play(counts, with_diff)
        for index, row in enumerate(rows):
            if row[2] == "failed":
                return rows[: index + 1]
        return rows


class FailedHostCarriesOn(Model):
    """Keeps running tasks on a host after one of them failed."""

    def stops_host(self, status: str) -> bool:
        return False


class RestartWhenRunningIsOk(Model):
    """Treats a restart of a running service as already done."""

    def unchanged(self, before: str, value: str) -> bool:
        return before == value or (value == "restarted" and before == "running")


class CheckSkipsHandlers(Model):
    """Leaves the handlers out of a check run."""

    def check(self) -> list[list[str]]:
        saved, self.handlers = self.handlers, []
        try:
            return super().check()
        finally:
            self.handlers = saved


# ------------------------------------------------------------------ level 4 mistakes
class MissingFactSkips(Model):
    """Skips a task whose condition names a fact the host lacks."""

    def gate(self, host: str, task: str) -> str | None:
        found = super().gate(host, task)
        if found == "failed" and any(
            fact not in self.facts[host] for fact, _, _ in self.conditions.get(task, [])
        ):
            return "skipped"
        return found


class NumbersComparedAsText(Model):
    """Compares numeric conditions as text."""

    def holds(self, host: str, fact: str, operator: str, value: str) -> bool | None:
        if fact not in self.facts[host]:
            return None
        have = self.facts[host][fact]
        table = {
            "==": have == value,
            "!=": have != value,
            "<": have < value,
            "<=": have <= value,
            ">": have > value,
            ">=": have >= value,
        }
        return table[operator]


class LenientNumbers(Model):
    """Accepts anything the language's integer parser accepts, such as +5."""

    def holds(self, host: str, fact: str, operator: str, value: str) -> bool | None:
        if fact not in self.facts[host] or operator in ("==", "!="):
            return super().holds(host, fact, operator, value)
        try:
            a, b = int(self.facts[host][fact]), int(value)
        except ValueError:
            return None
        return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[operator]


class AnyConditionSuffices(Model):
    """Runs a task when any one of its conditions holds."""

    def gate(self, host: str, task: str) -> str | None:
        results = [self.holds(host, *c) for c in self.conditions.get(task, [])]
        if any(result is None for result in results):
            return "failed"
        if results and not any(results):
            return "skipped"
        return None


class SkippedTaskNotifies(Model):
    """Lets a skipped task notify its handlers."""

    def sends(self, status: str) -> bool:
        return status in ("changed", "skipped")


class BatchesIgnored(Model):
    """Runs every host in one batch."""

    def batches(self) -> list[list[str]]:
        names = list(self.hosts)
        return [names] if names else []


class HandlersAfterAllBatches(Model):
    """Runs every batch's handlers after the last batch."""

    def handlers_per_batch(self) -> bool:
        return False


class NeverStops(Model):
    """Starts every batch even after a whole batch failed."""

    def stop_after(self, batch: list[str], down: set[str]) -> bool:
        return False


class StopsOnAnyFailure(Model):
    """Stops after any batch with a failed host."""

    def stop_after(self, batch: list[str], down: set[str]) -> bool:
        return bool(down)


class OkCountsChanged(Model):
    """Counts changed tasks under ok as well."""

    def counted(self, host: str) -> dict[str, int]:
        counts = dict(super().counted(host))
        counts["ok"] += counts["changed"]
        return counts


class SummaryLeavesOutHandlers(Model):
    """Counts only the tasks."""

    def run_handlers(self, batch, notified, down, counts, with_diff) -> list[list[str]]:
        scratch = {host: dict.fromkeys(STATUSES, 0) for host in counts}
        return super().run_handlers(batch, notified, down, scratch, with_diff)


class CheckUpdatesTheSummary(Model):
    """Lets a check run replace the summary."""

    def check(self) -> list[list[str]]:
        saved = self.snapshot()
        try:
            self.counts = {host: dict.fromkeys(STATUSES, 0) for host in self.hosts}
            return self.play(self.counts, with_diff=True)
        finally:
            self.restore(saved)


class SummaryOnlyListsHostsThatRan(Model):
    """Leaves out of the summary the hosts that the latest run never reached."""

    def summary(self) -> list[list[str]]:
        return [row for row in super().summary() if row[1:] != ["0", "0", "0", "0"]]


class ConditionOnAHandler(Model):
    """Accepts a condition on a handler name."""

    def only_if(self, task: str, fact: str, operator: str, value: str) -> bool:
        if any(h[0] == task for h in self.handlers):
            self.conditions.setdefault(task, []).append((fact, operator, value))
            return True
        return super().only_if(task, fact, operator, value)


class FactAlwaysNew(Model):
    """Says every fact is new."""

    def set_fact(self, host: str, key: str, value: str) -> bool:
        return super().set_fact(host, key, value) or host in self.hosts


class UndecidableAnywhereFails(Model):
    """Fails a task when any of its conditions cannot be decided, even after a false one."""

    def gate(self, host: str, task: str) -> str | None:
        results = [self.holds(host, *c) for c in self.conditions.get(task, [])]
        if any(result is None for result in results):
            return "failed"
        if not all(results):
            return "skipped"
        return None


class LeadingZerosRejected(Model):
    """Refuses a whole number written with leading zeros."""

    def holds(self, host: str, fact: str, operator: str, value: str) -> bool | None:
        have = self.facts[host].get(fact, "")
        if operator not in ("==", "!=") and re.fullmatch(r"-?0[0-9]+", have):
            return None
        return super().holds(host, fact, operator, value)


class FirstBatchSizeOfAllHostsIsNotNew(Model):
    """Says a first batch size that equals the number of hosts changes nothing."""

    def set_batch_size(self, size: int) -> bool:
        effective = self.size if self.size > 0 else len(self.hosts)
        self.size = size
        return size != effective


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
    except (IndexError, KeyError, ValueError, TypeError, AttributeError, StopIteration):
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


def test_a_second_run_of_a_converging_play_is_all_ok():
    """Every case that runs twice in a row without a restart or conflicting tasks converges."""
    for case in CASES:
        ops = case["ops"]
        for i in range(1, len(ops) - 1):
            if ops[i] == ops[i + 1] == "run" and case["id"] in ("ex1", "ex2", "h4", "h6"):
                assert all(row[2] in ("ok", "skipped") for row in case["expected"][i + 1])
