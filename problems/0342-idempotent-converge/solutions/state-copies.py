import copy
import re

COUNTED = ("ok", "changed", "failed", "skipped")
WHOLE = re.compile(r"-?[0-9]+")


class Host:
    """A simulated host: file contents by path, and the service state of each installed package
    (every package brings a service of the same name)."""

    def __init__(self) -> None:
        self.files: dict[str, str] = {}
        self.packages: dict[str, str] = {}
        self.facts: dict[str, str] = {}


def compare(fact: str, operator: str, value: str) -> bool | None:
    """The truth of one condition, or None when it cannot be decided."""
    if operator == "==":
        return fact == value
    if operator == "!=":
        return fact != value
    if not (WHOLE.fullmatch(fact) and WHOLE.fullmatch(value)):
        return None
    left, right = int(fact), int(value)
    return {"<": left < right, "<=": left <= right, ">": left > right, ">=": left >= right}[
        operator
    ]


class Converger:
    """Tasks describe the state a host should be in. Running a task compares that state with the
    host's and changes the host only when they differ, so a second run finds nothing to do. A run
    works through the hosts in batches; in each batch it applies every task to every host still
    standing, then the handlers that a change notified. A check run does the same on deep copies of
    the hosts, so later tasks see what earlier ones would have done while the real hosts stay as
    they were."""

    def __init__(self) -> None:
        self._hosts: dict[str, Host] = {}
        self._tasks: dict[str, tuple[str, str, str]] = {}
        self._handlers: dict[str, tuple[str, str, str]] = {}
        self._notify: dict[str, list[str]] = {}
        self._conditions: dict[str, list[tuple[str, str, str]]] = {}
        self._batch = 0
        self._summary: dict[str, dict[str, int]] = {}

    # Level 1
    def add_host(self, host: str) -> bool:
        if host in self._hosts:
            return False
        self._hosts[host] = Host()
        return True

    def set_state(self, host: str, kind: str, target: str, value: str) -> bool:
        if host not in self._hosts:
            return False
        self._apply(self._hosts[host], kind, target, value)
        return True

    def add_task(self, name: str, kind: str, target: str, value: str) -> bool:
        if name in self._tasks:
            return False
        self._tasks[name] = (kind, target, value)
        return True

    def run(self) -> list[list[str]]:
        counts = {host: dict.fromkeys(COUNTED, 0) for host in self._hosts}
        rows = self._play(self._hosts, False, counts)
        self._summary = counts
        return rows

    def state(self, host: str) -> list[list[str]]:
        if host not in self._hosts:
            return []
        found = self._hosts[host]
        rows = [["file", path, found.files[path]] for path in found.files]
        rows += [["package", name, "present"] for name in found.packages]
        rows += [["service", name, found.packages[name]] for name in found.packages]
        return sorted(rows, key=lambda row: (row[0], row[1]))

    # Level 2
    def check(self) -> list[list[str]]:
        copies = {name: copy.deepcopy(host) for name, host in self._hosts.items()}
        counts = {host: dict.fromkeys(COUNTED, 0) for host in self._hosts}
        return self._play(copies, True, counts)

    # Level 3
    def add_handler(self, name: str, kind: str, target: str, value: str) -> bool:
        if name in self._handlers:
            return False
        self._handlers[name] = (kind, target, value)
        return True

    def notifies(self, task: str, handler: str) -> bool:
        if task not in self._tasks or handler not in self._handlers:
            return False
        links = self._notify.setdefault(task, [])
        if handler in links:
            return False
        links.append(handler)
        return True

    # Level 4
    def set_fact(self, host: str, key: str, value: str) -> bool:
        if host not in self._hosts:
            return False
        new = key not in self._hosts[host].facts
        self._hosts[host].facts[key] = value
        return new

    def only_if(self, task: str, fact: str, comparison: str, value: str) -> bool:
        if task not in self._tasks:
            return False
        self._conditions.setdefault(task, []).append((fact, comparison, value))
        return True

    def set_batch_size(self, size: int) -> bool:
        changed = size != self._batch
        self._batch = size
        return changed

    def summary(self) -> list[list[str]]:
        rows = []
        for host in self._hosts:
            counts = self._summary.get(host, dict.fromkeys(COUNTED, 0))
            rows.append([host, *(str(counts[name]) for name in COUNTED)])
        return rows

    # Running
    def _play(self, hosts: dict[str, Host], dry: bool, counts) -> list[list[str]]:
        names = list(hosts)
        size = self._batch if self._batch > 0 else max(len(names), 1)
        rows: list[list[str]] = []
        for start in range(0, len(names), size):
            batch = names[start : start + size]
            failed: set[str] = set()
            notified: dict[str, set[str]] = {host: set() for host in batch}
            for task, (kind, target, value) in self._tasks.items():
                for host in batch:
                    if host in failed:
                        continue
                    status, diff = self._task(hosts[host], task, kind, target, value)
                    if status == "failed":
                        failed.add(host)
                    if status == "changed":
                        notified[host].update(self._notify.get(task, ()))
                    counts[host][status] += 1
                    rows.append([host, task, status, *(diff if dry else [])])
            for handler, (kind, target, value) in self._handlers.items():
                for host in batch:
                    if host in failed or handler not in notified[host]:
                        continue
                    status, diff = self._change(hosts[host], kind, target, value)
                    if status == "failed":
                        failed.add(host)
                    counts[host][status] += 1
                    rows.append([host, handler, status, *(diff if dry else [])])
            if len(failed) == len(batch):
                break
        return rows

    def _task(self, host: Host, task: str, kind: str, target: str, value: str):
        for fact, operator, wanted in self._conditions.get(task, ()):
            if fact not in host.facts:
                return "failed", []
            holds = compare(host.facts[fact], operator, wanted)
            if holds is None:
                return "failed", []
            if not holds:
                return "skipped", []
        return self._change(host, kind, target, value)

    @staticmethod
    def _current(host: Host, kind: str, target: str) -> str | None:
        """The state that a task of this kind compares with, or None for a missing service."""
        if kind == "file":
            return host.files.get(target, "")
        if kind == "package":
            return "present" if target in host.packages else "absent"
        return host.packages.get(target)

    def _change(self, host: Host, kind: str, target: str, value: str):
        before = self._current(host, kind, target)
        if before is None:
            return "failed", []
        if before == value and value != "restarted":
            return "ok", []
        self._apply(host, kind, target, value)
        return "changed", [before, value]

    @staticmethod
    def _apply(host: Host, kind: str, target: str, value: str) -> None:
        if kind == "file":
            host.files[target] = value
        elif kind == "package" and value == "present":
            host.packages.setdefault(target, "stopped")
        elif kind == "package":
            host.packages.pop(target, None)
        else:
            host.packages[target] = "running" if value == "restarted" else value
