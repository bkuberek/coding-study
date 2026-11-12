"""drift-detection promises that its hidden cases catch the classic mistakes of a drift detector:
records matched by name instead of id, attributes merged instead of replaced, keys compared on
one side only, a pattern matcher that treats `*` too narrowly or `?` and `[` as special, ignore
rules that hide too much or too little, order-insensitive lists compared as sets, defaults that
cross types or override real values, an import that checks its refusals in the wrong order or
shares the scan's attributes, a plan read from the scan, and a reconcile that picks the oldest
rule, reverts to the recorded value or forgets normalization. These tests replay every case
against a model of the detector written from the statement, which must give every expected
output, and against that model with one mistake planted at a time, which some hidden case must
fail. A mistake that crashes fails its case, as a thrown exception does in the grader."""

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0341-drift-detection"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]


def pairs(attributes: list[list[str]]) -> dict[str, str]:
    return {pair[0]: pair[1] for pair in attributes}


class Model:
    """The detector as the statement words it. Patterns become regular expressions, values are
    compared through a canonical form, rows are collected with a sort key and sorted at the end,
    and the policy of an address is found by scanning the rules from the newest. Each mistake
    below overrides one method."""

    def __init__(self) -> None:
        self.records: dict[str, dict[str, Any]] = {}
        self.scan: dict[str, dict[str, Any]] = {}
        self.ignores: list[tuple[str, str]] = []
        self.lists: set[tuple[str, str]] = set()
        self.defaults: dict[tuple[str, str], str] = {}
        self.want: dict[str, dict[str, str]] = {}
        self.rules: list[tuple[str, str]] = []

    # --- level 1
    def record(self, address: str, resource_id: str, attributes: list[list[str]]) -> bool:
        new = address not in self.records
        self.records[address] = {"id": resource_id, "attrs": pairs(attributes)}
        return new

    def observe(self, resource_id: str, resource_type: str, attributes: list[list[str]]) -> bool:
        new = resource_id not in self.scan
        self.scan[resource_id] = {"type": resource_type, "attrs": pairs(attributes)}
        return new

    def text_key(self, text: str) -> Any:
        return text

    def found(self, address: str) -> dict[str, Any] | None:
        return self.scan.get(self.records[address]["id"])

    def recorded_attrs(self, address: str) -> dict[str, str]:
        return self.records[address]["attrs"]

    def keys_of(self, first: dict[str, str], second: dict[str, str]) -> list[str]:
        return sorted(set(first) | set(second), key=self.text_key)

    def unmanaged_ids(self) -> list[str]:
        managed = {entry["id"] for entry in self.records.values()}
        return [rid for rid in self.scan if rid not in managed]

    def unmanaged_sort(self, rid: str) -> Any:
        return self.text_key(rid)

    def show(self, resource_type: str, key: str, value: str | None) -> str:
        return "" if value is None else value

    def drift_items(self) -> list[tuple[Any, list[str], str]]:
        items = []
        for address in self.records:
            if self.hidden(address, "*"):
                continue
            seen = self.found(address)
            if seen is None:
                if not self.deleted_hidden(address):
                    rid = self.records[address]["id"]
                    items.append(((0, self.text_key(address)), ["deleted", address, rid], address))
                continue
            kind = address.split(".")[0]
            ours, theirs = self.recorded_attrs(address), seen["attrs"]
            for key in self.keys_of(ours, theirs):
                if self.equal(kind, key, ours.get(key), theirs.get(key)):
                    continue
                if self.hidden(address, key):
                    continue
                row = [
                    "changed",
                    address,
                    key,
                    self.show(kind, key, ours.get(key)),
                    self.show(kind, key, theirs.get(key)),
                ]
                order = (0, self.text_key(address), self.text_key(key))
                items.append((order, row, address))
        for rid in self.unmanaged_ids():
            kind = self.scan[rid]["type"]
            if self.unmanaged_hidden(rid, kind):
                continue
            items.append(((1, self.unmanaged_sort(rid)), ["unmanaged", rid, kind], ""))
        return self.arrange(items)

    def arrange(self, items: list[tuple[Any, list[str], str]]) -> list[tuple[Any, list[str], str]]:
        return sorted(items, key=lambda item: item[0])

    def drift(self) -> list[list[str]]:
        return [row for _, row, _ in self.drift_items()]

    # --- level 2
    def ignore(self, pattern: str, key: str) -> bool:
        if (pattern, key) in self.ignores:
            return False
        self.ignores.append((pattern, key))
        return True

    def unordered(self, resource_type: str, key: str) -> bool:
        new = (resource_type, key) not in self.lists
        self.lists.add((resource_type, key))
        return new

    def default_value(self, resource_type: str, key: str, value: str) -> bool:
        new = (resource_type, key) not in self.defaults
        self.defaults[(resource_type, key)] = value
        return new

    def pattern_regex(self, pattern: str) -> str:
        return "".join(".*" if char == "*" else re.escape(char) for char in pattern)

    def matches(self, pattern: str, text: str) -> bool:
        return re.fullmatch(self.pattern_regex(pattern), text, flags=re.DOTALL) is not None

    def hidden(self, address: str, key: str) -> bool:
        return any(k == key and self.matches(p, address) for p, k in self.ignores)

    def deleted_hidden(self, address: str) -> bool:
        return False

    def unmanaged_hidden(self, rid: str, kind: str) -> bool:
        return self.hidden(f"{kind}.{rid}", "*")

    def is_list(self, resource_type: str, key: str) -> bool:
        return (resource_type, key) in self.lists

    def filled(self, resource_type: str, key: str, value: str | None) -> str | None:
        return self.defaults.get((resource_type, key)) if value is None else value

    def canonical(self, resource_type: str, key: str, value: str | None) -> Any:
        value = self.filled(resource_type, key, value)
        if value is None:
            return None
        if self.is_list(resource_type, key):
            return ("list", tuple(sorted(value.split(","))))
        return ("text", value)

    def equal(self, resource_type: str, key: str, first: str | None, second: str | None) -> bool:
        return self.canonical(resource_type, key, first) == self.canonical(
            resource_type, key, second
        )

    # --- level 3
    def import_resource(self, address: str, resource_id: str) -> str:
        for check, code in self.import_checks():
            if check(address, resource_id):
                return code
        self.adopt(address, resource_id)
        return "imported"

    def import_checks(self) -> list[tuple[Any, str]]:
        return [
            (lambda a, r: r not in self.scan, "not-found"),
            (lambda a, r: self.scan[r]["type"] != a.split(".")[0], "type-mismatch"),
            (lambda a, r: any(e["id"] == r for e in self.records.values()), "already-managed"),
            (lambda a, r: a in self.records, "address-taken"),
        ]

    def adopt(self, address: str, resource_id: str) -> None:
        self.records[address] = {"id": resource_id, "attrs": dict(self.scan[resource_id]["attrs"])}

    def desire(self, address: str, attributes: list[list[str]]) -> bool:
        new = address not in self.want
        self.want[address] = pairs(attributes)
        return new

    def plan_base(self, address: str) -> dict[str, str]:
        return self.records[address]["attrs"]

    def plan_hidden(self, address: str, key: str) -> bool:
        return False

    def plan_items(self) -> list[tuple[Any, list[str]]]:
        items = []
        for address in set(self.want) | set(self.records):
            if address not in self.records:
                items.append(((self.text_key(address),), ["create", address]))
            elif address not in self.want:
                items.append(((self.text_key(address),), ["delete", address]))
            else:
                kind = address.split(".")[0]
                base, goal = self.plan_base(address), self.want[address]
                for key in set(base) | set(goal):
                    if self.equal(kind, key, base.get(key), goal.get(key)):
                        continue
                    if self.plan_hidden(address, key):
                        continue
                    row = ["update", address, key, base.get(key, ""), goal.get(key, "")]
                    items.append(((self.text_key(address), self.text_key(key)), row))
        return items

    def plan(self) -> list[list[str]]:
        return [row for _, row in sorted(self.plan_items(), key=lambda item: item[0])]

    # --- level 4
    def policy(self, pattern: str, mode: str) -> bool:
        new = all(p != pattern for p, _ in self.rules)
        self.rules = [(p, m) for p, m in self.rules if p != pattern] + [(pattern, mode)]
        return new

    def mode_of(self, address: str) -> str:
        for pattern, mode in reversed(self.rules):
            if self.matches(pattern, address):
                return mode
        return self.fallback()

    def fallback(self) -> str:
        return "alert"

    def target(self, address: str, key: str) -> str:
        return self.want[address].get(key, "")

    def agrees(self, kind: str, key: str, scanned: str, desired: str) -> bool:
        return self.equal(kind, key, scanned or None, desired or None)

    def changed_row(self, mode: str, row: list[str]) -> list[str] | None:
        _, address, key, recorded, scanned = row
        if mode == "alert":
            return ["alert", address, key, recorded, scanned]
        desired = self.target(address, key)
        if self.agrees(address.split(".")[0], key, scanned, desired):
            return None
        if mode == "revert":
            return ["revert", address, key, scanned, desired]
        return self.accept_row(address, key, desired, scanned)

    def accept_row(self, address: str, key: str, desired: str, scanned: str) -> list[str]:
        return ["accept", address, key, desired, scanned]

    def deleted_row(self, mode: str, row: list[str]) -> list[str]:
        if mode == "revert":
            return ["recreate", row[1]]
        if mode == "accept":
            return ["forget", row[1]]
        return ["alert-deleted", row[1], row[2]]

    def unmanaged_row(self, row: list[str]) -> list[str]:
        return ["alert-unmanaged", row[1], row[2]]

    def reconcile_source(self) -> list[tuple[Any, list[str], str]]:
        return self.drift_items()

    def reconcile(self) -> list[list[str]]:
        out = []
        for _, row, address in self.reconcile_source():
            if row[0] == "unmanaged":
                made: list[str] | None = self.unmanaged_row(row)
            elif row[0] == "deleted":
                made = self.deleted_row(self.mode_of(address), row)
            else:
                made = self.changed_row(self.mode_of(address), row)
            if made is not None:
                out.append(made)
        return out


# ------------------------------------------------------------------ level 1 mistakes
class RecordMerges(Model):
    """Keeps the keys of an earlier record."""

    def record(self, address: str, resource_id: str, attributes: list[list[str]]) -> bool:
        old = self.records.get(address, {"attrs": {}})["attrs"]
        new = super().record(address, resource_id, attributes)
        self.records[address]["attrs"] = {**old, **self.records[address]["attrs"]}
        return new


class ObserveMerges(Model):
    """Keeps the keys of an earlier scan of the id."""

    def observe(self, resource_id: str, resource_type: str, attributes: list[list[str]]) -> bool:
        old = self.scan.get(resource_id, {"attrs": {}})["attrs"]
        new = super().observe(resource_id, resource_type, attributes)
        self.scan[resource_id]["attrs"] = {**old, **self.scan[resource_id]["attrs"]}
        return new


class MatchedByName(Model):
    """Looks a recorded address up in the scan by its name."""

    def found(self, address: str) -> dict[str, Any] | None:
        return self.scan.get(address.split(".", 1)[1])


class UnmanagedByType(Model):
    """Sorts unmanaged resources by type, then id."""

    def unmanaged_sort(self, rid: str) -> Any:
        return (self.scan[rid]["type"], rid)


class SortIgnoringCase(Model):
    """Sorts texts without regard to case."""

    def text_key(self, text: str) -> Any:
        return text.lower()


class NaturalSort(Model):
    """Sorts the digits in a text by their numeric value."""

    def text_key(self, text: str) -> Any:
        return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", text)]


class OnlyRecordedKeys(Model):
    """Compares only the keys the record has."""

    def keys_of(self, first: dict[str, str], second: dict[str, str]) -> list[str]:
        return sorted(first)


class ValuesIgnoreCase(Model):
    """Compares values without regard to case."""

    def canonical(self, resource_type: str, key: str, value: str | None) -> Any:
        found = super().canonical(resource_type, key, value)
        return ("text", found[1].lower()) if found and found[0] == "text" else found


class ValuesAsNumbers(Model):
    """Compares values that look like numbers by their numeric value."""

    def canonical(self, resource_type: str, key: str, value: str | None) -> Any:
        found = super().canonical(resource_type, key, value)
        if found and found[0] == "text" and found[1].isdigit():
            return ("text", str(int(found[1])))
        return found


class ChangedRowsInInputOrder(Model):
    """Lists the changed keys of a resource in the order the record gave them."""

    def keys_of(self, first: dict[str, str], second: dict[str, str]) -> list[str]:
        return [*first, *(key for key in second if key not in first)]

    def arrange(self, items: list[tuple[Any, list[str], str]]) -> list[tuple[Any, list[str], str]]:
        return sorted(items, key=lambda item: item[0][:2])


class AllRowsSortedTogether(Model):
    """Sorts unmanaged rows among the others by their second field."""

    def arrange(self, items: list[tuple[Any, list[str], str]]) -> list[tuple[Any, list[str], str]]:
        return sorted(items, key=lambda item: (item[1][1], item[1][2]))


# ------------------------------------------------------------------ level 2 mistakes
class StarNeedsACharacter(Model):
    """Lets a star match one character or more, never none."""

    def pattern_regex(self, pattern: str) -> str:
        return "".join(".+" if char == "*" else re.escape(char) for char in pattern)


class StarStopsAtADot(Model):
    """Lets a star match anything but a dot."""

    def pattern_regex(self, pattern: str) -> str:
        return "".join("[^.]*" if char == "*" else re.escape(char) for char in pattern)


class PatternIsAPrefix(Model):
    """Accepts any text that starts with what the pattern matches."""

    def pattern_regex(self, pattern: str) -> str:
        return super().pattern_regex(pattern) + ".*"


class ShellPatternSyntax(Model):
    """Reads ? as any character and [...] as a character class."""

    def pattern_regex(self, pattern: str) -> str:
        out = []
        for char in pattern:
            out.append({"*": ".*", "?": ".", "[": "[", "]": "]"}.get(char, re.escape(char)))
        return "".join(out)


class KeyRuleHidesDeleted(Model):
    """Hides a deleted resource when any of its keys is ignored."""

    def deleted_hidden(self, address: str) -> bool:
        return any(self.matches(p, address) for p, _ in self.ignores)


class UnmanagedMatchedById(Model):
    """Matches an unmanaged resource by its bare id."""

    def unmanaged_hidden(self, rid: str, kind: str) -> bool:
        return self.hidden(rid, "*")


class KeyRuleHidesUnmanaged(Model):
    """Hides an unmanaged resource under a rule for any key."""

    def unmanaged_hidden(self, rid: str, kind: str) -> bool:
        return any(self.matches(p, f"{kind}.{rid}") for p, _ in self.ignores)


class RecordedMatchedByTypeAndId(Model):
    """Matches recorded resources by type.id as well as by address."""

    def hidden(self, address: str, key: str) -> bool:
        if super().hidden(address, key):
            return True
        if address in self.records:
            text = f"{address.split('.')[0]}.{self.records[address]['id']}"
            return super().hidden(text, key)
        return False


class ListsAsSets(Model):
    """Compares order-insensitive lists as sets, ignoring repeats."""

    def canonical(self, resource_type: str, key: str, value: str | None) -> Any:
        found = super().canonical(resource_type, key, value)
        return ("list", tuple(sorted(set(found[1])))) if found and found[0] == "list" else found


class ListRuleOnEveryType(Model):
    """Applies an unordered rule to the key on every type."""

    def is_list(self, resource_type: str, key: str) -> bool:
        return any(k == key for _, k in self.lists)


class ListRuleOnEveryKey(Model):
    """Treats every key of a type with an unordered rule as a list."""

    def is_list(self, resource_type: str, key: str) -> bool:
        return any(t == resource_type for t, _ in self.lists)


class DefaultOverridesValues(Model):
    """Compares the default instead of a value that is present."""

    def filled(self, resource_type: str, key: str, value: str | None) -> str | None:
        return self.defaults.get((resource_type, key), value)


class DefaultOnEveryType(Model):
    """Applies a default to the key on every type."""

    def filled(self, resource_type: str, key: str, value: str | None) -> str | None:
        if value is not None:
            return value
        return next((v for (_, k), v in self.defaults.items() if k == key), None)


class RowsShowNormalizedValues(Model):
    """Prints the values after the default is filled in."""

    def show(self, resource_type: str, key: str, value: str | None) -> str:
        filled = self.filled(resource_type, key, value)
        return "" if filled is None else filled


class FirstDefaultKept(Model):
    """Keeps the first default of a type and key."""

    def default_value(self, resource_type: str, key: str, value: str) -> bool:
        new = (resource_type, key) not in self.defaults
        self.defaults.setdefault((resource_type, key), value)
        return new


class IgnoreAlwaysNew(Model):
    """Says every ignore rule is new."""

    def ignore(self, pattern: str, key: str) -> bool:
        super().ignore(pattern, key)
        return True


# ------------------------------------------------------------------ level 3 mistakes
class AddressCheckedBeforeOwner(Model):
    """Refuses a taken address before a managed id."""

    def import_checks(self) -> list[tuple[Any, str]]:
        checks = super().import_checks()
        return [*checks[:2], checks[3], checks[2]]


class TypeCheckedLast(Model):
    """Checks the type after the other refusals."""

    def import_checks(self) -> list[tuple[Any, str]]:
        checks = super().import_checks()
        return [checks[0], checks[2], checks[3], checks[1]]


class ImportSharesTheScan(Model):
    """Records the scan's own attributes, so a later scan rewrites the record."""

    def adopt(self, address: str, resource_id: str) -> None:
        self.records[address] = {"id": resource_id, "attrs": None, "live": resource_id}

    def recorded_attrs(self, address: str) -> dict[str, str]:
        entry = self.records[address]
        return self.scan[entry["live"]]["attrs"] if "live" in entry else entry["attrs"]

    def plan_base(self, address: str) -> dict[str, str]:
        return self.recorded_attrs(address)


class PlanReadsTheScan(Model):
    """Compares the desired state with the scan instead of the records."""

    def plan_base(self, address: str) -> dict[str, str]:
        seen = self.found(address)
        return seen["attrs"] if seen else self.records[address]["attrs"]


class PlanUsesIgnoreRules(Model):
    """Hides ignored keys and resources from the plan."""

    def plan_hidden(self, address: str, key: str) -> bool:
        return self.hidden(address, key) or self.hidden(address, "*")


class PlanWithoutNormalization(Model):
    """Compares plain texts in the plan."""

    def plan_items(self) -> list[tuple[Any, list[str]]]:
        saved_lists, saved_defaults = self.lists, self.defaults
        self.lists, self.defaults = set(), {}
        try:
            return super().plan_items()
        finally:
            self.lists, self.defaults = saved_lists, saved_defaults


class ImportNeedsNoConfig(Model):
    """Leaves an imported resource without a desired one out of the plan."""

    def plan_items(self) -> list[tuple[Any, list[str]]]:
        return [item for item in super().plan_items() if item[1][0] != "delete"]


class PlanGroupedByKind(Model):
    """Lists creates, then updates, then deletes."""

    def plan(self) -> list[list[str]]:
        rank = {"create": 0, "update": 1, "delete": 2}
        items = sorted(self.plan_items(), key=lambda item: (rank[item[1][0]], item[0]))
        return [row for _, row in items]


# ------------------------------------------------------------------ level 4 mistakes
class OldestRuleWins(Model):
    """Takes the first matching rule instead of the newest."""

    def mode_of(self, address: str) -> str:
        for pattern, mode in self.rules:
            if self.matches(pattern, address):
                return mode
        return self.fallback()


class RedeclaredRuleKeepsItsPlace(Model):
    """Changes the mode of a pattern given again without making it the newest."""

    def policy(self, pattern: str, mode: str) -> bool:
        if any(p == pattern for p, _ in self.rules):
            self.rules = [(p, mode if p == pattern else m) for p, m in self.rules]
            return False
        self.rules.append((pattern, mode))
        return True


class RevertByDefault(Model):
    """Reverts an address that no rule matches."""

    def fallback(self) -> str:
        return "revert"


class RevertsToTheRecord(Model):
    """Reverts to the recorded value instead of the desired one."""

    def target(self, address: str, key: str) -> str:
        return self.records[address]["attrs"].get(key, "")


class ActsWhenTheWorldAgrees(Model):
    """Reverts or accepts even when the scan already equals the desired value."""

    def agrees(self, kind: str, key: str, scanned: str, desired: str) -> bool:
        return False


class AgreementAsPlainText(Model):
    """Decides that the scan agrees with the desired value by comparing texts."""

    def agrees(self, kind: str, key: str, scanned: str, desired: str) -> bool:
        return scanned == desired


class AcceptRowBackwards(Model):
    """Lists the scanned value before the desired one in an accept row."""

    def accept_row(self, address: str, key: str, desired: str, scanned: str) -> list[str]:
        return ["accept", address, key, scanned, desired]


class DeletedAlwaysAlerts(Model):
    """Raises an alert for every deleted resource, whatever its rule."""

    def deleted_row(self, mode: str, row: list[str]) -> list[str]:
        return ["alert-deleted", row[1], row[2]]


class UnmanagedFollowsRules(Model):
    """Applies the rules to unmanaged resources by type.id."""

    def unmanaged_row(self, row: list[str]) -> list[str]:
        mode = self.mode_of(f"{self.scan[row[1]]['type']}.{row[1]}")
        return ["alert-unmanaged", row[1], row[2]] if mode == "alert" else [mode, row[1], row[2]]


class ReconcileSkipsIgnoreRules(Model):
    """Works from the drift before the ignore rules apply."""

    def reconcile_source(self) -> list[tuple[Any, list[str], str]]:
        saved, self.ignores = self.ignores, []
        try:
            return self.drift_items()
        finally:
            self.ignores = saved


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
    except (IndexError, KeyError, ValueError, TypeError, AttributeError):
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


def test_the_hidden_cases_reach_every_import_answer_and_reconcile_row():
    answers, heads = set(), set()
    for case in HIDDEN_CASES:
        for op, got in zip(case["ops"], case["expected"], strict=True):
            if op == "importResource":
                answers.add(got)
            if op == "reconcile":
                heads.update(row[0] for row in got)
    assert answers == {"imported", "not-found", "type-mismatch", "already-managed", "address-taken"}
    assert heads == {
        "revert",
        "accept",
        "alert",
        "recreate",
        "forget",
        "alert-deleted",
        "alert-unmanaged",
    }
