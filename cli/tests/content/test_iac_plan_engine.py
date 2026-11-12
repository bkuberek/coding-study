"""iac-plan-engine promises that its hidden cases catch the classic mistakes of a plan engine:
attributes merged instead of replaced, deletes ordered among the other steps, values compared as
anything but text, references compared before they are resolved, a dependency order taken by
depth or by insertion instead of the smallest ready step, cycles found in the wrong groups,
replacements forced or marked on the wrong keys, a mark that does not spread or spreads the wrong
way, the old object of a create-first replace deleted too early, and an apply that stops at the
first failure, writes unknown values or loses the old object. These tests replay every case
against a model of the engine written from the statement, which must give every expected output,
and against that model with one mistake planted at a time, which some hidden case must fail. A
mistake that crashes fails its case, as a thrown exception does in the grader."""

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0340-iac-plan-engine"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]
UNKNOWN = "<unknown>"
CREATE_FIRST = "create-first"
DELETE_FIRST = "delete-first"


def pairs(attributes: list[list[str]]) -> dict[str, str]:
    return {pair[0]: pair[1] for pair in attributes}


class Step:
    def __init__(self, verb: str, address: str, tag: str = "") -> None:
        self.verb, self.address, self.tag = verb, address, tag
        self.rows: list[list[str]] = []
        self.order = ""

    @property
    def head(self) -> list[str]:
        return [self.verb, self.address] + ([self.tag] if self.tag else [])


class Model:
    """The engine as the statement words it. Values resolve by memoized recursion, cycles come
    from a boolean reachability table, and the order is built by scanning every unplaced step for
    the smallest ready one. Each mistake below overrides one method."""

    def __init__(self) -> None:
        self.want: dict[str, dict[str, str]] = {}
        self.have: dict[str, dict[str, str]] = {}
        self.links: set[tuple[str, str]] = set()
        self.old: dict[str, dict[str, str]] = {}
        self.old_links: set[tuple[str, str]] = set()
        self.forced: set[tuple[str, str]] = set()
        self.comp: set[tuple[str, str]] = set()
        self.marks: set[str] = set()
        self.memo_value: dict[tuple[str, str], str] = {}
        self.memo_action: dict[str, str] = {}

    # --- level 1
    def desire(self, address: str, attributes: list[list[str]]) -> bool:
        new = address not in self.want
        self.want[address] = pairs(attributes)
        return new

    def remove(self, address: str) -> bool:
        return self.want.pop(address, None) is not None

    def observe(self, address: str, attributes: list[list[str]]) -> bool:
        new = address not in self.have
        self.have[address] = pairs(attributes)
        return new

    def plan(self) -> list[list[str]]:
        self.forget()
        errors = self.errors()
        if errors:
            return errors
        rows: list[list[str]] = []
        for step in self.ordered(self.steps()):
            rows += [step.head, *step.rows]
        return rows

    def sort_key(self, text: str) -> Any:
        return text

    def same(self, first: str | None, second: str | None) -> bool:
        return first == second

    def keys_compared(self, wanted: dict[str, str], actual: dict[str, str]) -> set[str]:
        return wanted.keys() | actual.keys()

    def rank(self, step: Step) -> int:
        return 1 if step.verb == "delete" else 0

    def change_rows(self, wanted: dict[str, str], actual: dict[str, str]) -> list[list[str]]:
        rows = []
        for key in self.keys_compared(wanted, actual):
            new, old = wanted.get(key), actual.get(key)
            if self.same(new, old):
                continue
            if old is None:
                rows.append(["+", key, new])
            elif new is None:
                rows.append(["-", key, old])
            else:
                rows.append(["~", key, old, new])
        return rows

    def sorted_rows(self, rows: list[list[str]]) -> list[list[str]]:
        return sorted(rows, key=lambda row: self.sort_key(row[1]))

    def gone_rows(self, attributes: dict[str, str]) -> list[list[str]]:
        return self.sorted_rows([["-", key, value] for key, value in attributes.items()])

    # --- level 2
    def observe_dependency(self, address: str, depends_on: str) -> bool:
        if address not in self.have or depends_on not in self.have:
            return False
        if (address, depends_on) in self.links:
            return False
        self.links.add((address, depends_on))
        return True

    @staticmethod
    def parse(value: str) -> tuple[str, str] | None:
        match = re.fullmatch(r"\$\{([a-z0-9_]+\.[a-z0-9_]+)\.([a-z0-9_]+)\}", value)
        return (match.group(1), match.group(2)) if match else None

    def kind(self, address: str) -> str:
        return address.split(".")[0]

    def is_comp(self, address: str, key: str) -> bool:
        return (self.kind(address), key) in self.comp

    def target_exists(self, target: str, key: str) -> bool:
        return target in self.want and (key in self.want[target] or self.is_comp(target, key))

    def bad_references(self) -> list[tuple[str, str, str]]:
        found = []
        for address, attributes in self.want.items():
            for key, value in attributes.items():
                parsed = self.parse(value)
                if parsed and not self.target_exists(*parsed):
                    found.append((address, key, f"{parsed[0]}.{parsed[1]}"))
        return found

    def unknown_rows(self) -> list[list[str]]:
        rows = sorted(self.bad_references(), key=lambda bad: (bad[0], bad[1]))
        return [["error", "unknown-reference", *bad] for bad in rows]

    def graph_edges(self) -> set[tuple[str, str]]:
        """(user, target) for every reference that points somewhere."""
        bad = {(address, key) for address, key, _ in self.bad_references()}
        return {
            (address, parsed[0])
            for address, attributes in self.want.items()
            for key, value in attributes.items()
            if (parsed := self.parse(value)) and (address, key) not in bad
        }

    def reach_table(self) -> dict[tuple[str, str], bool]:
        nodes = sorted(self.want)
        edges = self.graph_edges()
        table = {(a, b): (a, b) in edges for a in nodes for b in nodes}
        for middle in nodes:
            for a in nodes:
                for b in nodes:
                    if table[(a, middle)] and table[(middle, b)]:
                        table[(a, b)] = True
        return table

    def cycle_groups(self) -> list[list[str]]:
        table = self.reach_table()
        looped = [a for a in sorted(self.want) if table[(a, a)]]
        groups = {tuple(b for b in looped if table[(a, b)] and table[(b, a)]) for a in looped}
        return sorted(list(group) for group in groups)

    def cycle_rows(self) -> list[list[str]]:
        return [["error", "cycle", *group] for group in self.cycle_groups()]

    def errors(self) -> list[list[str]]:
        return self.unknown_rows() + self.cycle_rows()

    def depends(self, address: str) -> set[str]:
        return {parsed[0] for value in self.want[address].values() if (parsed := self.parse(value))}

    def reference_value(self, target: str, key: str) -> str:
        if self.is_comp(target, key):
            if self.action(target) in ("create", "replace"):
                return UNKNOWN
            return self.have[target][key]
        return self.resolved(target, key)

    def resolved(self, address: str, key: str) -> str:
        if (address, key) not in self.memo_value:
            value = self.want[address][key]
            parsed = self.parse(value)
            self.memo_value[(address, key)] = (
                value if parsed is None else self.reference_value(*parsed)
            )
        return self.memo_value[(address, key)]

    def wanted(self, address: str) -> dict[str, str]:
        return {key: self.resolved(address, key) for key in self.want[address]}

    def actual(self, address: str) -> dict[str, str]:
        return {k: v for k, v in self.have[address].items() if not self.is_comp(address, k)}

    def forces(self, address: str, key: str) -> bool:
        return (self.kind(address), key) in self.forced

    def action(self, address: str) -> str:
        if address not in self.memo_action:
            self.memo_action[address] = self.decide(address)
        return self.memo_action[address]

    def decide(self, address: str) -> str:
        if address not in self.have:
            return "create"
        rows = self.change_rows(self.wanted(address), self.actual(address))
        if not rows:
            return "no-op"
        return "replace" if any(self.forces(address, row[1]) for row in rows) else "update"

    # --- level 3
    def force_replacement(self, kind: str, key: str) -> bool:
        new = (kind, key) not in self.forced
        self.forced.add((kind, key))
        return new

    def computed(self, kind: str, key: str) -> bool:
        new = (kind, key) not in self.comp
        self.comp.add((kind, key))
        return new

    def create_before_destroy(self, address: str) -> bool:
        new = address not in self.marks
        self.marks.add(address)
        return new

    def comp_keys(self, address: str) -> list[str]:
        return [key for kind, key in self.comp if kind == self.kind(address)]

    def create_first(self) -> set[str]:
        table = self.reach_table()
        marked = {mark for mark in self.marks if mark in self.want}
        return marked | {b for a in marked for b in self.want if table[(a, b)]}

    def mark_forcing(self, address: str, rows: list[list[str]]) -> list[list[str]]:
        return [
            [*row, "forces-replacement"] if self.forces(address, row[1]) else row for row in rows
        ]

    def apply_step(self, address: str) -> Step:
        action = self.action(address)
        if action == "create":
            step = Step("create", address)
            rows = [["+", key, value] for key, value in self.wanted(address).items()]
            step.rows = self.sorted_rows(rows + self.unknown_comp_rows(address, {}))
        elif action == "replace":
            step = Step("create", address, "replace")
            rows = self.mark_forcing(
                address, self.change_rows(self.wanted(address), self.actual(address))
            )
            step.rows = self.sorted_rows(rows + self.unknown_comp_rows(address, self.have[address]))
        elif action == "update":
            step = Step("update", address)
            step.rows = self.sorted_rows(
                self.change_rows(self.wanted(address), self.actual(address))
            )
        else:
            step = Step("no-op", address)
        return step

    def unknown_comp_rows(self, address: str, actual: dict[str, str]) -> list[list[str]]:
        return [
            ["~", key, actual[key], UNKNOWN] if key in actual else ["+", key, UNKNOWN]
            for key in self.comp_keys(address)
        ]

    def steps(self) -> list[Step]:
        early = self.create_first()
        result = [self.apply_step(address) for address in self.want]
        for address in self.want:
            if self.action(address) == "replace":
                step = Step("delete", address, "replace")
                step.order = CREATE_FIRST if address in early else DELETE_FIRST
                result.append(step)
        for address in self.have:
            if address not in self.want:
                step = Step("delete", address)
                step.rows = self.gone_rows(self.have[address])
                result.append(step)
        for address in self.old:
            step = Step("delete", address, "old")
            step.rows = self.gone_rows(self.old[address])
            result.append(step)
        return result

    def rule1(self, by: dict, deletes: dict) -> set[tuple[Step, Step]]:
        return {(by[target], by[user]) for user, target in self.graph_edges()}

    def links_of(self, step: Step) -> set[str]:
        held = self.old_links if step.tag == "old" else self.links
        return {target for user, target in held if user == step.address}

    def rule2(self, by: dict, deletes: dict) -> set[tuple[Step, Step]]:
        return {
            (step, gone)
            for held in deletes.values()
            for step in held
            for target in self.links_of(step)
            for gone in deletes.get(target, [])
        }

    def rule3(self, by: dict, deletes: dict) -> set[tuple[Step, Step]]:
        pairs = set()
        for address, held in deletes.items():
            for step in held:
                if step.order == DELETE_FIRST:
                    pairs.add((step, by[address]))
                elif step.order == CREATE_FIRST:
                    pairs.add((by[address], step))
        return pairs

    @staticmethod
    def replaced_again(target: str, deletes: dict) -> bool:
        return any(step.tag == "replace" for step in deletes.get(target, []))

    def holds_back(self, gone: Step, deletes: dict) -> bool:
        """Whether rule 4 makes the users of an address wait for this delete of it."""
        if gone.order == DELETE_FIRST:
            return False
        return not (gone.tag == "old" and self.replaced_again(gone.address, deletes))

    def rule4(self, by: dict, deletes: dict) -> set[tuple[Step, Step]]:
        return {
            (by[user], gone)
            for user, target in self.links
            if user in by and user in self.have
            for gone in deletes.get(target, [])
            if self.holds_back(gone, deletes)
        }

    def rule5(self, by: dict, deletes: dict) -> set[tuple[Step, Step]]:
        pairs = set()
        for address, held in deletes.items():
            for old in (step for step in held if step.tag == "old"):
                for other in (step for step in held if step.tag != "old"):
                    pairs.add((old, other))
                    if other.tag == "replace":
                        pairs.add((old, by[address]))
        return pairs

    def before(self, items: list[Step]) -> set[tuple[Step, Step]]:
        by = {step.address: step for step in items if step.verb != "delete"}
        deletes: dict[str, list[Step]] = {}
        for step in items:
            if step.verb == "delete":
                deletes.setdefault(step.address, []).append(step)
        rules = (self.rule1, self.rule2, self.rule3, self.rule4, self.rule5)
        return set().union(*(rule(by, deletes) for rule in rules))

    def pick(self, ready: list[Step]) -> Step:
        return min(ready, key=lambda step: (self.rank(step), self.sort_key(step.address)))

    def ordered(self, items: list[Step]) -> list[Step]:
        pairs = self.before(items)
        placed: list[Step] = []
        while len(placed) < len(items):
            ready = [
                step
                for step in items
                if step not in placed
                and all(first in placed for first, second in pairs if second is step)
            ]
            if not ready:
                return placed
            placed.append(self.pick(ready))
        return placed

    # --- level 4
    def apply(self, failures: list[list[str]], values: list[list[str]]) -> list[list[str]]:
        self.forget()
        errors = self.errors()
        if errors:
            return errors
        items = self.ordered(self.steps())
        pairs = self.before(items)
        failing = {tuple(pair) for pair in failures}
        picked = {(a, k): v for a, k, v in values}
        outcome: dict[Step, str] = {}
        rows = []
        for step in items:
            outcome[step] = self.outcome(step, pairs, outcome, failing)
            if outcome[step] == "ok":
                self.perform(step, picked)
            rows.append([step.verb, step.address, outcome[step]])
        return rows

    def outcome(self, step: Step, pairs, outcome: dict, failing: set) -> str:
        if any(outcome[first] != "ok" for first, second in pairs if second is step):
            return "skipped"
        if step.verb != "no-op" and (step.verb, step.address) in failing:
            return "failed"
        return "ok"

    def forget(self) -> None:
        """Resolved values and actions are memoized while one plan is computed."""
        self.memo_value.clear()
        self.memo_action.clear()

    def live(self, address: str, key: str) -> str:
        parsed = self.parse(self.want[address][key])
        if parsed is None:
            return self.want[address][key]
        target, wanted_key = parsed
        if self.is_comp(target, wanted_key):
            return self.have[target][wanted_key]
        return self.live(target, wanted_key)

    def built(self, address: str, picked: dict) -> dict[str, str]:
        made = {key: self.live(address, key) for key in self.want[address]}
        made.update({key: picked[(address, key)] for key in self.comp_keys(address)})
        return made

    def record_links(self, address: str) -> None:
        self.links = {(u, t) for u, t in self.links if u != address}
        self.links |= {(address, target) for target in self.depends(address)}

    def perform(self, step: Step, picked: dict) -> None:
        address = step.address
        if step.verb == "create":
            if step.tag == "replace" and address in self.have:
                self.old[address] = self.have[address]
                self.old_links |= {(u, t) for u, t in self.links if u == address}
            self.have[address] = self.built(address, picked)
            self.record_links(address)
        elif step.verb == "update":
            kept = {k: v for k, v in self.have[address].items() if self.is_comp(address, k)}
            self.have[address] = {
                **{key: self.live(address, key) for key in self.want[address]},
                **kept,
            }
            self.record_links(address)
        elif step.verb == "delete":
            if step.tag == "old" or step.order == CREATE_FIRST:
                self.old.pop(address)
                self.old_links = {(u, t) for u, t in self.old_links if u != address}
            else:
                self.have.pop(address)
                self.links = {(u, t) for u, t in self.links if u != address}

    def state(self) -> list[list[str]]:
        rows = []
        for address in sorted(self.have.keys() | self.old.keys(), key=self.sort_key):
            for role, objects in (("current", self.have), ("old", self.old)):
                if address in objects:
                    pairs = sorted(objects[address].items(), key=lambda kv: self.sort_key(kv[0]))
                    rows.append([address, role, *(part for pair in pairs for part in pair)])
        return rows


# ------------------------------------------------------------------ level 1 mistakes
class DesireMerges(Model):
    """Keeps the keys of an earlier desire."""

    def desire(self, address: str, attributes: list[list[str]]) -> bool:
        new = address not in self.want
        self.want[address] = {**self.want.get(address, {}), **pairs(attributes)}
        return new


class ObserveMerges(Model):
    """Keeps the keys of an earlier observe."""

    def observe(self, address: str, attributes: list[list[str]]) -> bool:
        new = address not in self.have
        self.have[address] = {**self.have.get(address, {}), **pairs(attributes)}
        return new


class RemoveAlwaysTrue(Model):
    """Says yes to removing an address that was never desired."""

    def remove(self, address: str) -> bool:
        self.want.pop(address, None)
        return True


class DeletesAmongTheOthers(Model):
    """Sorts deletes by address with everything else."""

    def rank(self, step: Step) -> int:
        return 0


class NaturalSort(Model):
    """Sorts the digits in a text by their numeric value."""

    def sort_key(self, text: str) -> Any:
        return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", text)]


class ValuesIgnoreCase(Model):
    """Compares values without regard to case."""

    def same(self, first: str | None, second: str | None) -> bool:
        if first is None or second is None:
            return first == second
        return first.lower() == second.lower()


class ValuesAsNumbers(Model):
    """Compares values that look like numbers by their numeric value."""

    def same(self, first: str | None, second: str | None) -> bool:
        try:
            return float(first) == float(second)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return first == second


class OnlyDesiredKeysCompared(Model):
    """Ignores keys that only the actual resource has."""

    def keys_compared(self, wanted: dict[str, str], actual: dict[str, str]) -> set[str]:
        return set(wanted)


class RowsInInputOrder(Model):
    """Lists attribute rows in the order the keys were given."""

    def sorted_rows(self, rows: list[list[str]]) -> list[list[str]]:
        return rows


class DeleteListsNoAttributes(Model):
    """Gives a delete no attribute rows."""

    def gone_rows(self, attributes: dict[str, str]) -> list[list[str]]:
        return []


# ------------------------------------------------------------------ level 2 mistakes
class ReferencesComparedAsText(Model):
    """Compares and prints the reference text instead of the resolved value."""

    def resolved(self, address: str, key: str) -> str:
        return self.want[address][key]


class ReferencesReadTheActualTarget(Model):
    """Resolves a reference to the target's actual value when it has one."""

    def reference_value(self, target: str, key: str) -> str:
        if target in self.have and key in self.have[target]:
            return self.have[target][key]
        return super().reference_value(target, key)


class DependentsFirst(Model):
    """Puts a resource before the resources it refers to."""

    def rule1(self, by: dict, deletes: dict) -> set[tuple[Step, Step]]:
        return {(later, earlier) for earlier, later in super().rule1(by, deletes)}


class OrderByDepth(Model):
    """Orders by the length of the longest chain of references, then by address."""

    def pick(self, ready: list[Step]) -> Step:
        def depth(address: str) -> int:
            if address not in self.want:
                return 0
            return 1 + max((depth(t) for t in self.depends(address) if t != address), default=-1)

        return min(ready, key=lambda s: (self.rank(s), depth(s.address), s.address))


class TiesInInsertionOrder(Model):
    """Breaks ties by the order in which resources were declared."""

    def pick(self, ready: list[Step]) -> Step:
        known = [*self.want, *self.have, *self.old]
        return min(ready, key=lambda step: (self.rank(step), known.index(step.address)))


class DeletesNotReversed(Model):
    """Ignores recorded links and deletes by address."""

    def rule2(self, by: dict, deletes: dict) -> set[tuple[Step, Step]]:
        return set()


class DeletesInReversedCreationOrder(Model):
    """Deletes in the exact reverse of the order the deleted resources would be created in."""

    def ordered(self, items: list[Step]) -> list[Step]:
        placed = super().ordered(items)
        plain = {step.address: step for step in placed if step.verb == "delete" and not step.tag}
        forward: list[str] = []
        while len(forward) < len(plain):
            ready = [
                address
                for address in plain
                if address not in forward
                and all(t in forward for u, t in self.links if u == address and t in plain)
            ]
            forward.append(min(ready))
        rest = [step for step in placed if step.address not in plain or step.tag]
        return rest + [plain[address] for address in reversed(forward)]


class ActualTargetsCount(Model):
    """Accepts a reference to a resource that is only actual."""

    def target_exists(self, target: str, key: str) -> bool:
        return target in self.have or super().target_exists(target, key)

    def reference_value(self, target: str, key: str) -> str:
        if target not in self.want:
            return self.have[target][key]
        return super().reference_value(target, key)


class ReferencedKeyNotChecked(Model):
    """Accepts a reference to any key of a desired resource."""

    def target_exists(self, target: str, key: str) -> bool:
        return target in self.want


class SelfReferenceIsNoCycle(Model):
    """Finds cycles of two or more resources only."""

    def cycle_groups(self) -> list[list[str]]:
        return [group for group in super().cycle_groups() if len(group) > 1]


class OneRowForAllCycles(Model):
    """Puts every resource on a cycle into one row."""

    def cycle_groups(self) -> list[list[str]]:
        groups = super().cycle_groups()
        return [sorted(a for group in groups for a in group)] if groups else []


class ReachingACycleCounts(Model):
    """Adds to a group the resources that only lead into it."""

    def cycle_groups(self) -> list[list[str]]:
        table = self.reach_table()
        groups = super().cycle_groups()
        return sorted(
            sorted({*group, *(a for a in self.want if table[(a, group[0])])}) for group in groups
        )


class BrokenReferencesCloseCycles(Model):
    """Follows references that point nowhere when looking for cycles."""

    def graph_edges(self) -> set[tuple[str, str]]:
        edges = set()
        for address, attributes in self.want.items():
            for value in attributes.values():
                parsed = self.parse(value)
                if parsed and parsed[0] in self.want:
                    edges.add((address, parsed[0]))
        return edges


class CyclesFirst(Model):
    """Lists cycle rows before unknown references."""

    def errors(self) -> list[list[str]]:
        return self.cycle_rows() + self.unknown_rows()


class UnknownRowsByKey(Model):
    """Sorts unknown-reference rows by key before address."""

    def unknown_rows(self) -> list[list[str]]:
        rows = sorted(self.bad_references(), key=lambda bad: (bad[1], bad[0]))
        return [["error", "unknown-reference", *bad] for bad in rows]


class LinksToAnything(Model):
    """Records a link even when an address is not actual."""

    def observe_dependency(self, address: str, depends_on: str) -> bool:
        new = (address, depends_on) not in self.links
        self.links.add((address, depends_on))
        return new


class ObserveDropsLinks(Model):
    """Forgets the links of a resource that is observed again."""

    def observe(self, address: str, attributes: list[list[str]]) -> bool:
        self.links = {(u, t) for u, t in self.links if u != address}
        return super().observe(address, attributes)


# ------------------------------------------------------------------ level 3 mistakes
class ComputedKeysCompared(Model):
    """Compares computed keys like any other."""

    def actual(self, address: str) -> dict[str, str]:
        return dict(self.have[address])


class ComputedKeysNotListed(Model):
    """Leaves the computed keys out of a create and a replace."""

    def unknown_comp_rows(self, address: str, actual: dict[str, str]) -> list[list[str]]:
        return []


class ComputedRowsLast(Model):
    """Appends the computed rows after the sorted ones."""

    def apply_step(self, address: str) -> Step:
        step = super().apply_step(address)
        comp = {row[1] for row in self.unknown_comp_rows(address, {})}
        if step.verb == "create":
            step.rows = [r for r in step.rows if r[1] not in comp] + [
                r for r in step.rows if r[1] in comp
            ]
        return step


class DeleteHidesComputedKeys(Model):
    """Leaves computed keys out of a delete's rows."""

    def steps(self) -> list[Step]:
        result = super().steps()
        for step in result:
            if step.verb == "delete" and not step.tag:
                step.rows = [r for r in step.rows if not self.is_comp(step.address, r[1])]
        return result


class ForcedOnlyWhenChanged(Model):
    """Lets only a changed value force a replace, not an added or removed key."""

    def decide(self, address: str) -> str:
        if address not in self.have:
            return "create"
        rows = self.change_rows(self.wanted(address), self.actual(address))
        if not rows:
            return "no-op"
        forced = any(row[0] == "~" and self.forces(address, row[1]) for row in rows)
        return "replace" if forced else "update"


class EveryReplaceRowMarked(Model):
    """Marks every row of a replace as forcing it."""

    def mark_forcing(self, address: str, rows: list[list[str]]) -> list[list[str]]:
        return [[*row, "forces-replacement"] for row in rows]


class ForcedKeyOnAnyType(Model):
    """Lets a forced key force a replace on every type."""

    def forces(self, address: str, key: str) -> bool:
        return any(forced_key == key for _, forced_key in self.forced)


class ReplacedTargetIsAllUnknown(Model):
    """Makes every reference to a replaced resource unknown, not only its computed keys."""

    def reference_value(self, target: str, key: str) -> str:
        if self.action(target) == "replace":
            return UNKNOWN
        return super().reference_value(target, key)


class UnknownStopsAfterOneHop(Model):
    """Resolves a reference to an unknown value to the target's actual value instead."""

    def reference_value(self, target: str, key: str) -> str:
        value = super().reference_value(target, key)
        if value == UNKNOWN and not self.is_comp(target, key) and target in self.have:
            return self.have[target].get(key, value)
        return value


class UpdatedTargetLendsUnknown(Model):
    """Makes a reference to a computed key unknown whenever the target changes at all."""

    def reference_value(self, target: str, key: str) -> str:
        if self.is_comp(target, key) and self.action(target) != "no-op":
            return UNKNOWN
        return super().reference_value(target, key)


class MarkDoesNotSpread(Model):
    """Applies the mark only to the marked address."""

    def create_first(self) -> set[str]:
        return {mark for mark in self.marks if mark in self.want}


class MarkSpreadsToDependents(Model):
    """Spreads the mark to the resources that depend on the marked one."""

    def create_first(self) -> set[str]:
        table = self.reach_table()
        marked = {mark for mark in self.marks if mark in self.want}
        return marked | {a for b in marked for a in self.want if table[(a, b)]}


class NoRuleFour(Model):
    """Lets an old resource go before its users have moved."""

    def rule4(self, by: dict, deletes: dict) -> set[tuple[Step, Step]]:
        return set()


class RuleFourForEveryDelete(Model):
    """Makes users move before any delete, even the delete of a delete-first replace."""

    def holds_back(self, gone: Step, deletes: dict) -> bool:
        return True


class RuleTwoOnlyForPlainDeletes(Model):
    """Orders by recorded links only the deletes that are not part of a replace."""

    def rule2(self, by: dict, deletes: dict) -> set[tuple[Step, Step]]:
        return {
            (step, gone)
            for step, gone in super().rule2(by, deletes)
            if step.tag != "replace" and gone.tag != "replace"
        }


class MarkSpreadsOnlyFromReplaced(Model):
    """Spreads the mark only from a marked resource that is itself replaced."""

    def create_first(self) -> set[str]:
        table = self.reach_table()
        marked = {m for m in self.marks if m in self.want and self.action(m) == "replace"}
        return marked | {b for a in marked for b in self.want if table[(a, b)]}


# ------------------------------------------------------------------ level 4 mistakes
class StopsAtTheFirstFailure(Model):
    """Skips every step after a failure."""

    def outcome(self, step: Step, pairs, outcome: dict, failing: set) -> str:
        if any(value != "ok" for value in outcome.values()):
            return "skipped"
        return super().outcome(step, pairs, outcome, failing)


class SkipsOnlyBehindAFailure(Model):
    """Runs a step whose earlier step was skipped rather than failed."""

    def outcome(self, step: Step, pairs, outcome: dict, failing: set) -> str:
        if any(outcome[first] == "failed" for first, second in pairs if second is step):
            return "skipped"
        if step.verb != "no-op" and (step.verb, step.address) in failing:
            return "failed"
        return "ok"


class RecordsThePlannedValues(Model):
    """Writes the values the plan printed, unknowns included."""

    def live(self, address: str, key: str) -> str:
        return self.resolved(address, key)


class CreateDropsCloudValues(Model):
    """Records a created resource without the values the cloud picked."""

    def built(self, address: str, picked: dict) -> dict[str, str]:
        return {key: self.live(address, key) for key in self.want[address]}


class UpdateDropsComputedValues(Model):
    """Replaces every key on an update, computed ones included."""

    def perform(self, step: Step, picked: dict) -> None:
        if step.verb == "update":
            address = step.address
            self.have[address] = {k: self.live(address, k) for k in self.want[address]}
            self.record_links(step.address)
        else:
            super().perform(step, picked)


class UpdateKeepsDroppedKeys(Model):
    """Leaves keys that are no longer desired on an updated resource."""

    def perform(self, step: Step, picked: dict) -> None:
        if step.verb == "update":
            before = dict(self.have[step.address])
            super().perform(step, picked)
            self.have[step.address] = {**before, **self.have[step.address]}
        else:
            super().perform(step, picked)


class NoOldObject(Model):
    """Lets the create of a create-first replace overwrite the resource for good."""

    def perform(self, step: Step, picked: dict) -> None:
        if step.verb == "delete" and step.order == CREATE_FIRST:
            return
        if step.verb == "create" and step.tag == "replace":
            self.have[step.address] = self.built(step.address, picked)
            self.record_links(step.address)
            return
        super().perform(step, picked)


class LinksNotRecordedByApply(Model):
    """Leaves the recorded links alone when apply creates or updates."""

    def record_links(self, address: str) -> None:
        pass


class FailedStepIsRecorded(Model):
    """Records the effect of a step that failed."""

    def outcome(self, step: Step, pairs, outcome: dict, failing: set) -> str:
        result = super().outcome(step, pairs, outcome, failing)
        if result == "failed":
            self.perform(step, {})
        return result


class FailureOfANoOpCounts(Model):
    """Fails a no-op step that failures name."""

    def outcome(self, step: Step, pairs, outcome: dict, failing: set) -> str:
        result = super().outcome(step, pairs, outcome, failing)
        if result == "ok" and (step.verb, step.address) in failing:
            return "failed"
        return result


class NoOpsLeftOutOfApply(Model):
    """Lists only the steps that change something."""

    def apply(self, failures: list[list[str]], values: list[list[str]]) -> list[list[str]]:
        rows = super().apply(failures, values)
        return [row for row in rows if row[0] != "no-op"]


class StateHidesOldObjects(Model):
    """Lists only the current resources."""

    def state(self) -> list[list[str]]:
        return [row for row in super().state() if row[1] == "current"]


class OneDeletePerAddress(Model):
    """Keeps only the old object's delete at an address that has one."""

    def steps(self) -> list[Step]:
        return [
            step
            for step in super().steps()
            if not (step.verb == "delete" and step.tag != "old" and step.address in self.old)
        ]


class OldObjectNotFirst(Model):
    """Leaves the old object's delete unordered against the other steps of its address."""

    def rule5(self, by: dict, deletes: dict) -> set[tuple[Step, Step]]:
        return set()


class OldObjectWaitsForUsersEvenWhenReplacedAgain(Model):
    """Holds the old object's delete for the users of an address that is replaced again."""

    def holds_back(self, gone: Step, deletes: dict) -> bool:
        return gone.order != DELETE_FIRST


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
    except (IndexError, KeyError, ValueError, TypeError, RecursionError, AttributeError):
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


def test_the_hidden_cases_reach_every_outcome_and_step_kind():
    outcomes, heads = set(), set()
    for case in HIDDEN_CASES:
        for op, got in zip(case["ops"], case["expected"], strict=True):
            if op == "apply" and got and got[0][0] != "error":
                outcomes.update(row[2] for row in got)
            if op == "plan":
                heads.update(tuple(row[2:]) for row in got if row[0] in ("create", "delete"))
    assert outcomes == {"ok", "failed", "skipped"}
    assert {(), ("replace",), ("old",)} <= heads
