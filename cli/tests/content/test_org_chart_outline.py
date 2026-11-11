"""org-chart-outline promises that its hidden cases catch the classic mistakes of building a tree
from flat rows: children sorted instead of kept in input order, rows assumed to arrive parents
first, orphans and cycles mishandled, chains and common managers that skip the person, an indent
or a sort that is not the one stated, and a recursion that runs out of stack. These tests replay
every case against a model of the chart written from the statement, which must give every
expected output, and against that model with one mistake planted at a time, which some hidden
case must fail. A mistake that crashes fails its case, as a thrown exception does in the grader."""

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0313-org-chart-outline"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
SCRIPTED_CASES = [case for case in CASES if "ops" in case]
HIDDEN_CASES = [case for case in SCRIPTED_CASES if not case.get("visible", False)]
INDENT = "  "


class Model:
    """The chart as the statement words it, one rule per method, so that each mistake below
    overrides a single method. It keeps the rows as given and answers by looking at them."""

    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str]] = []
        self.parent: dict[str, str] = {}
        self.name: dict[str, str] = {}

    # --- what a row is
    def known(self, employee: str) -> bool:
        return employee in self.parent

    def is_root(self, employee: str) -> bool:
        return self.parent[employee] == ""

    def is_orphan(self, employee: str) -> bool:
        parent = self.parent[employee]
        return parent != "" and not self.known(parent)

    def top_of(self, employee: str) -> str | None:
        """The root or orphan above a row, or None when the parent links go round a cycle."""
        current = employee
        for _ in range(len(self.rows) + 1):
            if self.is_root(current) or self.is_orphan(current):
                return current
            current = self.parent[current]
        return None

    def attached(self, employee: str) -> bool:
        return self.known(employee) and self.top_of(employee) is not None

    def attached_ids(self) -> list[str]:
        return [row_id for row_id, _, _ in self.rows if self.attached(row_id)]

    # --- level 1
    def load(self, rows: list[list[str]]) -> None:
        self.rows = [(row[0], row[1], row[2]) for row in rows]
        self.parent = {row_id: parent for row_id, parent, _ in self.rows}
        self.name = {row_id: name for row_id, _, name in self.rows}

    def roots(self) -> list[str]:
        return [row_id for row_id, _, _ in self.rows if self.is_root(row_id)]

    def name_of(self, employee: str) -> str:
        return self.name.get(employee, "")

    def reports_of(self, employee: str) -> list[str]:
        return [row_id for row_id, parent, _ in self.rows if parent == employee]

    def children(self, employee: str) -> list[str]:
        return self.reports_of(employee) if self.known(employee) else []

    # --- level 2
    def orphans(self) -> list[str]:
        return [row_id for row_id, _, _ in self.rows if self.is_orphan(row_id)]

    def cycle_from(self, employee: str) -> list[str] | None:
        """The cycle that starts at this row, following the parent links, or None."""
        members = [employee]
        current = self.parent[employee]
        while current != employee:
            if not self.known(current) or current in members:
                return None
            members.append(current)
            current = self.parent[current]
        return members

    def cycle_start(self, members: Sequence[str]) -> str:
        positions = {row_id: index for index, (row_id, _, _) in enumerate(self.rows)}
        return min(members, key=lambda member: positions[member])

    def cycles(self) -> list[list[str]]:
        found = []
        for row_id, _, _ in self.rows:
            members = self.cycle_from(row_id)
            if members is not None and self.cycle_start(members) == row_id:
                found.append(members)
        return found

    # --- level 3
    def chain(self, employee: str) -> list[str]:
        if not self.attached(employee):
            return []
        path = [employee]
        while self.known(self.parent[path[-1]]):
            path.append(self.parent[path[-1]])
        return path

    def lowest_common_manager(self, first: str, second: str) -> str:
        above_second = self.chain(second)
        for manager in self.chain(first):
            if manager in above_second:
                return manager
        return ""

    # --- level 4
    def subtree_size(self, employee: str) -> int:
        if not self.attached(employee):
            return 0
        return sum(1 for row_id in self.attached_ids() if employee in self.chain(row_id))

    def sibling_key(self, order: str, row_id: str) -> Any:
        if order == "name":
            return (self.name[row_id], row_id)
        if order == "size":
            return (-self.subtree_size(row_id), self.name[row_id], row_id)
        return 0

    def sort_siblings(self, siblings: list[str], order: str) -> list[str]:
        return sorted(siblings, key=lambda row_id: self.sibling_key(order, row_id))

    def tops(self, order: str) -> list[str]:
        tops = [r for r, _, _ in self.rows if self.is_root(r) or self.is_orphan(r)]
        return self.sort_siblings(tops, order)

    def indent(self, depth: int) -> str:
        return INDENT * depth

    def line(self, depth: int, row_id: str) -> str:
        return f"{self.indent(depth)}{self.name[row_id]} ({row_id})"

    def walk(self, row_id: str, depth: int, order: str) -> list[str]:
        lines = [self.line(depth, row_id)]
        for kid in self.sort_siblings(self.reports_of(row_id), order):
            lines.extend(self.walk(kid, depth + 1, order))
        return lines

    def outline(self, order: str) -> list[str]:
        lines: list[str] = []
        for top in self.tops(order):
            lines.extend(self.walk(top, 0, order))
        return lines


# ------------------------------------------------------------------ level 1 mistakes
class ChildrenSortedById(Model):
    """Sorts the reports by id instead of keeping the order of the rows."""

    def children(self, employee: str) -> list[str]:
        return sorted(super().children(employee))


class ChildrenSortedByName(Model):
    """Sorts the reports by name instead of keeping the order of the rows."""

    def children(self, employee: str) -> list[str]:
        return sorted(super().children(employee), key=lambda row_id: self.name[row_id])


class ChildrenOfTheEmptyIdAreTheRoots(Model):
    """Reads the empty string as an id, so that its 'reports' are the roots."""

    def children(self, employee: str) -> list[str]:
        return self.reports_of(employee) if employee == "" or self.known(employee) else []


class ChildrenOfAnUnknownManagerAreItsReports(Model):
    """Answers for a manager that has no row, as long as some row names it."""

    def children(self, employee: str) -> list[str]:
        return self.reports_of(employee) if employee != "" or self.known(employee) else []


class ChildrenOrderedByTheirOwnPosition(Model):
    """Lists the reports in reverse order of the rows."""

    def children(self, employee: str) -> list[str]:
        return list(reversed(super().children(employee)))


class NameOfUnknownIsTheId(Model):
    """Gives the id back when there is no row."""

    def name_of(self, employee: str) -> str:
        return self.name.get(employee, employee)


class LoadKeepsTheOldRows(Model):
    """Adds the new rows to the old ones instead of replacing them."""

    def load(self, rows: list[list[str]]) -> None:
        old = [list(row) for row in self.rows]
        super().load(old + rows)


class RootsSorted(Model):
    """Sorts the roots by id."""

    def roots(self) -> list[str]:
        return sorted(super().roots())


class FirstRootOnly(Model):
    """Keeps one root, as if a chart could have only one."""

    def roots(self) -> list[str]:
        return super().roots()[:1]


# ------------------------------------------------------------------ level 2 mistakes
class ParentsMustComeFirst(Model):
    """Attaches a row only to a parent whose row came earlier, the way a single pass would."""

    def reports_of(self, employee: str) -> list[str]:
        later = [
            r for r in super().reports_of(employee) if self.position(r) > self.position(employee)
        ]
        return later if self.known(employee) else super().reports_of(employee)

    def position(self, employee: str) -> int:
        return next(i for i, (row_id, _, _) in enumerate(self.rows) if row_id == employee)


class OrphansAreRoots(Model):
    """Lists the orphans among the roots."""

    def roots(self) -> list[str]:
        return [r for r, _, _ in self.rows if self.is_root(r) or self.is_orphan(r)]


class OrphansDropped(Model):
    """Reports no orphan."""

    def orphans(self) -> list[str]:
        return []


class OrphansWithTheirReports(Model):
    """Reports the whole subtree of an orphan, not just the row whose manager is missing."""

    def orphans(self) -> list[str]:
        return [
            r for r, _, _ in self.rows if self.attached(r) and self.top_of(r) in super().orphans()
        ]


class OrphansSorted(Model):
    """Sorts the orphans by id."""

    def orphans(self) -> list[str]:
        return sorted(super().orphans())


class RowsBelowACycleAreOrphans(Model):
    """Counts a row as an orphan when its manager is not attached."""

    def orphans(self) -> list[str]:
        return super().orphans() + [
            r for r, p, _ in self.rows if self.known(p) and not self.attached(p) and p != r
        ]


class CyclesNotReported(Model):
    """Reports no cycle."""

    def cycles(self) -> list[list[str]]:
        return []


class SelfLoopsOnly(Model):
    """Finds only the rows that report to themselves."""

    def cycles(self) -> list[list[str]]:
        return [[r] for r, p, _ in self.rows if r == p]


class SelfLoopsMissed(Model):
    """Finds every cycle except a row that reports to itself."""

    def cycles(self) -> list[list[str]]:
        return [cycle for cycle in super().cycles() if len(cycle) > 1]


class CycleStartsAtTheSmallestId(Model):
    """Starts each cycle at its smallest id instead of its first row."""

    def cycle_start(self, members: Sequence[str]) -> str:
        return min(members)


class CycleReadFromTheStartOnly(Model):
    """Lists the members in the order of their rows instead of the order of the links."""

    def cycles(self) -> list[list[str]]:
        positions = {r: i for i, (r, _, _) in enumerate(self.rows)}
        return [sorted(cycle, key=lambda member: positions[member]) for cycle in super().cycles()]


class CycleFollowsTheReportsNotTheManagers(Model):
    """Lists a cycle in the other direction: first member, then the person who reports to it."""

    def cycles(self) -> list[list[str]]:
        return [[cycle[0], *reversed(cycle[1:])] for cycle in super().cycles()]


class CyclesSortedByTheirSmallestId(Model):
    """Orders the cycles by id instead of by the position of their first member."""

    def cycles(self) -> list[list[str]]:
        return sorted(super().cycles(), key=lambda cycle: cycle[0])


class CycleCarriesItsTail(Model):
    """Adds the rows below a cycle to the cycle."""

    def cycles(self) -> list[list[str]]:
        found = []
        for cycle in super().cycles():
            tail = [
                r
                for r, _, _ in self.rows
                if r not in cycle and not self.attached(r) and self.leads_into(r, cycle)
            ]
            found.append(cycle + tail)
        return found

    def leads_into(self, employee: str, cycle: Sequence[str]) -> bool:
        current = employee
        for _ in range(len(self.rows)):
            current = self.parent[current]
            if current in cycle:
                return True
        return False


class CyclesIncludeEveryUnattachedRow(Model):
    """Reports each row that is not attached as a cycle of its own."""

    def cycles(self) -> list[list[str]]:
        return [[r] for r, _, _ in self.rows if not self.attached(r)]


# ------------------------------------------------------------------ level 3 mistakes
class ChainWithoutThePerson(Model):
    """Starts the chain at the manager."""

    def chain(self, employee: str) -> list[str]:
        return super().chain(employee)[1:]


class ChainOfARowOnACycleStopsAtTheRepeat(Model):
    """Climbs from a row on a cycle until a row repeats instead of answering with nothing."""

    def chain(self, employee: str) -> list[str]:
        if not self.known(employee):
            return []
        path = [employee]
        while self.known(self.parent[path[-1]]) and self.parent[path[-1]] not in path:
            path.append(self.parent[path[-1]])
        return path


class ChainEndsBelowTheTop(Model):
    """Leaves the top of the tree off the chain."""

    def chain(self, employee: str) -> list[str]:
        path = super().chain(employee)
        return path[:-1] if len(path) > 1 else path


class ChainOfAnUnknownIdIsTheId(Model):
    """Answers with the id itself when there is no row."""

    def chain(self, employee: str) -> list[str]:
        return super().chain(employee) or [employee]


class ManagerOfAManagerIsAboveThem(Model):
    """Answers with the manager of the common person when one person manages the other."""

    def lowest_common_manager(self, first: str, second: str) -> str:
        found = super().lowest_common_manager(first, second)
        return (
            self.parent[found]
            if found in (first, second) and self.known(self.parent[found])
            else found
        )


class SamePersonTwiceIsTheirManager(Model):
    """Looks only at the managers of the two people, never at the people themselves."""

    def lowest_common_manager(self, first: str, second: str) -> str:
        above_second = self.chain(second)[1:]
        for manager in self.chain(first)[1:]:
            if manager in above_second:
                return manager
        return ""


class HighestCommonManagerInstead(Model):
    """Returns the top of the shared part of the chains, not the lowest."""

    def lowest_common_manager(self, first: str, second: str) -> str:
        above_second = self.chain(second)
        shared = [m for m in self.chain(first) if m in above_second]
        return shared[-1] if shared else ""


class DifferentTreesShareTheFirstRoot(Model):
    """Answers with the top of the first person's tree when the two trees differ."""

    def lowest_common_manager(self, first: str, second: str) -> str:
        found = super().lowest_common_manager(first, second)
        return found or (self.chain(first) or [""])[-1]


class UnknownIdIsIgnored(Model):
    """Answers with the other person when one id has no row."""

    def lowest_common_manager(self, first: str, second: str) -> str:
        if not self.known(second):
            return first if self.attached(first) else ""
        if not self.known(first):
            return second if self.attached(second) else ""
        return super().lowest_common_manager(first, second)


# ------------------------------------------------------------------ level 4 mistakes
class IndentOfFourSpaces(Model):
    """Indents four spaces for each level."""

    def indent(self, depth: int) -> str:
        return "    " * depth


class IndentOfOneSpace(Model):
    """Indents one space for each level."""

    def indent(self, depth: int) -> str:
        return " " * depth


class IdBeforeTheName(Model):
    """Writes the id first and the name in brackets."""

    def line(self, depth: int, row_id: str) -> str:
        return f"{self.indent(depth)}{row_id} ({self.name[row_id]})"


class NoIdOnTheLine(Model):
    """Writes the name only."""

    def line(self, depth: int, row_id: str) -> str:
        return f"{self.indent(depth)}{self.name[row_id]}"


class NamesSortedWithoutCase(Model):
    """Compares names without their case."""

    def sibling_key(self, order: str, row_id: str) -> Any:
        if order == "name":
            return (self.name[row_id].lower(), row_id)
        if order == "size":
            return (-self.subtree_size(row_id), self.name[row_id].lower(), row_id)
        return 0


class NamesSortedByIdOnly(Model):
    """Sorts by id and ignores the name."""

    def sibling_key(self, order: str, row_id: str) -> Any:
        if order == "name":
            return row_id
        return super().sibling_key(order, row_id)


class EqualNamesKeepTheirInputOrder(Model):
    """Breaks a tie on the name by the order of the rows, not by the id."""

    def sibling_key(self, order: str, row_id: str) -> Any:
        if order == "name":
            return self.name[row_id]
        if order == "size":
            return (-self.subtree_size(row_id), self.name[row_id])
        return 0


class IdsInNaturalOrder(Model):
    """Orders ids with digits as numbers, so that 'k2' comes before 'k10'."""

    def sibling_key(self, order: str, row_id: str) -> Any:
        natural = [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", row_id)]
        if order == "name":
            return (self.name[row_id], natural_key(natural))
        if order == "size":
            return (-self.subtree_size(row_id), self.name[row_id], natural_key(natural))
        return 0


def natural_key(parts: list[Any]) -> list[tuple[int, Any]]:
    return [(0, part) if isinstance(part, int) else (1, part) for part in parts]


class SmallerSubtreeFirst(Model):
    """Puts the smaller subtree first."""

    def sibling_key(self, order: str, row_id: str) -> Any:
        if order == "size":
            return (self.subtree_size(row_id), self.name[row_id], row_id)
        return super().sibling_key(order, row_id)


class SizeTieBrokenByIdOnly(Model):
    """Breaks a tie on the size by the id, skipping the name."""

    def sibling_key(self, order: str, row_id: str) -> Any:
        if order == "size":
            return (-self.subtree_size(row_id), row_id)
        return super().sibling_key(order, row_id)


class TopsKeepTheirInputOrder(Model):
    """Sorts the reports of each person but leaves the tops in the order of the rows."""

    def tops(self, order: str) -> list[str]:
        return super().tops("input")


class OrphansListedAfterTheRoots(Model):
    """Puts the roots first and the orphans after them, whatever the order of the rows."""

    def tops(self, order: str) -> list[str]:
        roots = self.sort_siblings(self.roots(), order)
        return roots + self.sort_siblings(self.orphans(), order)


class OutlineLeavesOutOrphans(Model):
    """Draws only the trees whose top is a root."""

    def tops(self, order: str) -> list[str]:
        return self.sort_siblings(self.roots(), order)


class OutlineByLevels(Model):
    """Lists a level at a time, instead of finishing a person's subtree first."""

    def outline(self, order: str) -> list[str]:
        lines: list[str] = []
        level = [(top, 0) for top in self.tops(order)]
        while level:
            lines.extend(self.line(depth, row_id) for row_id, depth in level)
            level = [
                (kid, depth + 1)
                for row_id, depth in level
                for kid in self.sort_siblings(self.reports_of(row_id), order)
            ]
        return lines


class OutlineDrawsRowsThatAreNotAttached(Model):
    """Adds the rows on or below a cycle after the trees, at depth 0."""

    def outline(self, order: str) -> list[str]:
        lines = super().outline(order)
        lines.extend(self.line(0, r) for r, _, _ in self.rows if not self.attached(r))
        return lines


class SubtreeSizeWithoutThePerson(Model):
    """Counts only the people below."""

    def subtree_size(self, employee: str) -> int:
        return max(super().subtree_size(employee) - 1, 0)


class SubtreeSizeOfARowOnACycle(Model):
    """Counts the people below a row even when it is not attached."""

    def subtree_size(self, employee: str) -> int:
        if not self.known(employee):
            return 0
        count, queue, seen = 0, [employee], set()
        while queue:
            current = queue.pop()
            if current in seen:
                continue
            seen.add(current)
            count += 1
            queue.extend(self.reports_of(current))
        return count


class SubtreeSizeOnlyDirectReports(Model):
    """Counts the person and the direct reports, not the people further down."""

    def subtree_size(self, employee: str) -> int:
        if not self.attached(employee):
            return 0
        return 1 + len(self.reports_of(employee))


class SubtreeSizeByRecursion(Model):
    """Computes the size by calling itself once per level, so that a long chain overflows."""

    def subtree_size(self, employee: str) -> int:
        if not self.attached(employee):
            return 0
        return self.count_below(employee)

    def count_below(self, employee: str) -> int:
        return 1 + sum(self.count_below(kid) for kid in self.reports_of(employee))


class ChainByRecursion(Model):
    """Builds the chain by calling itself once per level."""

    def chain(self, employee: str) -> list[str]:
        if not self.attached(employee):
            return []
        return self.climb(employee)

    def climb(self, employee: str) -> list[str]:
        parent = self.parent[employee]
        return [employee] + (self.climb(parent) if self.known(parent) else [])


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
    except (IndexError, KeyError, ValueError, TypeError, RecursionError):
        return False


@pytest.mark.parametrize("case", SCRIPTED_CASES, ids=[case["id"] for case in SCRIPTED_CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert outputs(Model, case) == case["expected"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_a_hidden_case_holds_a_chain_deeper_than_the_default_recursion_limit():
    deepest = max(
        len(arguments[0])
        for case in HIDDEN_CASES
        for op, arguments in zip(case["ops"], case["args"], strict=True)
        if op == "load"
    )
    assert deepest > 1000


def test_the_generated_case_loads_a_chart_of_the_largest_size():
    generated = [case for case in CASES if "generate" in case]
    assert [case["generate"]["n"] for case in generated] == [100000]


def test_every_level_has_visible_and_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in SCRIPTED_CASES if case["level"] == level]
        assert any(case.get("visible") for case in at_level)
        assert sum(not case.get("visible") for case in at_level) >= 2
