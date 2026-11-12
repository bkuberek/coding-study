"""lineage-graph promises that its hidden cases catch the classic mistakes of column-level lineage:
specs accepted with a bad part, unknown inputs reported under the wrong code or checked too early,
cycles missed or split, walks in the wrong direction or order, filters left out of dependencies,
changes that travel too far or not far enough, direct and derived use told apart by the wrong
rule, and sensitivity labels that leak through masked or filtering edges, stop at aggregates or
after one hop, or are exposed without the source behind them. These tests replay every case
against a model of the graph written from the statement, which must give every expected output,
and against that model with one mistake planted at a time, which some hidden case must fail. The
model relaxes distances over a set of edges until nothing changes and finds cycles from a
transitive closure, where the reference walks adjacency lists breadth first and groups cycles
with Kosaraju's algorithm. A mistake that crashes fails its case, as a thrown exception does in
the grader."""

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0338-lineage-graph"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
SCRIPTED_CASES = [case for case in CASES if "ops" in case]
HIDDEN_CASES = [case for case in SCRIPTED_CASES if not case.get("visible", False)]
USAGES = ("identity", "transform", "aggregate", "filter")
Edge = tuple[str, str, str, bool]
COLUMN_REF = re.compile(r"[^.]+\.[^.]+")


class Model:
    """The graph as the statement words it: a set of edges `(input, output, usage, masking)`.
    Distances come from relaxing every edge until nothing changes. Each mistake below overrides
    one rule."""

    def __init__(self) -> None:
        self.datasets: dict[str, list[str]] = {}
        self.edges: list[Edge] = []
        self.labels: dict[str, set[str]] = {}
        self.published: set[str] = set()

    # --- rules
    def edge_ok(self, edge: list[str], columns: list[str]) -> bool:
        if len(edge) not in (3, 4) or edge[0] not in columns:
            return False
        if not self.reference_ok(edge[1]) or not self.usage_ok(edge[2]):
            return False
        if len(edge) == 4:
            return edge[3] == "masking" and self.may_mask(edge[2])
        return True

    def reference_ok(self, text: str) -> bool:
        return COLUMN_REF.fullmatch(text) is not None

    def usage_ok(self, usage: str) -> bool:
        return usage in USAGES

    def may_mask(self, usage: str) -> bool:
        return usage in ("transform", "aggregate")

    def name_taken(self, name: str) -> bool:
        return name in self.datasets

    def pairs_ok(self, edges: list[list[str]]) -> bool:
        pairs = [(edge[0], edge[1]) for edge in edges]
        return len(set(pairs)) == len(pairs)

    def unknown(self, edge: Edge) -> str | None:
        dataset, column = edge[0].split(".")
        if dataset not in self.datasets:
            return "unknown-dataset"
        return None if column in self.datasets[dataset] else "unknown-column"

    def reaches(self) -> set[tuple[str, str]]:
        closure = {(e[0], e[1]) for e in self.edges}
        while True:
            more = {(a, d) for a, b in closure for c, d in closure if b == c} - closure
            if not more:
                return closure
            closure |= more

    def cycle_groups(self) -> list[list[str]]:
        closure = self.reaches()
        on_cycle = sorted({a for a, b in closure if a == b})
        groups: list[list[str]] = []
        for node in on_cycle:
            if not any(node in group for group in groups):
                groups.append(sorted(m for m in on_cycle if (node, m) in closure))
        return groups

    def order_issues(self, issues: list[list[str]]) -> list[list[str]]:
        return sorted(issues)

    def depends(self, edge: Edge) -> bool:
        return True

    def distances(self, start: str, forward: bool, keep: Any = None) -> dict[str, int]:
        keep = keep or self.depends
        hops = [(e[0], e[1]) if forward else (e[1], e[0]) for e in self.edges if keep(e)]
        best: dict[str, int] = {}
        changed = True
        while changed:
            changed = False
            for a, b in hops:
                here = 0 if a == start else best.get(a)
                if here is not None and (b not in best or here + 1 < best[b]):
                    best[b] = here + 1
                    changed = True
        return best

    def ordered(self, best: dict[str, int]) -> list[str]:
        return sorted(best, key=lambda name: (best[name], name))

    def typed(self, column: str) -> dict[str, int]:
        found = self.distances(column, True, lambda e: e[2] == "identity")
        found[column] = 0
        return found

    def affected(self, column: str, change: str) -> dict[str, int]:
        if change == "drop":
            return self.distances(column, True)
        if change == "rename":
            return {e[1]: 1 for e in self.edges if e[0] == column}
        typed = self.typed(column)
        result: dict[str, int] = {}
        for a, b, _, _ in self.edges:
            if a in typed:
                result[b] = min(result.get(b, typed[a] + 1), typed[a] + 1)
        return result

    def use(self, column: str, distance: int, change: str) -> str:
        return "direct" if distance == 1 else "derived"

    def unsafe_for_retype(self, usage: str) -> bool:
        return usage != "identity"

    def carries(self, edge: Edge) -> bool:
        return edge[2] != "filter" and not edge[3]

    def declared(self, column: str) -> bool:
        if not self.reference_ok(column):
            return False
        dataset, name = column.split(".")
        return name in self.datasets.get(dataset, [])

    def label_reach(self, source: str) -> set[str]:
        return {source} | set(self.distances(source, True, self.carries))

    def exposure_rows(self, label: str) -> list[list[str]]:
        rows = []
        for source in sorted(self.labels):
            if label in self.labels[source]:
                for column in self.label_reach(source):
                    if column.split(".")[0] in self.published:
                        rows.append([column, source])
        return rows

    # --- level 1
    def add_dataset(self, name: str, columns: list[str], edges: list[list[str]]) -> bool:
        if self.name_taken(name) or len(set(columns)) != len(columns):
            return False
        if not all(self.edge_ok(edge, columns) for edge in edges) or not self.pairs_ok(edges):
            return False
        self.datasets[name] = list(columns)
        self.edges += [(e[1], f"{name}.{e[0]}", e[2], len(e) == 4) for e in edges]
        return True

    def validate(self) -> list[list[str]]:
        issues = [
            [code, edge[1], edge[0]]
            for edge in self.edges
            if (code := self.unknown(edge)) is not None
        ]
        issues += [["cycle", *group] for group in self.cycle_groups()]
        return self.order_issues(issues)

    def inputs_of(self, column: str) -> list[str]:
        return sorted(e[0] for e in self.edges if e[1] == column)

    # --- level 2
    def upstream(self, column: str) -> list[str]:
        return self.ordered(self.distances(column, False))

    def downstream(self, column: str) -> list[str]:
        return self.ordered(self.distances(column, True))

    # --- level 3
    def impact(self, column: str, change: str) -> list[list[str]]:
        found = self.affected(column, change)
        return [[name, self.use(name, found[name], change)] for name in self.ordered(found)]

    def is_breaking(self, column: str, change: str) -> bool:
        if change != "retype":
            return bool(self.affected(column, change))
        typed = self.typed(column)
        return any(e[0] in typed and self.unsafe_for_retype(e[2]) for e in self.edges)

    def impacted_datasets(self, column: str, change: str) -> list[str]:
        return sorted({name.split(".")[0] for name in self.affected(column, change)})

    # --- level 4
    def tag(self, column: str, label: str) -> bool:
        if not self.declared(column) or label in self.labels.get(column, set()):
            return False
        self.labels.setdefault(column, set()).add(label)
        return True

    def tags_of(self, column: str) -> list[str]:
        found = set()
        for source, labels in self.labels.items():
            if column in self.label_reach(source):
                found |= labels
        return sorted(found)

    def publish(self, dataset: str) -> bool:
        if dataset not in self.datasets or dataset in self.published:
            return False
        self.published.add(dataset)
        return True

    def exposures(self, label: str) -> list[list[str]]:
        return sorted(self.exposure_rows(label))


# ------------------------------------------------------------------ level 1 mistakes
class SecondDatasetReplacesTheFirst(Model):
    """Accepts a dataset name that is already declared."""

    def name_taken(self, name: str) -> bool:
        self.datasets.pop(name, None)
        self.edges = [e for e in self.edges if not e[1].startswith(f"{name}.")]
        return False


class RepeatedColumnAccepted(Model):
    """Accepts a column listed twice."""

    def add_dataset(self, name: str, columns: list[str], edges: list[list[str]]) -> bool:
        return super().add_dataset(name, list(dict.fromkeys(columns)), edges)


class UnknownOutputAccepted(Model):
    """Accepts an edge whose output is not a column of the dataset."""

    def edge_ok(self, edge: list[str], columns: list[str]) -> bool:
        return super().edge_ok(edge, [*columns, edge[0]] if edge else columns)


class MalformedInputAccepted(Model):
    """Accepts an input that is not `dataset.column`."""

    def reference_ok(self, text: str) -> bool:
        return text != ""


class UsageIgnoresCase(Model):
    """Accepts a usage written in any case."""

    def usage_ok(self, usage: str) -> bool:
        return usage.lower() in USAGES


class AnyUsageMayMask(Model):
    """Accepts masking on identity and filter edges."""

    def may_mask(self, usage: str) -> bool:
        return True


class SamePairTwiceAccepted(Model):
    """Accepts two edges between the same input and output."""

    def pairs_ok(self, edges: list[list[str]]) -> bool:
        return True


class EveryUnknownIsAColumn(Model):
    """Reports a missing dataset as a missing column."""

    def unknown(self, edge: Edge) -> str | None:
        return None if super().unknown(edge) is None else "unknown-column"


class InputsCheckedWhenAdded(Model):
    """Checks inputs when a dataset is added, so a dataset declared later never clears it."""

    def add_dataset(self, name: str, columns: list[str], edges: list[list[str]]) -> bool:
        before = len(self.edges)
        added = super().add_dataset(name, columns, edges)
        if added:
            self.early = getattr(self, "early", []) + [
                [code, edge[1], edge[0]]
                for edge in self.edges[before:]
                if (code := self.unknown(edge)) is not None
            ]
        return added

    def validate(self) -> list[list[str]]:
        cycles = [issue for issue in super().validate() if issue[0] == "cycle"]
        return sorted(getattr(self, "early", []) + cycles)


class CycleMembersOneByOne(Model):
    """Reports each column on a cycle as its own issue."""

    def cycle_groups(self) -> list[list[str]]:
        return [[member] for group in super().cycle_groups() for member in group]


class SelfLoopIsNoCycle(Model):
    """Misses a column that reads itself."""

    def cycle_groups(self) -> list[list[str]]:
        return [group for group in super().cycle_groups() if len(group) > 1]


class IssuesInTheOrderFound(Model):
    """Lists the issues in the order the edges were added, cycles last."""

    def order_issues(self, issues: list[list[str]]) -> list[list[str]]:
        return issues


# ------------------------------------------------------------------ level 2 mistakes
class OrderedByNameOnly(Model):
    """Sorts a walk's answer by name, ignoring distance."""

    def ordered(self, best: dict[str, int]) -> list[str]:
        return sorted(best)


class LongestDistance(Model):
    """Orders by the longest path instead of the shortest."""

    def distances(self, start: str, forward: bool, keep: Any = None) -> dict[str, int]:
        best = super().distances(start, forward, keep)
        keep = keep or self.depends
        hops = [(e[0], e[1]) if forward else (e[1], e[0]) for e in self.edges if keep(e)]
        longest = dict(best)
        for _ in range(len(hops)):
            for a, b in hops:
                here = 0 if a == start else longest.get(a)
                if here is not None and b in longest and here + 1 > longest[b] and b != start:
                    longest[b] = here + 1
        return longest


class StartAlwaysIncluded(Model):
    """Lists the column itself in its own walk."""

    def distances(self, start: str, forward: bool, keep: Any = None) -> dict[str, int]:
        best = super().distances(start, forward, keep)
        return {start: 0, **best} if best else best


class StartNeverIncluded(Model):
    """Leaves the column out of its own walk, even on a cycle."""

    def distances(self, start: str, forward: bool, keep: Any = None) -> dict[str, int]:
        best = super().distances(start, forward, keep)
        best.pop(start, None)
        return best


class FiltersAreNoDependency(Model):
    """Leaves filter inputs out of upstream and downstream."""

    def depends(self, edge: Edge) -> bool:
        return edge[2] != "filter"


class DirectionsSwapped(Model):
    """Walks consumers for upstream and inputs for downstream."""

    def upstream(self, column: str) -> list[str]:
        return super().downstream(column)

    def downstream(self, column: str) -> list[str]:
        return super().upstream(column)


class UndeclaredNamesSkipped(Model):
    """Never walks into or out of a column that no dataset declares."""

    def depends(self, edge: Edge) -> bool:
        return self.declared(edge[0]) and self.declared(edge[1])


# ------------------------------------------------------------------ level 3 mistakes
class RetypeTravelsEverywhere(Model):
    """Treats a retype like a drop."""

    def affected(self, column: str, change: str) -> dict[str, int]:
        return super().affected(column, "drop" if change == "retype" else change)


class RetypeStopsAtOneHop(Model):
    """Treats a retype like a rename."""

    def affected(self, column: str, change: str) -> dict[str, int]:
        return super().affected(column, "rename" if change == "retype" else change)


class RenameTravelsEverywhere(Model):
    """Treats a rename like a drop."""

    def affected(self, column: str, change: str) -> dict[str, int]:
        return super().affected(column, "drop" if change == "rename" else change)


class DirectMeansIdentity(Model):
    """Calls a use direct when it copies the value, derived otherwise."""

    def use(self, column: str, distance: int, change: str) -> str:
        identity = any(e[1] == column and e[2] == "identity" for e in self.edges)
        return "direct" if identity else "derived"


class FilterIsSafeForRetype(Model):
    """Lets a filter read a retyped column without breaking."""

    def unsafe_for_retype(self, usage: str) -> bool:
        return usage not in ("identity", "filter")


class EveryRetypeBreaks(Model):
    """Calls any retype that reaches a column breaking."""

    def unsafe_for_retype(self, usage: str) -> bool:
        return True


class OwnDatasetImpacted(Model):
    """Counts the changed column's own dataset as impacted."""

    def impacted_datasets(self, column: str, change: str) -> list[str]:
        found = super().impacted_datasets(column, change)
        return sorted({*found, column.split(".")[0]}) if found else found


# ------------------------------------------------------------------ level 4 mistakes
class MaskingIgnored(Model):
    """Lets labels pass masked edges."""

    def carries(self, edge: Edge) -> bool:
        return edge[2] != "filter"


class FiltersCarryLabels(Model):
    """Lets labels pass filter edges."""

    def carries(self, edge: Edge) -> bool:
        return not edge[3]


class AggregatesAlwaysMask(Model):
    """Stops labels at every aggregate."""

    def carries(self, edge: Edge) -> bool:
        return super().carries(edge) and edge[2] != "aggregate"


class LabelsTravelOneHop(Model):
    """Passes a label to the direct consumers only."""

    def label_reach(self, source: str) -> set[str]:
        return {source} | {e[1] for e in self.edges if e[0] == source and self.carries(e)}


class OwnLabelsForgotten(Model):
    """Reports only the labels a column inherits."""

    def tags_of(self, column: str) -> list[str]:
        found = set()
        for source, labels in self.labels.items():
            if source != column and column in self.label_reach(source):
                found |= labels
        return sorted(found)


class UndeclaredColumnsTakeLabels(Model):
    """Labels any name, declared or not."""

    def declared(self, column: str) -> bool:
        return True


class SecondLabelIsNew(Model):
    """Accepts a label a column already has."""

    def tag(self, column: str, label: str) -> bool:
        if not self.declared(column):
            return False
        self.labels.setdefault(column, set()).add(label)
        return True


class PublishTwiceIsNew(Model):
    """Accepts publishing a dataset that is already published."""

    def publish(self, dataset: str) -> bool:
        if dataset not in self.datasets:
            return False
        self.published.add(dataset)
        return True


class EveryColumnExposes(Model):
    """Reports labelled columns whether or not their dataset is published."""

    def exposure_rows(self, label: str) -> list[list[str]]:
        published = self.published
        self.published = set(self.datasets)
        rows = super().exposure_rows(label)
        self.published = published
        return rows


class SourceDoesNotExposeItself(Model):
    """Leaves out a tagged column of a published dataset."""

    def label_reach(self, source: str) -> set[str]:
        return super().label_reach(source) - {source} | (
            {source} if (source, source) in self.reaches() else set()
        )


class FirstSourceOnly(Model):
    """Reports one source per exposed column."""

    def exposure_rows(self, label: str) -> list[list[str]]:
        first: dict[str, str] = {}
        for column, source in super().exposure_rows(label):
            first.setdefault(column, source)
        return [[column, source] for column, source in first.items()]


class ExposuresBySource(Model):
    """Sorts exposures by source first."""

    def exposures(self, label: str) -> list[list[str]]:
        return sorted(self.exposure_rows(label), key=lambda row: (row[1], row[0]))


MISTAKES: Sequence[type[Model]] = Model.__subclasses__()


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", op).lower()


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


def test_the_hidden_cases_ask_every_change_and_both_answers():
    asked = {
        (arguments[1], got)
        for case in HIDDEN_CASES
        for op, arguments, got in zip(case["ops"], case["args"], case["expected"], strict=True)
        if op == "isBreaking"
    }
    assert asked == {
        (change, answer) for change in ("drop", "rename", "retype") for answer in (True, False)
    }
