"""scd-type2-dimension promises that its hidden cases catch the classic mistakes of a type 2
slowly changing dimension: surrogate keys numbered in the wrong order, duplicate rows in a batch
read the wrong way, versions closed a day early or left open, untracked attributes overwritten in
one version only or by a stale row, point-in-time lookups that include the end date, facts tied to
the current version whatever their date, late changes that replace the current version instead of
splitting history, and deletes that close a key twice or reopen an old version. These tests replay
every case against a model of the dimension written from the statement, which must give every
expected output, and against that model with one mistake planted at a time, which some hidden case
must fail. The model keeps one flat list of rows and scans it, where the reference keeps a sorted
list of versions per business key. A mistake that crashes fails its case, as a thrown exception
does in the grader."""

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0335-scd-type2-dimension"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
SCRIPTED_CASES = [case for case in CASES if "ops" in case]
HIDDEN_CASES = [case for case in SCRIPTED_CASES if not case.get("visible", False)]
OPEN = 99991231


class Model:
    """The dimension as the statement words it: a flat list of rows, each a dict, scanned for every
    question. Each mistake below overrides one rule."""

    def __init__(self, attributes: list[str]) -> None:
        self.names = list(attributes)
        self.tracked: list[str] = []
        self.rows: list[dict[str, Any]] = []
        self.latest: dict[str, int] = {}

    # --- rules
    def batch(self, rows: list[list[str]]) -> list[tuple[str, list[str]]]:
        """The rows of a load, one per business key (the last one), in business key order."""
        last: dict[str, list[str]] = {}
        for row in rows:
            last[row[0]] = row[1:]
        return sorted(last.items())

    def valid(self, row: dict[str, Any], day: int) -> bool:
        return row["from"] <= day < row["to"]

    def end_of_closed(self, day: int) -> int:
        return day

    def versions(self, key: str) -> list[dict[str, Any]]:
        return sorted((row for row in self.rows if row["key"] == key), key=lambda r: r["from"])

    def holder(self, key: str, day: int) -> dict[str, Any] | None:
        return next((row for row in self.versions(key) if self.valid(row, day)), None)

    def new_row(self, key: str, values: dict[str, str], start: int, end: int) -> None:
        number = len(self.rows) + 1
        self.rows.append({"sk": number, "key": key, "vals": dict(values), "from": start, "to": end})

    def untracked_applies(self, key: str, day: int) -> bool:
        return day >= self.latest[key]

    def copy_untracked(self, key: str, name: str, value: str) -> None:
        for row in self.versions(key):
            row["vals"][name] = value

    def same_day(self, holder: dict[str, Any], incoming: dict[str, str]) -> None:
        for name in self.tracked:
            holder["vals"][name] = incoming[name]

    def split(self, key: str, holder: dict[str, Any], values: dict[str, str], day: int) -> None:
        end = holder["to"]
        holder["to"] = self.end_of_closed(day)
        self.new_row(key, values, day, end)

    def fill_gap(self, key: str, values: dict[str, str], day: int) -> None:
        later = [row["from"] for row in self.versions(key) if row["from"] > day]
        self.new_row(key, values, day, min(later, default=OPEN))

    def merge(self, key: str, incoming: dict[str, str], day: int) -> bool:
        changed = False
        if self.untracked_applies(key, day):
            self.latest[key] = max(self.latest[key], day)
            shared = self.versions(key)[0]["vals"]
            for name in self.names:
                if name not in self.tracked and shared[name] != incoming[name]:
                    self.copy_untracked(key, name, incoming[name])
                    changed = True
        shared = self.versions(key)[0]["vals"]
        values = {
            name: incoming[name] if name in self.tracked else shared[name] for name in self.names
        }
        holder = self.holder(key, day)
        if holder is None:
            self.fill_gap(key, values, day)
            return True
        if all(holder["vals"][name] == incoming[name] for name in self.tracked):
            return changed
        if holder["from"] == day:
            self.same_day(holder, incoming)
        else:
            self.split(key, holder, values, day)
        return True

    def apply(self, rows: list[list[str]], day: int) -> list[int]:
        counts = [0, 0, 0]
        for key, row in self.batch(rows):
            incoming = dict(zip(self.names, row, strict=True))
            if not self.versions(key):
                self.latest[key] = day
                self.new_row(key, incoming, day, OPEN)
                counts[0] += 1
            elif self.merge(key, incoming, day):
                counts[1] += 1
            else:
                counts[2] += 1
        return counts

    def text(self, row: dict[str, Any]) -> list[str]:
        flag = "Y" if row["to"] == OPEN else "N"
        values = [row["vals"][name] for name in self.names]
        return [str(row["sk"]), row["key"], *values, str(row["from"]), str(row["to"]), flag]

    def current(self, key: str) -> dict[str, Any] | None:
        return next((row for row in self.versions(key) if row["to"] == OPEN), None)

    def fact_status(self, key: str, day: int) -> list[str]:
        if not self.versions(key):
            return ["0", "unknown-key"]
        row = self.holder(key, day)
        if row is None:
            return ["0", "no-version"]
        return [str(row["sk"]), "current" if row["to"] == OPEN else "late"]

    def ordered_history(self, key: str) -> list[dict[str, Any]]:
        return self.versions(key)

    def close(self, row: dict[str, Any], day: int) -> bool:
        if row["to"] != OPEN:
            return False
        row["to"] = day
        return True

    # --- level 1
    def load(self, rows: list[list[str]], load_date: int) -> list[int]:
        return self.apply(rows, load_date)

    def lookup(self, business_key: str) -> int:
        row = self.current(business_key)
        return row["sk"] if row else -1

    def row_of(self, surrogate_key: int) -> list[str]:
        found = [row for row in self.rows if row["sk"] == surrogate_key]
        return self.text(found[0]) if found else []

    def size(self) -> int:
        return len(self.rows)

    # --- level 2
    def track_history(self, attribute: str) -> bool:
        if attribute not in self.names or attribute in self.tracked:
            return False
        self.tracked.append(attribute)
        return True

    def history(self, business_key: str) -> list[list[str]]:
        return [self.text(row) for row in self.ordered_history(business_key)]

    # --- level 3
    def lookup_at(self, business_key: str, as_of: int) -> int:
        row = self.holder(business_key, as_of)
        return row["sk"] if row else -1

    def snapshot_at(self, as_of: int) -> list[list[str]]:
        keys = sorted({row["key"] for row in self.rows})
        held = [self.holder(key, as_of) for key in keys]
        return [self.text(row) for row in held if row is not None]

    def resolve_facts(self, facts: list[list[str]]) -> list[list[str]]:
        return [[fact, *self.fact_status(key, int(day))] for fact, key, day in facts]

    # --- level 4
    def load_full(self, rows: list[list[str]], load_date: int) -> list[int]:
        counts = self.apply(rows, load_date)
        present = {row[0] for row in rows}
        closed = 0
        for key in sorted({row["key"] for row in self.rows} - present):
            last = self.versions(key)[-1]
            closed += self.close(last, load_date)
        return [*counts, closed]

    def full_history(self) -> list[list[str]]:
        keys = sorted({row["key"] for row in self.rows})
        return [self.text(row) for key in keys for row in self.ordered_history(key)]


# ------------------------------------------------------------------ level 1 mistakes
class KeysInInputOrder(Model):
    """Numbers new rows in the order the batch lists them."""

    def batch(self, rows: list[list[str]]) -> list[tuple[str, list[str]]]:
        last: dict[str, list[str]] = {}
        for row in rows:
            last[row[0]] = row[1:]
        return list(last.items())


class KeysIgnoringCase(Model):
    """Sorts business keys without regard to case."""

    def batch(self, rows: list[list[str]]) -> list[tuple[str, list[str]]]:
        return sorted(super().batch(rows), key=lambda item: (item[0].lower(), item[0]))


class FirstRowWins(Model):
    """Keeps the first row of a key in a batch."""

    def batch(self, rows: list[list[str]]) -> list[tuple[str, list[str]]]:
        first: dict[str, list[str]] = {}
        for row in rows:
            first.setdefault(row[0], row[1:])
        return sorted(first.items())


class DuplicatesCountTwice(Model):
    """Applies every row of a batch, so a repeated key counts once per row."""

    def batch(self, rows: list[list[str]]) -> list[tuple[str, list[str]]]:
        order = {key: rank for rank, (key, _) in enumerate(super().batch(rows))}
        return sorted(((row[0], row[1:]) for row in rows), key=lambda item: order[item[0]])


class OverwriteMovesTheStart(Model):
    """Moves the start of a row to the date of the load that overwrote it."""

    def copy_untracked(self, key: str, name: str, value: str) -> None:
        super().copy_untracked(key, name, value)
        self.versions(key)[-1]["from"] = max(self.latest[key], self.versions(key)[-1]["from"])


class SizeCountsKeys(Model):
    """Counts business keys instead of rows."""

    def size(self) -> int:
        return len({row["key"] for row in self.rows})


# ------------------------------------------------------------------ level 2 mistakes
class ClosesTheDayBefore(Model):
    """Ends a closed version on the day before the next one starts."""

    def end_of_closed(self, day: int) -> int:
        return day - 1


class SameDayAddsAVersion(Model):
    """Adds a version even when the current one started on the same date."""

    def same_day(self, holder: dict[str, Any], incoming: dict[str, str]) -> None:
        shared = holder["vals"]
        values = {
            name: incoming[name] if name in self.tracked else shared[name] for name in self.names
        }
        self.split(holder["key"], holder, values, holder["from"])


class UntrackedOnlyOnTheCurrentVersion(Model):
    """Overwrites an untracked attribute in the current version only."""

    def copy_untracked(self, key: str, name: str, value: str) -> None:
        self.versions(key)[-1]["vals"][name] = value

    def merge(self, key: str, incoming: dict[str, str], day: int) -> bool:
        changed = False
        last = self.versions(key)[-1]["vals"]
        for name in self.names:
            if name not in self.tracked and last[name] != incoming[name]:
                self.copy_untracked(key, name, incoming[name])
                changed = True
        holder = self.holder(key, day)
        if holder is None or all(holder["vals"][n] == incoming[n] for n in self.tracked):
            return changed or holder is None
        if holder["from"] == day:
            self.same_day(holder, incoming)
        else:
            self.split(key, holder, dict(incoming), day)
        return True


class TrackingTwiceIsTrue(Model):
    """Accepts an attribute that is already tracked."""

    def track_history(self, attribute: str) -> bool:
        if attribute not in self.names:
            return False
        if attribute not in self.tracked:
            self.tracked.append(attribute)
        return True


class OldValueReopensItsVersion(Model):
    """Reopens an earlier version whose tracked values come back instead of adding one."""

    def split(self, key: str, holder: dict[str, Any], values: dict[str, str], day: int) -> None:
        earlier = [
            row
            for row in self.versions(key)
            if row is not holder and all(row["vals"][n] == values[n] for n in self.tracked)
        ]
        if earlier and holder["to"] == OPEN:
            holder["to"] = day
            earlier[-1]["to"] = OPEN
            return
        super().split(key, holder, values, day)


class HistoryBySurrogateKey(Model):
    """Lists the versions of a key by surrogate key."""

    def ordered_history(self, key: str) -> list[dict[str, Any]]:
        return sorted(self.versions(key), key=lambda row: row["sk"])


# ------------------------------------------------------------------ level 3 mistakes
class InclusiveEnd(Model):
    """Counts the end date as part of a version."""

    def valid(self, row: dict[str, Any], day: int) -> bool:
        return row["from"] <= day <= row["to"]

    def holder(self, key: str, day: int) -> dict[str, Any] | None:
        found = [row for row in self.versions(key) if self.valid(row, day)]
        return found[0] if found else None


class FactsUseTheCurrentVersion(Model):
    """Ties every fact to the current version of its key."""

    def fact_status(self, key: str, day: int) -> list[str]:
        row = self.current(key)
        if row is None:
            return ["0", "unknown-key" if not self.versions(key) else "no-version"]
        return [str(row["sk"]), "current"]


class UnknownKeyIsMinusOne(Model):
    """Gives an unknown business key the surrogate key -1."""

    def fact_status(self, key: str, day: int) -> list[str]:
        return ["-1", "unknown-key"] if not self.versions(key) else super().fact_status(key, day)


class EarlyFactUsesTheFirstVersion(Model):
    """Ties a fact dated before the first version to that version."""

    def fact_status(self, key: str, day: int) -> list[str]:
        versions = self.versions(key)
        if versions and day < versions[0]["from"]:
            first = versions[0]
            return [str(first["sk"]), "current" if first["to"] == OPEN else "late"]
        return super().fact_status(key, day)


class LateMeansBeforeTheLoad(Model):
    """Calls a fact late only when it falls before the first version's end."""

    def fact_status(self, key: str, day: int) -> list[str]:
        answer = super().fact_status(key, day)
        if answer[1] == "late" and day >= self.versions(key)[0]["to"]:
            return [answer[0], "current"]
        return answer


class SnapshotByLoadOrder(Model):
    """Lists a snapshot in the order the keys were first loaded."""

    def snapshot_at(self, as_of: int) -> list[list[str]]:
        keys: list[str] = []
        for row in self.rows:
            if row["key"] not in keys:
                keys.append(row["key"])
        held = [self.holder(key, as_of) for key in keys]
        return [self.text(row) for row in held if row is not None]


# ------------------------------------------------------------------ level 4 mistakes
class LateChangeBecomesCurrent(Model):
    """Treats every changed row as the newest: closes the current version and opens one."""

    def merge(self, key: str, incoming: dict[str, str], day: int) -> bool:
        current = self.current(key)
        if current is not None and day < current["from"]:
            if all(current["vals"][n] == incoming[n] for n in self.tracked):
                return False
            current["to"] = day
            self.new_row(key, dict(incoming), day, OPEN)
            return True
        return super().merge(key, incoming, day)


class SplitRunsToTheOpenEnd(Model):
    """Gives the version a late change adds the open end."""

    def split(self, key: str, holder: dict[str, Any], values: dict[str, str], day: int) -> None:
        holder["to"] = self.end_of_closed(day)
        self.new_row(key, values, day, OPEN)


class StaleRowOverwritesUntracked(Model):
    """Lets an older row overwrite the untracked values."""

    def untracked_applies(self, key: str, day: int) -> bool:
        return True


class GapRowIsCurrent(Model):
    """Opens the version a row adds before or between versions to the open end."""

    def fill_gap(self, key: str, values: dict[str, str], day: int) -> None:
        self.new_row(key, values, day, OPEN)


class FullLoadClosesTwice(Model):
    """Counts a key closed by an earlier full load again."""

    def close(self, row: dict[str, Any], day: int) -> bool:
        if row["to"] == OPEN:
            row["to"] = day
        return True


class ReturningKeyReopensItsVersion(Model):
    """Reopens the closed version of a key that comes back."""

    def fill_gap(self, key: str, values: dict[str, str], day: int) -> None:
        last = self.versions(key)[-1]
        if last["to"] <= day and all(last["vals"][n] == values[n] for n in self.names):
            last["to"] = OPEN
            return
        super().fill_gap(key, values, day)


class LookupReturnsAClosedKey(Model):
    """Answers lookup with the last version even when a full load closed it."""

    def lookup(self, business_key: str) -> int:
        versions = self.versions(business_key)
        return versions[-1]["sk"] if versions else -1


MISTAKES: Sequence[type[Model]] = Model.__subclasses__()


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", op).lower()


def outputs(model_type: type[Model], case: Mapping[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor."""
    model = model_type(*case["args"][0])
    calls = zip(case["ops"][1:], case["args"][1:], strict=True)
    return [None, *(getattr(model, snake_case(op))(*arguments) for op, arguments in calls)]


def passes(model_type: type[Model], case: Mapping[str, Any]) -> bool:
    try:
        return outputs(model_type, case) == case["expected"]
    except (IndexError, KeyError, ValueError, TypeError, StopIteration):
        return False


@pytest.mark.parametrize("case", SCRIPTED_CASES, ids=[case["id"] for case in SCRIPTED_CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert outputs(Model, case) == case["expected"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_every_level_has_two_visible_and_two_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in SCRIPTED_CASES if case["level"] == level]
        assert sum(bool(case.get("visible")) for case in at_level) >= 2
        assert sum(not case.get("visible") for case in at_level) >= 2


def test_the_hidden_cases_give_every_fact_status():
    statuses = {
        row[2]
        for case in HIDDEN_CASES
        for op, got in zip(case["ops"], case["expected"], strict=True)
        if op == "resolveFacts"
        for row in got
    }
    assert statuses == {"current", "late", "no-version", "unknown-key"}
