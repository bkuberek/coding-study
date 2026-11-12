"""consistent-hash-ring promises that its hidden cases catch the classic mistakes of a hash ring:
a hash over characters instead of UTF-8 bytes or read as a signed number, an exclusive boundary,
a ring that does not wrap, equal positions ordered by arrival, modulo placement over the sorted
nodes, virtual node labels named the other way round, arcs that forget the wrap, a report that
is cleared, unsorted or written by a question, replicas sorted or stopped at a repeat, and a
capacity computed in floating point or per point. These tests replay every case against a model
written from the statement (linear scans over the points and exact fractions), which must give
every expected output, and against that model with one mistake planted at a time, which some
hidden case must fail. A mistake that crashes, as a capacity too small to place every key does,
fails its case, as a thrown exception or a hang does in the grader. The statement's FNV-1a test
values are checked against the reference ones."""

import json
import math
import re
from collections.abc import Mapping, Sequence
from fractions import Fraction
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0370-consistent-hash-ring"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]
RING = 2**32
# FNV-1a 32-bit test values from the FNV reference (draft-eastlake-fnv, section 8.3).
FNV_REFERENCE = {"": 0x811C9DC5, "a": 0xE40C292C, "foobar": 0xBF9CF968}

Point = tuple[int, str, str]


def snake_case(op: str) -> str:
    return re.sub(r"(?<=[a-z])(?=[A-Z])", "_", op).lower()


class Model:
    """Points as a plain list in insertion order; every question scans it."""

    def __init__(self) -> None:
        self.points: list[Point] = []
        self.joined: list[str] = []
        self.sizes: dict[str, int] = {}
        self.tracked: list[str] = []
        self.report: list[list[str]] = []

    # --- hashing and labels
    def data(self, text: str) -> bytes:
        return text.encode("utf-8")

    def position_of(self, text: str) -> int:
        value = 2166136261
        for byte in self.data(text):
            value = ((value ^ byte) * 16777619) & 0xFFFFFFFF
        return value

    def label(self, node: str, index: int) -> str:
        return node if index == 0 else f"{index}#{node}"

    def ring_key(self, point: Point) -> tuple[int, str]:
        return (point[0], point[1])

    # --- ownership
    def owner_point(self, points: list[Point], position: int) -> Point | None:
        if not points:
            return None
        after = [p for p in points if self.at_or_after(p[0], position)]
        return min(after or points, key=self.ring_key)

    def at_or_after(self, point_position: int, position: int) -> bool:
        return point_position >= position

    def owner(self, points: list[Point], key: str) -> str:
        found = self.owner_point(points, self.position_of(key))
        return found[2] if found else ""

    def walk(self, key: str) -> list[Point]:
        """Every point once, clockwise from the key's owner point."""
        ordered = sorted(self.points, key=self.ring_key)
        first = self.owner_point(self.points, self.position_of(key))
        start = ordered.index(first) if first else 0
        return ordered[start:] + ordered[:start]

    # --- level 1
    def add_node(self, node: str) -> int:
        return self.position_of(node) if self.add_virtual_node(node, 1) else -1

    def remove_node(self, node: str) -> bool:
        if node not in self.sizes:
            return False
        before = self.owners()
        self.points = [p for p in self.points if p[2] != node]
        self.joined.remove(node)
        del self.sizes[node]
        self.make_report(before)
        return True

    def nodes(self) -> list[str]:
        return sorted(self.sizes)

    def node_for(self, key: str) -> str:
        return self.owner(self.points, key)

    def modulo_order(self, joined: list[str]) -> list[str]:
        return joined

    def modulo(self, joined: list[str], key: str) -> str:
        order = self.modulo_order(joined)
        return order[self.position_of(key) % len(order)] if order else ""

    def modulo_node_for(self, key: str) -> str:
        return self.modulo(self.joined, key)

    def count_moves(self, keys: list[str], node: str) -> list[int]:
        if node in self.sizes:
            return []
        grown = [*self.points, (self.position_of(node), node, node)]
        joined = [*self.joined, node]
        return [
            sum(self.owner(self.points, k) != self.owner(grown, k) for k in keys),
            sum(self.modulo(self.joined, k) != self.modulo(joined, k) for k in keys),
        ]

    # --- level 2
    def refuse_count(self, count: int) -> bool:
        return count < 1

    def add_virtual_node(self, node: str, count: int) -> bool:
        if node in self.sizes or self.refuse_count(count):
            return False
        before = self.owners()
        for index in range(max(count, 1)):
            label = self.label(node, index)
            self.points.append((self.position_of(label), label, node))
        self.joined.append(node)
        self.sizes[node] = max(count, 1)
        self.make_report(before)
        return True

    def positions(self, node: str) -> list[int]:
        if node not in self.sizes:
            return []
        return [self.position_of(self.label(node, i)) for i in range(self.sizes[node])]

    def predecessor(self, point: Point) -> tuple[Point, bool]:
        """The point before this one on the ring, and whether the step back crosses the top."""
        smaller = [p for p in self.points if self.ring_key(p) < self.ring_key(point)]
        if smaller:
            return max(smaller, key=self.ring_key), False
        return max(self.points, key=self.ring_key), True

    def arc(self, point: Point) -> int:
        previous, wraps = self.predecessor(point)
        return point[0] - previous[0] + (RING if wraps else 0)

    def arc_share(self) -> list[int]:
        return [sum(self.arc(p) for p in self.points if p[2] == node) for node in self.nodes()]

    def key_counts(self, keys: list[str]) -> list[int]:
        owners = [self.node_for(k) for k in keys]
        return [owners.count(node) for node in self.nodes()]

    # --- level 3
    def track_keys(self, keys: list[str]) -> int:
        self.tracked.extend(k for k in keys if k not in self.tracked)
        return len(self.tracked)

    def owners(self) -> dict[str, str]:
        return {k: self.node_for(k) for k in self.tracked}

    def sort_rows(self, rows: list[list[str]]) -> list[list[str]]:
        return sorted(rows)

    def make_report(self, before: dict[str, str]) -> None:
        after = self.owners()
        self.report = self.sort_rows(
            [[k, before[k], after[k]] for k in before if before[k] != after[k]]
        )

    def last_moves(self) -> list[list[str]]:
        return [list(row) for row in self.report]

    def owned_keys(self, node: str) -> list[str]:
        if node not in self.sizes:
            return []
        return sorted(k for k in self.tracked if self.node_for(k) == node)

    # --- level 4
    def replicas(self, key: str, count: int) -> list[str]:
        if count < 1 or not self.points:
            return []
        found: list[str] = []
        for _, _, node in self.walk(key):
            if len(found) < count and node not in found:
                found.append(node)
        return found

    def capacity(self, m: int, numerator: int, denominator: int) -> int:
        return math.ceil((1 + Fraction(numerator, denominator)) * m / len(self.sizes))

    def holder(self, point: Point) -> str:
        return point[2]

    def assign_bounded(self, keys: list[str], numerator: int, denominator: int) -> list[str]:
        if not self.points or not keys:
            return []
        limit = self.capacity(len(keys), numerator, denominator)
        load: dict[str, int] = {}
        placed = []
        for key in self.order_keys(keys):
            room = [p for p in self.walk(key) if load.get(self.holder(p), 0) < limit]
            if not room:
                raise ValueError("no node has room")
            load[self.holder(room[0])] = load.get(self.holder(room[0]), 0) + 1
            placed.append((key, room[0][2]))
        return [node for _, node in self.restore(keys, placed)]

    def order_keys(self, keys: list[str]) -> list[str]:
        return keys

    def restore(self, keys: list[str], placed: list[tuple[str, str]]) -> list[tuple[str, str]]:
        return placed


# ------------------------------------------------------------------ level 1 mistakes
class HashesCodePoints(Model):
    """Feeds each character's code to the hash instead of its UTF-8 bytes."""

    def data(self, text: str) -> bytes:
        return bytes(ord(ch) % 256 for ch in text)


class SignedPositions(Model):
    """Reads the 32-bit hash as a signed integer."""

    def position_of(self, text: str) -> int:
        value = super().position_of(text)
        return value - RING if value >= 2**31 else value


class ExclusiveBoundary(Model):
    """Gives a key exactly at a point's position to the next point."""

    def at_or_after(self, point_position: int, position: int) -> bool:
        return point_position > position


class WrapsToTheLastPoint(Model):
    """Gives a key past the last point to the last point."""

    def owner_point(self, points: list[Point], position: int) -> Point | None:
        if not points:
            return None
        after = [p for p in points if p[0] >= position]
        return min(after, key=self.ring_key) if after else max(points, key=self.ring_key)


class EqualPositionsByArrival(Model):
    """Lets the point added first win a tie."""

    def ring_key(self, point: Point) -> tuple[int, str]:
        return (point[0], f"{self.points.index(point):06d}" if point in self.points else "")


class ModuloOverSortedNodes(Model):
    """Indexes the sorted node names instead of the join order."""

    def modulo_order(self, joined: list[str]) -> list[str]:
        return sorted(joined)


class CountMovesForAPresentNode(Model):
    """Counts moves for a node that is already on the ring."""

    def count_moves(self, keys: list[str], node: str) -> list[int]:
        if node in self.sizes:
            return [0, 0]
        return super().count_moves(keys, node)


class NoMovesOnAnEmptyRing(Model):
    """Says that nothing moves when the ring was empty."""

    def count_moves(self, keys: list[str], node: str) -> list[int]:
        if not self.points and node not in self.sizes:
            return [0, 0]
        return super().count_moves(keys, node)


# ------------------------------------------------------------------ level 2 mistakes
class NumberAfterTheName(Model):
    """Labels point i as node#i."""

    def label(self, node: str, index: int) -> str:
        return node if index == 0 else f"{node}#{index}"


class NumberedFromZero(Model):
    """Labels every point with its number, point 0 included."""

    def label(self, node: str, index: int) -> str:
        return f"{index}#{node}"


class PositionsSorted(Model):
    """Lists a node's positions sorted."""

    def positions(self, node: str) -> list[int]:
        return sorted(super().positions(node))


class CountBelowOneMeansOne(Model):
    """Accepts a count below 1 as one point."""

    def refuse_count(self, count: int) -> bool:
        return False


class ArcWithoutTheWrap(Model):
    """Forgets that the first point's arc crosses the top of the ring."""

    def arc(self, point: Point) -> int:
        previous, wraps = self.predecessor(point)
        return point[0] if wraps else point[0] - previous[0]


class TiedPointsShareTheArc(Model):
    """Measures each arc from the previous different position."""

    def predecessor(self, point: Point) -> tuple[Point, bool]:
        smaller = [p for p in self.points if p[0] < point[0]]
        if smaller:
            return max(smaller, key=self.ring_key), False
        return max(self.points, key=self.ring_key), True


class KeyCountsDistinctKeys(Model):
    """Counts each key once, however often it is listed."""

    def key_counts(self, keys: list[str]) -> list[int]:
        return super().key_counts(list(dict.fromkeys(keys)))


# ------------------------------------------------------------------ level 3 mistakes
class RowsSortedIgnoringCase(Model):
    """Sorts the report as if B were b."""

    def sort_rows(self, rows: list[list[str]]) -> list[list[str]]:
        return sorted(rows, key=lambda row: (row[0].lower(), row[0]))


class RefusedChangeClearsTheReport(Model):
    """Empties the report when a change is refused."""

    def add_virtual_node(self, node: str, count: int) -> bool:
        done = super().add_virtual_node(node, count)
        if not done:
            self.report = []
        return done

    def remove_node(self, node: str) -> bool:
        done = super().remove_node(node)
        if not done:
            self.report = []
        return done


class NoRowsFromOrToAnEmptyRing(Model):
    """Leaves out keys that had no owner before or have none after."""

    def make_report(self, before: dict[str, str]) -> None:
        super().make_report(before)
        self.report = [row for row in self.report if row[1] and row[2]]


class CountMovesWritesTheReport(Model):
    """Lets the question countMoves replace the report."""

    def count_moves(self, keys: list[str], node: str) -> list[int]:
        answer = super().count_moves(keys, node)
        self.report = []
        return answer


class TrackedKeysCountedWithRepeats(Model):
    """Counts a key tracked twice twice."""

    def __init__(self) -> None:
        super().__init__()
        self.repeats = 0

    def track_keys(self, keys: list[str]) -> int:
        super().track_keys(keys)
        self.repeats += len(keys) - len(set(keys))
        return len(self.tracked) + self.repeats


# ------------------------------------------------------------------ level 4 mistakes
class ReplicasSorted(Model):
    """Lists the replicas by name."""

    def replicas(self, key: str, count: int) -> list[str]:
        return sorted(super().replicas(key, count))


class ReplicasStopAtARepeat(Model):
    """Stops the walk at the first point of a node already listed."""

    def replicas(self, key: str, count: int) -> list[str]:
        if count < 1 or not self.points:
            return []
        found: list[str] = []
        for _, _, node in self.walk(key):
            if node in found or len(found) == count:
                break
            found.append(node)
        return found


class ReplicasCountPoints(Model):
    """Takes the next count points, repeats and all."""

    def replicas(self, key: str, count: int) -> list[str]:
        if count < 1 or not self.points:
            return []
        return [node for _, _, node in self.walk(key)][:count]


class CapacityInFloatingPoint(Model):
    """Computes the capacity with floating point."""

    def capacity(self, m: int, numerator: int, denominator: int) -> int:
        return math.ceil((1 + numerator / denominator) * m / len(self.sizes))


class CapacityRoundedDown(Model):
    """Rounds the capacity down."""

    def capacity(self, m: int, numerator: int, denominator: int) -> int:
        return math.floor((1 + Fraction(numerator, denominator)) * m / len(self.sizes))


class CapacityPerPoint(Model):
    """Divides by the number of points instead of the number of nodes."""

    def capacity(self, m: int, numerator: int, denominator: int) -> int:
        return math.ceil((1 + Fraction(numerator, denominator)) * m / len(self.points))


class LoadCountedPerPoint(Model):
    """Fills each point up to the capacity instead of each node."""

    def holder(self, point: Point) -> str:
        return point[1]


class KeysPlacedSorted(Model):
    """Places the keys in sorted order rather than in the order given."""

    def order_keys(self, keys: list[str]) -> list[str]:
        return sorted(keys)

    def restore(self, keys: list[str], placed: list[tuple[str, str]]) -> list[tuple[str, str]]:
        by_key = dict(placed)
        return [(key, by_key[key]) for key in keys]


class ForwardToTheNextNodeByName(Model):
    """Sends a key from a full node to the next node by name, not the next point."""

    def assign_bounded(self, keys: list[str], numerator: int, denominator: int) -> list[str]:
        if not self.points or not keys:
            return []
        limit = self.capacity(len(keys), numerator, denominator)
        names = self.nodes()
        load = dict.fromkeys(names, 0)
        placed = []
        for key in keys:
            at = names.index(self.node_for(key))
            while load[names[at]] >= limit:
                at = (at + 1) % len(names)
            load[names[at]] += 1
            placed.append(names[at])
        return placed


MISTAKES: Sequence[type[Model]] = Model.__subclasses__()


def outputs(model_type: type[Model], case: Mapping[str, Any]) -> list[Any]:
    """The output of every op of the case, `None` for the constructor."""
    model = model_type()
    calls = zip(case["ops"][1:], case["args"][1:], strict=True)
    return [None, *(getattr(model, snake_case(op))(*arguments) for op, arguments in calls)]


def passes(model_type: type[Model], case: Mapping[str, Any]) -> bool:
    try:
        return outputs(model_type, case) == case["expected"]
    except (IndexError, KeyError, ValueError, TypeError, ZeroDivisionError):
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


def test_the_hash_gives_the_fnv_reference_values_quoted_in_the_statement():
    statement = (PROBLEM / "problem.md").read_text(encoding="utf-8")
    for text, value in FNV_REFERENCE.items():
        assert Model().position_of(text) == value
        assert f"`{value}`" in statement


def test_the_first_example_checks_the_hash_against_the_reference():
    example = next(case for case in CASES if case["id"] == "ex1")
    hashed = {
        args[0]: got
        for op, args, got in zip(example["ops"], example["args"], example["expected"], strict=True)
        if op == "positionOf"
    }
    assert hashed == FNV_REFERENCE
