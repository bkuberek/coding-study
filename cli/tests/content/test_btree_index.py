"""btree-index promises that its hidden cases catch the classic mistakes of a B+ tree: a key equal
to a separator sent left, a split that keeps the middle key on the wrong side or copies it out of
an inner node, a scan that does not count the leaf it peeks into, a delete that repairs in the
wrong order or forgets the separator, an inner borrow without the rotation, and a bulk load that
rounds, groups or orders wrongly. These tests replay every case against a model of the index
written from the statement, recursive where the reference keeps a path, which must give every
expected output, and against that model with one mistake planted at a time, which some hidden
case must fail. A mistake that crashes fails its case, as a thrown exception does in the grader."""

import json
import re
from collections.abc import Mapping, Sequence
from itertools import pairwise
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0367-btree-index"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]
MAX_ROW_ID = 10**9
"""The constraints say `0 <= rowId <= 10^9`, which also keeps a row id apart from the `-1` that
`search` answers for a missing key."""

Key = tuple[int, ...]


class Node:
    def __init__(self, leaf: bool, keys: list[Key], payload: list[Any]) -> None:
        self.leaf = leaf
        self.keys = keys
        self.rows: list[int] = payload if leaf else []
        self.children: list[Node] = [] if leaf else payload
        self.next: Node | None = None


class Model:
    """The index as the statement words it, one rule per method. Each mistake below overrides one
    rule."""

    REPAIRS = ("borrow_left", "borrow_right", "merge_left", "merge_right")

    def __init__(self, min_keys: int) -> None:
        self.d = min_keys
        self.root = Node(True, [], [])

    # --- keys
    def cmp(self, first: Key, second: Key) -> int:
        return (first > second) - (first < second)

    def show(self, key: Key) -> str:
        return ",".join(map(str, key))

    def child_index(self, node: Node, key: Key) -> int:
        return sum(1 for separator in node.keys if self.cmp(separator, key) <= 0)

    def first_at_least(self, node: Node, key: Key) -> int:
        return next((i for i, k in enumerate(node.keys) if self.cmp(k, key) >= 0), len(node.keys))

    def leaf_for(self, key: Key) -> tuple[Node, int]:
        node, depth = self.root, 1
        while not node.leaf:
            node, depth = node.children[self.child_index(node, key)], depth + 1
        return node, depth

    # --- level 1
    def search(self, key: list[int]) -> int:
        leaf, _ = self.leaf_for(tuple(key))
        at = self.first_at_least(leaf, tuple(key))
        if at < len(leaf.keys) and self.cmp(leaf.keys[at], tuple(key)) == 0:
            return leaf.rows[at]
        return -1

    def insert(self, key: list[int], row_id: int) -> bool:
        target = tuple(key)
        if self.duplicate_in_leaf(target):
            return self.on_duplicate(target, row_id)
        grown = self.insert_below(self.root, target, row_id)
        if grown is not None:
            separator, right = grown
            self.root = Node(False, [separator], [self.root, right])
        return True

    def duplicate_in_leaf(self, key: Key) -> bool:
        leaf, _ = self.leaf_for(key)
        return any(self.cmp(k, key) == 0 for k in leaf.keys)

    def on_duplicate(self, key: Key, row_id: int) -> bool:
        return False

    def insert_below(self, node: Node, key: Key, row_id: int) -> tuple[Key, Node] | None:
        if node.leaf:
            at = self.first_at_least(node, key)
            node.keys.insert(at, key)
            node.rows.insert(at, row_id)
            return self.split_leaf(node) if self.too_full(node) else None
        index = self.child_index(node, key)
        grown = self.insert_below(node.children[index], key, row_id)
        if grown is None:
            return None
        separator, right = grown
        node.keys.insert(index, separator)
        node.children.insert(index + 1, right)
        return self.split_inner(node) if self.too_full(node) else None

    def too_full(self, node: Node) -> bool:
        return len(node.keys) > 2 * self.d

    def split_leaf(self, node: Node) -> tuple[Key, Node]:
        keep = self.d
        right = Node(True, node.keys[keep:], node.rows[keep:])
        del node.keys[keep:], node.rows[keep:]
        right.next, node.next = node.next, right
        return right.keys[0], right

    def split_inner(self, node: Node) -> tuple[Key, Node]:
        middle = node.keys[self.d]
        right = Node(False, node.keys[self.d + 1 :], node.children[self.d + 1 :])
        del node.keys[self.d :], node.children[self.d + 1 :]
        return middle, right

    def levels(self) -> list[str]:
        lines, depth = [], [self.root]
        while depth:
            lines.append(" ".join(self.show_node(node) for node in depth))
            depth = [child for node in depth for child in node.children]
        return lines

    def show_node(self, node: Node) -> str:
        return "[" + " ".join(self.show(key) for key in node.keys) + "]"

    # --- level 2
    def scan(self, low: Key, high: Key) -> tuple[list[int], int]:
        leaf, visits = self.scan_start(low)
        rows, at = [], self.first_at_least(leaf, low)
        while True:
            while at < len(leaf.keys):
                if self.past_high(leaf.keys[at], high):
                    return rows, visits
                rows.append(leaf.rows[at])
                at += 1
            if leaf.next is None:
                return rows, visits
            leaf, at = leaf.next, 0
            visits += self.step_cost(leaf, high)

    def scan_start(self, low: Key) -> tuple[Node, int]:
        return self.leaf_for(low)

    def past_high(self, key: Key, high: Key) -> bool:
        return self.cmp(key, high) > 0

    def step_cost(self, leaf: Node, high: Key) -> int:
        return 1

    def range_scan(self, low: list[int], high: list[int]) -> list[int]:
        return self.scan(tuple(low), tuple(high))[0]

    def scan_visits(self, low: list[int], high: list[int]) -> int:
        return self.scan(tuple(low), tuple(high))[1]

    def height(self) -> int:
        node, count = self.root, 1
        while not node.leaf:
            node, count = node.children[0], count + 1
        return count

    # --- level 3
    def remove(self, key: list[int]) -> bool:
        if not self.remove_below(self.root, tuple(key)):
            return False
        if not self.root.leaf and not self.root.keys:
            self.shrink_root()
        return True

    def shrink_root(self) -> None:
        self.root = self.root.children[0]

    def remove_below(self, node: Node, key: Key) -> bool:
        if node.leaf:
            at = self.first_at_least(node, key)
            if at == len(node.keys) or self.cmp(node.keys[at], key) != 0:
                return False
            del node.keys[at], node.rows[at]
            return True
        index = self.child_index(node, key)
        if not self.remove_below(node.children[index], key):
            return False
        self.after_child_lost_a_key(node, index)
        if self.too_empty(node.children[index]):
            self.repair(node, index)
        return True

    def after_child_lost_a_key(self, parent: Node, index: int) -> None:
        """Nothing: the separators stay."""

    def too_empty(self, node: Node) -> bool:
        return len(node.keys) < self.d

    def repair(self, parent: Node, index: int) -> None:
        node = parent.children[index]
        left = parent.children[index - 1] if index > 0 else None
        right = parent.children[index + 1] if index + 1 < len(parent.children) else None
        for step in self.REPAIRS:
            if step == "borrow_left" and left is not None and self.can_lend(left):
                return self.borrow_left(parent, index, node, left)
            if step == "borrow_right" and right is not None and self.can_lend(right):
                return self.borrow_right(parent, index, node, right)
            if step == "merge_left" and left is not None:
                return self.merge(parent, index - 1)
            if step == "merge_right" and right is not None:
                return self.merge(parent, index)
        raise AssertionError("no sibling")

    def can_lend(self, sibling: Node) -> bool:
        return len(sibling.keys) > self.d

    def borrow_left(self, parent: Node, index: int, node: Node, left: Node) -> None:
        if node.leaf:
            node.keys.insert(0, left.keys.pop())
            node.rows.insert(0, left.rows.pop())
            parent.keys[index - 1] = node.keys[0]
        else:
            node.keys.insert(0, parent.keys[index - 1])
            parent.keys[index - 1] = left.keys.pop()
            node.children.insert(0, left.children.pop())

    def borrow_right(self, parent: Node, index: int, node: Node, right: Node) -> None:
        if node.leaf:
            node.keys.append(right.keys.pop(0))
            node.rows.append(right.rows.pop(0))
            parent.keys[index] = right.keys[0]
        else:
            node.keys.append(parent.keys[index])
            parent.keys[index] = right.keys.pop(0)
            node.children.append(right.children.pop(0))

    def merge(self, parent: Node, first: int) -> None:
        left, right = parent.children[first], parent.children[first + 1]
        separator = parent.keys.pop(first)
        parent.children.pop(first + 1)
        if left.leaf:
            left.keys += right.keys
            left.rows += right.rows
            left.next = right.next
        else:
            left.keys += [separator, *right.keys]
            left.children += right.children

    # --- level 4
    def bulk_load(self, keys: list[list[int]], row_ids: list[int], fill_percent: int) -> bool:
        if not self.may_bulk_load():
            return False
        entries = [tuple(key) for key in keys]
        if not self.increasing(entries):
            return False
        if not entries:
            return True
        per = self.per_node(fill_percent)
        level: list[Node] = []
        start = 0
        for size in self.group_sizes(len(entries), per, self.d, 2 * self.d):
            leaf = Node(True, entries[start : start + size], list(row_ids[start : start + size]))
            if level:
                level[-1].next = leaf
            level.append(leaf)
            start += size
        while len(level) > 1:
            parents, start = [], 0
            per_inner = self.children_per_node(per)
            for size in self.group_sizes(len(level), per_inner, self.d + 1, 2 * self.d + 1):
                children = level[start : start + size]
                parents.append(Node(False, [self.smallest(c) for c in children[1:]], children))
                start += size
            level = parents
        self.root = level[0]
        return True

    def may_bulk_load(self) -> bool:
        return self.root.leaf and not self.root.keys

    def increasing(self, entries: list[Key]) -> bool:
        return all(self.cmp(a, b) < 0 for a, b in pairwise(entries))

    def per_node(self, fill_percent: int) -> int:
        return 2 * self.d * fill_percent // 100

    def children_per_node(self, per: int) -> int:
        return per + 1

    def group_sizes(self, total: int, size: int, low: int, high: int) -> list[int]:
        groups = []
        while total > 0:
            groups.append(min(size, total))
            total -= groups[-1]
        if len(groups) > 1 and groups[-1] < low:
            pool = groups.pop() + groups.pop()
            groups += self.combine(pool, high)
        return groups

    def combine(self, pool: int, high: int) -> list[int]:
        return [pool] if pool <= high else [pool - pool // 2, pool // 2]

    def smallest(self, node: Node) -> Key:
        while not node.leaf:
            node = node.children[0]
        return node.keys[0]

    def prefix_scan(self, prefix: list[int]) -> list[int]:
        node, width, rows = self.root, len(prefix), []
        while not node.leaf:
            node = node.children[0]
        leaf: Node | None = node
        while leaf is not None:
            rows += [
                r for k, r in zip(leaf.keys, leaf.rows, strict=True) if list(k[:width]) == prefix
            ]
            leaf = leaf.next
        return rows


class EqualKeyGoesLeft(Model):
    """Sends a key equal to a separator to the left child."""

    def child_index(self, node: Node, key: Key) -> int:
        return sum(1 for separator in node.keys if self.cmp(separator, key) < 0)


class LeafSplitKeepsTheMiddle(Model):
    """Keeps the middle entry in the left leaf."""

    def split_leaf(self, node: Node) -> tuple[Key, Node]:
        right = Node(True, node.keys[self.d + 1 :], node.rows[self.d + 1 :])
        del node.keys[self.d + 1 :], node.rows[self.d + 1 :]
        right.next, node.next = node.next, right
        return right.keys[0], right


class SeparatorIsTheLastLeftKey(Model):
    """Copies the last key of the left leaf up instead of the first key of the right one."""

    def split_leaf(self, node: Node) -> tuple[Key, Node]:
        _, right = super().split_leaf(node)
        return node.keys[-1], right


class InnerSplitCopiesTheMiddle(Model):
    """Splits an inner node like a leaf: the middle key goes up and stays in the right node."""

    def split_inner(self, node: Node) -> tuple[Key, Node]:
        middle = node.keys[self.d]
        right = Node(False, node.keys[self.d :], node.children[self.d + 1 :])
        del node.keys[self.d :], node.children[self.d + 1 :]
        return middle, right


class SplitsAtTwiceMinKeys(Model):
    """Splits a node as soon as it holds 2 * minKeys keys."""

    def too_full(self, node: Node) -> bool:
        return len(node.keys) >= 2 * self.d


class DuplicateReplacesTheRowId(Model):
    """Refuses a duplicate but stores its row id."""

    def on_duplicate(self, key: Key, row_id: int) -> bool:
        leaf, _ = self.leaf_for(key)
        leaf.rows[self.first_at_least(leaf, key)] = row_id
        return False


class DuplicateSaysTrue(Model):
    """Answers true for a duplicate."""

    def on_duplicate(self, key: Key, row_id: int) -> bool:
        return True


class EmptyIndexPrintsNothing(Model):
    """Prints the empty index as an empty list."""

    def levels(self) -> list[str]:
        return [] if self.root.leaf and not self.root.keys else super().levels()


class ScanDoesNotCountThePeek(Model):
    """Counts a step to the next leaf only when that leaf yields an entry."""

    def step_cost(self, leaf: Node, high: Key) -> int:
        return int(bool(leaf.keys) and self.cmp(leaf.keys[0], high) <= 0)


class ScanStartsAtTheLeftmostLeaf(Model):
    """Walks the leaves from the first one instead of going down with the low bound."""

    def scan_start(self, low: Key) -> tuple[Node, int]:
        node, depth = self.root, 1
        while not node.leaf:
            node, depth = node.children[0], depth + 1
        return node, depth


class HeightCountsInnerNodesOnly(Model):
    """Counts the levels above the leaves only."""

    def height(self) -> int:
        return super().height() - 1

    def scan(self, low: Key, high: Key) -> tuple[list[int], int]:
        rows, visits = super().scan(low, high)
        return rows, visits - 1


class HighBoundExcluded(Model):
    """Stops a scan at a key equal to the high bound."""

    def past_high(self, key: Key, high: Key) -> bool:
        return self.cmp(key, high) >= 0


class RemoveRefreshesTheSeparator(Model):
    """Rewrites the separator before a leaf to its new first key after every remove."""

    def after_child_lost_a_key(self, parent: Node, index: int) -> None:
        child = parent.children[index]
        if child.leaf and index > 0 and child.keys:
            parent.keys[index - 1] = child.keys[0]


class BorrowsRightFirst(Model):
    """Tries the right sibling before the left one."""

    REPAIRS = ("borrow_right", "borrow_left", "merge_left", "merge_right")


class MergesRightFirst(Model):
    """Merges with the right sibling when there is one."""

    REPAIRS = ("borrow_left", "borrow_right", "merge_right", "merge_left")


class BorrowLeavesTheSeparator(Model):
    """Moves an entry between leaves without updating the separator."""

    def borrow_left(self, parent: Node, index: int, node: Node, left: Node) -> None:
        if node.leaf:
            node.keys.insert(0, left.keys.pop())
            node.rows.insert(0, left.rows.pop())
        else:
            super().borrow_left(parent, index, node, left)

    def borrow_right(self, parent: Node, index: int, node: Node, right: Node) -> None:
        if node.leaf:
            node.keys.append(right.keys.pop(0))
            node.rows.append(right.rows.pop(0))
        else:
            super().borrow_right(parent, index, node, right)


class BorrowFromRightUsesTheMovedKey(Model):
    """Sets the separator to the entry that moved left, not to the right sibling's new first key."""

    def borrow_right(self, parent: Node, index: int, node: Node, right: Node) -> None:
        super().borrow_right(parent, index, node, right)
        if node.leaf:
            parent.keys[index] = node.keys[-1]


class InnerBorrowWithoutRotation(Model):
    """Moves the sibling's key straight across instead of through the parent."""

    def borrow_left(self, parent: Node, index: int, node: Node, left: Node) -> None:
        if node.leaf:
            super().borrow_left(parent, index, node, left)
        else:
            node.keys.insert(0, left.keys.pop())
            node.children.insert(0, left.children.pop())

    def borrow_right(self, parent: Node, index: int, node: Node, right: Node) -> None:
        if node.leaf:
            super().borrow_right(parent, index, node, right)
        else:
            node.keys.append(right.keys.pop(0))
            node.children.append(right.children.pop(0))


class InnerMergeDropsTheSeparator(Model):
    """Joins two inner nodes without pulling the separator down."""

    def merge(self, parent: Node, first: int) -> None:
        left, right = parent.children[first], parent.children[first + 1]
        if left.leaf:
            super().merge(parent, first)
        else:
            parent.keys.pop(first)
            parent.children.pop(first + 1)
            left.keys += right.keys
            left.children += right.children


class RootNeverShrinks(Model):
    """Keeps an inner root with no keys."""

    def shrink_root(self) -> None:
        pass


class UnderflowAtMinKeys(Model):
    """Repairs a node that still holds minKeys keys."""

    def too_empty(self, node: Node) -> bool:
        return len(node.keys) <= self.d


class FillRoundsUp(Model):
    """Rounds the keys per node up."""

    def per_node(self, fill_percent: int) -> int:
        return -(-2 * self.d * fill_percent // 100)


class InnerNodesGetFillKeysAsChildren(Model):
    """Gives an inner node c children instead of c + 1."""

    def children_per_node(self, per: int) -> int:
        return max(per, 2)


class ShortLastGroupStays(Model):
    """Leaves a short last group as it is."""

    def group_sizes(self, total: int, size: int, low: int, high: int) -> list[int]:
        return [min(size, total - start) for start in range(0, total, size)]


class ShortLastGroupAlwaysJoins(Model):
    """Puts a short last group into the one before it, even when they do not fit in one node."""

    def combine(self, pool: int, high: int) -> list[int]:
        return [pool]


class ShortLastGroupSecondHalfLarger(Model):
    """Gives the extra entry of an odd split to the second half."""

    def combine(self, pool: int, high: int) -> list[int]:
        return [pool] if pool <= high else [pool // 2, pool - pool // 2]


class BulkLoadReplacesAnything(Model):
    """Loads over an index that already holds entries."""

    def may_bulk_load(self) -> bool:
        return True


class BulkLoadAcceptsRepeats(Model):
    """Accepts keys that repeat, as long as they never go down."""

    def increasing(self, entries: list[Key]) -> bool:
        return all(self.cmp(a, b) <= 0 for a, b in pairwise(entries))


class ComparesTheFirstFieldOnly(Model):
    """Compares composite keys by their first field."""

    def cmp(self, first: Key, second: Key) -> int:
        return (first[0] > second[0]) - (first[0] < second[0])


class ComparesTheSum(Model):
    """Compares composite keys by the sum of their fields."""

    def cmp(self, first: Key, second: Key) -> int:
        return (sum(first) > sum(second)) - (sum(first) < sum(second)) or super().cmp(first, second)


class KeyPrintsWithSpaces(Model):
    """Prints a composite key as `1, 9`."""

    def show(self, key: Key) -> str:
        return ", ".join(map(str, key))


class PrefixPaddedWithZeros(Model):
    """Scans a prefix as the range from the prefix padded with zeros."""

    def prefix_scan(self, prefix: list[int]) -> list[int]:
        if self.root.leaf and not self.root.keys:
            return []
        missing = len(self.smallest(self.root)) - len(prefix)
        low = (*prefix, *[0] * missing)
        high = (*prefix, *[10**7] * missing)
        return self.scan(low, high)[0]


MISTAKES: Sequence[type[Model]] = Model.__subclasses__()


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", op).lower()


def outputs(model_type: type[Model], case: Mapping[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor."""
    model = model_type(*case["args"][0])
    calls = zip(case["ops"][1:], case["args"][1:], strict=True)
    return [None, *(getattr(model, snake_case(op))(*arguments) for op, arguments in calls)]


def passes(model_type: type[Model], case: Mapping[str, Any]) -> bool:
    try:
        return outputs(model_type, case) == case["expected"]
    except (IndexError, KeyError, ValueError, TypeError, AttributeError, AssertionError):
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


def test_keys_have_one_field_until_level_four():
    for case in CASES:
        if case["level"] < 4:
            keys = [arg for args in case["args"][1:] for arg in args if isinstance(arg, list)]
            assert all(len(key) == 1 for key in keys), case["id"]


def row_ids(case: Mapping[str, Any]) -> list[int]:
    """Every row id the case passes to `insert` or `bulkLoad`."""
    found: list[int] = []
    for op, arguments in zip(case["ops"], case["args"], strict=True):
        if op == "insert":
            found.append(arguments[1])
        elif op == "bulkLoad":
            found += arguments[1]
    return found


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_every_row_id_is_within_the_stated_range(case):
    assert all(0 <= row_id <= MAX_ROW_ID for row_id in row_ids(case))
