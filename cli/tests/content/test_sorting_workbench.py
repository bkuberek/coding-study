"""sorting-workbench promises that its hidden cases catch the classic mistakes of four sorts that
report their own work: a move counted for the key's placement, a comparison missed or invented at
the end of an insertion, equal values shifted, a merge that is not stable or splits the other way,
a tail counted as comparisons, a quicksort pivot taken from the wrong place or a partition that
does not group the equal values, a select that sorts everything or keeps partitioning the block of
equal values, a count of runs that drops the last short run, and merge passes counted per group,
per run, or with the fan-in ignored. These tests replay every case against a model of the
workbench written from the statement, which must give every expected output, and against that
model with one mistake planted at a time, which some hidden case must fail. A mistake that crashes
fails its case, as a thrown exception does in the grader."""

import heapq
import json
import re
from bisect import bisect_left, bisect_right, insort
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0361-sorting-workbench"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]
LEVELS = (1, 2, 3, 4)


class Model:
    """The workbench as the statement words it, one rule per method, so that each mistake below
    overrides a single method. The counts of insertion sort are worked out on a sorted prefix with
    binary searches, not by replaying the shifts, so that the model is not the reference again."""

    def __init__(self) -> None:
        self.meter: list[int] = []

    # --- level 1: insertion sort
    def shifts(self, prefix: list[int], value: int) -> int:
        """How many values of the sorted prefix the key passes: those strictly greater."""
        return len(prefix) - bisect_right(prefix, value)

    def stops_on_a_comparison(self, prefix: list[int], value: int) -> bool:
        """Whether the key stops against a value that is not greater, not at the left end."""
        return bisect_right(prefix, value) > 0

    def placements(self, count: int) -> int:
        return 0

    def insertion_sort(self, values: list[int]) -> list[int]:
        prefix: list[int] = []
        comparisons = moves = 0
        for value in values:
            if prefix:
                passed = self.shifts(prefix, value)
                comparisons += passed + (1 if self.stops_on_a_comparison(prefix, value) else 0)
                moves += passed
            insort(prefix, value)
        self.meter = [comparisons, moves + self.placements(len(values))]
        return prefix

    def report(self) -> list[int]:
        return list(self.meter)

    # --- level 2: merge sort by a column
    def left_size(self, size: int) -> int:
        return size // 2

    def takes_left(self, left: int, right: int) -> bool:
        return left <= right

    def counts_the_tail(self) -> bool:
        return False

    def column(self, key: int) -> int:
        return key

    def merge_sort_by(self, rows: list[list[int]], key: int) -> list[list[int]]:
        self.meter = [0]
        column = self.column(key)

        def sort(part: list[list[int]]) -> list[list[int]]:
            if len(part) < 2:
                return part
            cut = self.left_size(len(part))
            left, right = sort(part[:cut]), sort(part[cut:])
            merged: list[list[int]] = []
            while left and right:
                self.meter[0] += 1
                merged.append(
                    (left if self.takes_left(left[0][column], right[0][column]) else right).pop(0)
                )
            for rest in (left, right):
                if self.counts_the_tail():
                    self.meter[0] += len(rest)
                merged.extend(rest)
            return merged

        return sort([list(row) for row in rows])

    # --- level 3: quicksort and quickselect
    def pivot_position(self, low: int, high: int) -> int:
        return low + (high - low) // 2

    def smallest_range(self) -> int:
        """The shortest range that is partitioned."""
        return 2

    def group_equals(self) -> bool:
        return True

    def partition(self, items: list[int], low: int, high: int) -> tuple[int, int]:
        """Returns where the block of values equal to the pivot starts and ends."""
        position = self.pivot_position(low, high)
        pivot = items[position]
        if not self.group_equals():
            return self.two_way_partition(items, low, high, position)
        below, scan, above = low, low, high
        while scan <= above:
            if items[scan] < pivot:
                items[below], items[scan] = items[scan], items[below]
                below += 1
                scan += 1
            elif items[scan] > pivot:
                items[scan], items[above] = items[above], items[scan]
                above -= 1
            else:
                scan += 1
        return below, above

    @staticmethod
    def two_way_partition(items: list[int], low: int, high: int, position: int) -> tuple[int, int]:
        """The pivot goes to the end, smaller values to the front, and the pivot to its place."""
        pivot = items[position]
        items[position], items[high] = items[high], items[position]
        store = low
        for scan in range(low, high):
            if items[scan] < pivot:
                items[store], items[scan] = items[scan], items[store]
                store += 1
        items[store], items[high] = items[high], items[store]
        return store, store

    def work_of(self, low: int, high: int) -> int:
        return high - low + 1

    def quick_sort(self, values: list[int]) -> list[int]:
        items = list(values)
        calls = steps = 0
        pending = [(0, len(items) - 1)]
        while pending:
            low, high = pending.pop()
            if high - low + 1 < self.smallest_range():
                continue
            below, above = self.partition(items, low, high)
            calls += 1
            steps += self.work_of(low, high)
            pending += [(low, below - 1), (above + 1, high)]
        self.meter = [calls, steps]
        return items

    def select_ranges(
        self, below: int, above: int, target: int, low: int, high: int
    ) -> tuple[int, int] | None:
        """The range to keep partitioning, or None when the answer is known."""
        if target < below:
            return low, below - 1
        if target > above:
            return above + 1, high
        return None

    def rank(self, k: int) -> int:
        return k - 1

    def quick_select(self, values: list[int], k: int) -> int:
        items = list(values)
        target = self.rank(k)
        calls = steps = 0
        low, high = 0, len(items) - 1
        while high - low + 1 >= self.smallest_range():
            below, above = self.partition(items, low, high)
            calls += 1
            steps += self.work_of(low, high)
            narrower = self.select_ranges(below, above, target, low, high)
            if narrower is None:
                break
            low, high = narrower
        self.meter = [calls, steps]
        return items[target]

    # --- level 4: external merge sort
    def runs_of(self, values: list[int], memory: int) -> list[list[int]]:
        return [sorted(values[start : start + memory]) for start in range(0, len(values), memory)]

    def fan_in(self, ways: int) -> int:
        return ways

    def passes_needed(self, runs: int, ways: int) -> int:
        passes = 0
        while runs > 1:
            runs = -(-runs // self.fan_in(ways))
            passes += 1
        return passes

    def external_sort(self, values: list[int], memory: int, ways: int) -> list[int]:
        runs = self.runs_of(values, memory)
        self.meter = [len(runs), self.passes_needed(len(runs), ways)]
        return list(heapq.merge(*runs))


# --- the mistakes, one rule each
class KeyPlacementCountsAsAMove(Model):
    """Counts the write of the key after its shifts as one more move per value."""

    def placements(self, count: int) -> int:
        return max(count - 1, 0)


class ShiftsEqualValues(Model):
    """Passes values that are equal to the key, as `>=` would."""

    def shifts(self, prefix: list[int], value: int) -> int:
        return len(prefix) - bisect_left(prefix, value)

    def stops_on_a_comparison(self, prefix: list[int], value: int) -> bool:
        return bisect_left(prefix, value) > 0


class NoComparisonAtTheEnd(Model):
    """Counts only the comparisons that lead to a move, missing the one that stops the key."""

    def stops_on_a_comparison(self, prefix: list[int], value: int) -> bool:
        return False


class ComparisonAtTheLeftEnd(Model):
    """Counts a comparison against nothing when the key reaches the front."""

    def stops_on_a_comparison(self, prefix: list[int], value: int) -> bool:
        return True


class MeterAccumulates(Model):
    """Adds the work of an insertion sort to the meter instead of replacing it."""

    def insertion_sort(self, values: list[int]) -> list[int]:
        before = list(self.meter)
        result = super().insertion_sort(values)
        if len(before) == len(self.meter):
            self.meter = [old + new for old, new in zip(before, self.meter, strict=True)]
        return result


class MergeIsNotStable(Model):
    """Takes the right run on a tie."""

    def takes_left(self, left: int, right: int) -> bool:
        return left < right


class MergeSplitsUpperHalf(Model):
    """Gives the left run the larger half of an odd number of rows."""

    def left_size(self, size: int) -> int:
        return (size + 1) // 2


class MergeCountsTheTail(Model):
    """Counts the rows copied after one run is empty as comparisons."""

    def counts_the_tail(self) -> bool:
        return True


class MergeSortsByTheFirstColumn(Model):
    """Ignores the key column."""

    def column(self, key: int) -> int:
        return 0


class PivotIsTheFirstValue(Model):
    """Takes the first value of the range as the pivot."""

    def pivot_position(self, low: int, high: int) -> int:
        return low


class PivotIsTheLastValue(Model):
    """Takes the last value of the range as the pivot."""

    def pivot_position(self, low: int, high: int) -> int:
        return high


class PivotIsTheUpperMiddle(Model):
    """Takes the upper middle of an even range."""

    def pivot_position(self, low: int, high: int) -> int:
        return (low + high + 1) // 2


class PartitionsAShortRangeOfOne(Model):
    """Also partitions ranges of one value."""

    def smallest_range(self) -> int:
        return 1


class EqualsAreNotGrouped(Model):
    """Splits into smaller and not smaller, so equal values are partitioned again and again."""

    def group_equals(self) -> bool:
        return False


class StepsCountOnlyThePivotComparisons(Model):
    """Counts the values compared with the pivot, which leaves the pivot's own slot out."""

    def work_of(self, low: int, high: int) -> int:
        return high - low


class SelectKeepsPartitioningTheEqualBlock(Model):
    """Narrows to the equal block instead of stopping when the answer is in it."""

    def select_ranges(
        self, below: int, above: int, target: int, low: int, high: int
    ) -> tuple[int, int] | None:
        if target < below:
            return low, below - 1
        if target > above:
            return above + 1, high
        if (below, above) == (low, high):
            return None
        return below, above


class SelectPartitionsBothSides(Model):
    """Behaves like a quicksort and then reads the answer."""

    def quick_select(self, values: list[int], k: int) -> int:
        return self.quick_sort(values)[k - 1]


class SelectRankIsZeroBased(Model):
    """Reads `k` as a position from 0."""

    def rank(self, k: int) -> int:
        return k


class RunsFromTheMemoryDivision(Model):
    """Counts the runs as n // memory, dropping the last short one."""

    def external_sort(self, values: list[int], memory: int, ways: int) -> list[int]:
        result = super().external_sort(values, memory, ways)
        runs = max(len(values) // memory, 1 if values else 0)
        self.meter = [runs, self.passes_needed(runs, ways)]
        return result


class MergesEveryRunAtOnce(Model):
    """Ignores the fan-in: one pass merges all the runs."""

    def passes_needed(self, runs: int, ways: int) -> int:
        return 1 if runs > 1 else 0


class CountsEveryGroupAsAPass(Model):
    """Counts the merges inside a pass, not the passes."""

    def passes_needed(self, runs: int, ways: int) -> int:
        merges = 0
        while runs > 1:
            groups = -(-runs // ways)
            merges += groups
            runs = groups
        return merges


class CountsTheRunsAsAPass(Model):
    """Counts the pass that forms the runs."""

    def passes_needed(self, runs: int, ways: int) -> int:
        return super().passes_needed(runs, ways) + (1 if runs else 0)


class OneRunStillMerges(Model):
    """Counts a pass of a single run with itself."""

    def passes_needed(self, runs: int, ways: int) -> int:
        return max(super().passes_needed(runs, ways), 1 if runs else 0)


class FanInIsOneLess(Model):
    """Merges `ways - 1` runs at a time."""

    def fan_in(self, ways: int) -> int:
        return max(ways - 1, 2)


class SelectLeavesTheMeterAlone(Model):
    """Does not touch the meter in a select."""

    def quick_select(self, values: list[int], k: int) -> int:
        saved = list(self.meter)
        answer = super().quick_select(values, k)
        self.meter = saved
        return answer


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


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert outputs(Model, case) == case["expected"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_every_level_has_visible_and_hidden_cases():
    for level in LEVELS:
        at_level = [case for case in CASES if case["level"] == level]
        assert any(case.get("visible") for case in at_level)
        assert sum(not case.get("visible") for case in at_level) >= 2


def test_a_case_of_each_level_uses_only_the_methods_of_that_level_and_below():
    methods = {
        "insertionSort": 1,
        "report": 1,
        "mergeSortBy": 2,
        "quickSort": 3,
        "quickSelect": 3,
        "externalSort": 4,
    }
    for case in CASES:
        assert all(methods[op] <= case["level"] for op in case["ops"][1:]), case["id"]


def test_insertion_sort_moves_are_the_inversions_of_the_input():
    for case in CASES:
        if case["level"] != 1:
            continue
        latest: list[int] | None = None
        for index, op in enumerate(case["ops"]):
            if op == "insertionSort":
                latest = case["args"][index][0]
            elif op == "report" and latest is not None:
                inversions = sum(
                    1
                    for later in range(len(latest))
                    for earlier in range(later)
                    if latest[earlier] > latest[later]
                )
                assert case["expected"][index][1] == inversions, case["id"]


def test_stable_passes_from_the_last_column_to_the_first_give_the_lexicographic_order():
    case = next(case for case in CASES if case["id"] == "h24")
    rows = case["args"][1][0]
    assert case["expected"][3] == sorted(rows)


def test_the_two_passes_of_the_first_example_group_the_teams_in_order_of_minutes():
    case = next(case for case in CASES if case["id"] == "ex3")
    assert case["expected"][2] == sorted(case["args"][1][0])
