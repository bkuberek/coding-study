"""water-on-terrain promises that its hidden cases catch the classic mistakes of a water
simulation: rows drawn from the bottom, a flat stretch taken for a wall, water that slides one
step instead of to the bottom of a slope, the wrong column of a flat bottom, edges that are walls
instead of cliffs, the right tried before the left, the water of earlier units ignored, units
poured all at once, and windows that lose a column or the height of the picture. These tests
replay every case against a model of the terrain written from the statement, which must give every
expected output, and against that model with one mistake planted at a time, which some hidden case
must fail. A mistake that crashes fails its case, as a thrown exception does in the grader."""

import json
import random
import re
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from tests.helpers import CATALOG_PROBLEMS

PROBLEM = CATALOG_PROBLEMS / "0316-water-on-terrain"
CASES: Sequence[Mapping[str, Any]] = json.loads(
    (PROBLEM / "tests.json").read_text(encoding="utf-8")
)["cases"]
HIDDEN_CASES = [case for case in CASES if not case.get("visible", False)]
EARTH, WATER, AIR = "#", "~", "."


class Model:
    """The terrain as the statement words it, one rule per method, so that each mistake below
    overrides a single method. A unit's walk is listed column by column, and the column it settles
    on is read from that list."""

    def __init__(self, heights: list[int]) -> None:
        self.heights = list(heights)
        self.depths = [0] * len(heights)
        self.off = 0

    def level(self, column: int) -> int:
        return self.heights[column] + self.depths[column]

    def walk_level(self, column: int) -> int:
        return self.level(column)

    # --- level 1
    def top_row(self) -> int:
        return max((self.level(column) for column in range(len(self.heights))), default=0)

    def cell(self, column: int, row: int) -> str:
        if self.heights[column] >= row:
            return EARTH
        return WATER if self.level(column) >= row else AIR

    def row_numbers(self) -> list[int]:
        return list(range(self.top_row(), 0, -1))

    def picture(self, first: int, last: int) -> list[str]:
        return [
            "".join(self.cell(column, row) for column in range(first, last + 1))
            for row in self.row_numbers()
        ]

    def render(self) -> list[str]:
        return self.picture(0, len(self.heights) - 1)

    def tallest(self) -> int:
        return max(self.heights, default=0)

    # --- level 2
    def directions(self) -> tuple[int, int]:
        return (-1, 1)

    def may_step(self, here: int, there: int) -> bool:
        return self.walk_level(there) <= self.walk_level(here)

    def outside(self, column: int) -> bool:
        return not 0 <= column < len(self.heights)

    def walk(self, start: int, step: int) -> tuple[list[int], bool]:
        """The columns a unit visits from `start`, and whether it reaches an edge."""
        visited = [start]
        while True:
            ahead = visited[-1] + step
            if self.outside(ahead):
                return visited, self.edge_is_a_cliff()
            if not self.may_step(visited[-1], ahead):
                return visited, False
            visited.append(ahead)

    def edge_is_a_cliff(self) -> bool:
        return True

    def falls_off(self, start: int, visited: list[int]) -> bool:
        return True

    def settling_column(self, start: int, visited: list[int]) -> int | None:
        lowest = min(self.walk_level(column) for column in visited)
        if lowest >= self.walk_level(start):
            return None
        return next(column for column in visited if self.walk_level(column) == lowest)

    def drop(self, column: int) -> None:
        for step in self.directions():
            visited, at_edge = self.walk(column, step)
            if at_edge and self.falls_off(column, visited):
                self.lose(column, visited)
                return
            target = self.settling_column(column, visited)
            if target is not None:
                self.depths[target] += 1
                return
        self.depths[column] += 1

    def lose(self, column: int, visited: list[int]) -> None:
        self.off += 1

    def pour(self, column: int) -> list[int]:
        self.drop(column)
        return self.water()

    def water(self) -> list[int]:
        return list(self.depths)

    def spilled(self) -> int:
        return self.off

    # --- level 3
    def pour_many(self, column: int, units: int) -> list[int]:
        for _ in range(units):
            self.drop(column)
        return self.water()

    # --- level 4
    def render_window(self, first: int, last: int) -> list[str]:
        return self.picture(first, last)


# ------------------------------------------------------------------ level 1 mistakes
class RowsFromTheBottom(Model):
    """Lists the rows from row 1 up."""

    def row_numbers(self) -> list[int]:
        return list(reversed(super().row_numbers()))


class GroundRowAdded(Model):
    """Adds a row of ground under the picture."""

    def picture(self, first: int, last: int) -> list[str]:
        return [*super().picture(first, last), EARTH * (last - first + 1)]


class ColumnNeedsToBeTallerThanTheRow(Model):
    """Fills a cell only when the column is taller than the row, not as tall."""

    def cell(self, column: int, row: int) -> str:
        if self.heights[column] > row:
            return EARTH
        return WATER if self.level(column) > row else AIR


class FlatProfileDrawsOneRow(Model):
    """Draws a row of dots for a profile of zeros."""

    def row_numbers(self) -> list[int]:
        return super().row_numbers() or [1]


class TallestIsTheWidth(Model):
    """Reports the number of columns."""

    def tallest(self) -> int:
        return len(self.heights)


class TallestIsTheLastColumn(Model):
    """Reports the height of the last column."""

    def tallest(self) -> int:
        return self.heights[-1]


# ------------------------------------------------------------------ level 2 mistakes
class RightFirst(Model):
    """Tries the right before the left."""

    def directions(self) -> tuple[int, int]:
        return (1, -1)


class FlatStretchIsAWall(Model):
    """Stops at a column of the same level."""

    def may_step(self, here: int, there: int) -> bool:
        return self.walk_level(there) < self.walk_level(here)


class SmallStepsUpAreAllowed(Model):
    """Climbs onto a column that is one level higher."""

    def may_step(self, here: int, there: int) -> bool:
        return self.walk_level(there) <= self.walk_level(here) + 1


class SettlesOnTheFirstLowerColumn(Model):
    """Stops sliding at the first column that is lower, not at the bottom of the run."""

    def settling_column(self, start: int, visited: list[int]) -> int | None:
        return next((c for c in visited if self.walk_level(c) < self.walk_level(start)), None)


class SettlesOnTheFarEndOfTheFlatBottom(Model):
    """Takes the farthest column of the lowest level, not the nearest."""

    def settling_column(self, start: int, visited: list[int]) -> int | None:
        lowest = min(self.walk_level(column) for column in visited)
        if lowest >= self.walk_level(start):
            return None
        return [column for column in visited if self.walk_level(column) == lowest][-1]


class SettlesOnTheLastColumnVisited(Model):
    """Settles on the last column the walk reached, whatever its level."""

    def settling_column(self, start: int, visited: list[int]) -> int | None:
        last = visited[-1]
        return last if self.walk_level(last) < self.walk_level(start) else None


class EdgesAreWalls(Model):
    """Treats the end of the landscape as a high wall."""

    def edge_is_a_cliff(self) -> bool:
        return False


class FlatRunToAnEdgeStays(Model):
    """Lets a unit fall off an edge only if the run is lower than where it started."""

    def falls_off(self, start: int, visited: list[int]) -> bool:
        return self.walk_level(visited[-1]) < self.walk_level(start)


class SpilledUnitStillLandsOnTheLastColumn(Model):
    """Counts a unit that fell off and also adds it to the last column of its walk."""

    def lose(self, column: int, visited: list[int]) -> None:
        super().lose(column, visited)
        self.depths[visited[-1]] += 1


class WaterOfEarlierUnitsIsIgnored(Model):
    """Walks on the heights of the terrain alone."""

    def walk_level(self, column: int) -> int:
        return self.heights[column]


class PourReturnsTheLevels(Model):
    """Returns height plus water instead of the water."""

    def pour(self, column: int) -> list[int]:
        self.drop(column)
        return [self.level(c) for c in range(len(self.heights))]


class SpilledCountIsNeverReported(Model):
    """Reports no spilled unit."""

    def spilled(self) -> int:
        return 0


class UnitStaysEvenWhenOnlyTheLeftFails(Model):
    """Gives up after the left and settles where it landed, never trying the right."""

    def directions(self) -> tuple[int, int]:
        return (-1, -1)


# ------------------------------------------------------------------ level 3 mistakes
class PourManyAllAtOnce(Model):
    """Decides every unit on the levels of the start and adds them up afterwards."""

    def pour_many(self, column: int, units: int) -> list[int]:
        before, off_before = list(self.depths), self.off
        landings = []
        for _ in range(units):
            self.depths, self.off = list(before), off_before
            self.drop(column)
            landings.append([now - then for now, then in zip(self.depths, before, strict=True)])
        self.depths = before
        for landing in landings:
            self.depths = [total + part for total, part in zip(self.depths, landing, strict=True)]
        self.off = off_before + sum(1 for landing in landings if not any(landing))
        return self.water()


class PourManyOneUnitShort(Model):
    """Pours one unit fewer than asked."""

    def pour_many(self, column: int, units: int) -> list[int]:
        return super().pour_many(column, max(units - 1, 0))


class PourManyStopsAtTheFirstSpill(Model):
    """Stops pouring when a unit falls off an edge."""

    def pour_many(self, column: int, units: int) -> list[int]:
        for _ in range(units):
            before = self.off
            self.drop(column)
            if self.off > before:
                break
        return self.water()


class PourManyDoesNotCountSpilledUnits(Model):
    """Counts the units that spill in a single pour, but not those of pourMany."""

    def pour_many(self, column: int, units: int) -> list[int]:
        before = self.off
        result = super().pour_many(column, units)
        self.off = before
        return result


# ------------------------------------------------------------------ level 4 mistakes
class WaterDrawnAsEarth(Model):
    """Draws water with the mark of the terrain."""

    def cell(self, column: int, row: int) -> str:
        return EARTH if self.level(column) >= row else AIR


class WindowWithoutItsLastColumn(Model):
    """Leaves the last column of a window out."""

    def render_window(self, first: int, last: int) -> list[str]:
        return self.picture(first, last - 1)


class WindowWithoutItsFirstColumn(Model):
    """Leaves the first column of a window out."""

    def render_window(self, first: int, last: int) -> list[str]:
        return self.picture(first + 1, last)


class WindowRowsFromTheWindow(Model):
    """Gives a window the number of rows of its own highest column."""

    def render_window(self, first: int, last: int) -> list[str]:
        top = max(self.level(column) for column in range(first, last + 1))
        return [
            "".join(self.cell(column, row) for column in range(first, last + 1))
            for row in range(top, 0, -1)
        ]


class WaterOnlyShownAboveTheTallestRow(Model):
    """Draws water only where the terrain of the whole picture is not as tall."""

    def cell(self, column: int, row: int) -> str:
        if self.heights[column] >= row:
            return EARTH
        return WATER if self.level(column) >= row and row > 1 else AIR


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
    except (IndexError, KeyError, ValueError, TypeError, StopIteration, RecursionError):
        return False


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_the_model_of_the_statement_gives_every_expected_output(case):
    assert outputs(Model, case) == case["expected"]


@pytest.mark.parametrize("mistake", MISTAKES, ids=[mistake.__name__ for mistake in MISTAKES])
def test_a_hidden_case_catches_each_classic_mistake(mistake):
    assert not all(passes(mistake, case) for case in HIDDEN_CASES), mistake.__doc__


def test_water_never_rises_above_the_tallest_column_and_every_unit_is_accounted_for():
    rng = random.Random(316)
    for _ in range(300):
        heights = [rng.randint(0, 8) for _ in range(rng.randint(1, 12))]
        terrain = Model(heights)
        units = rng.randint(0, 60)
        for _ in range(units):
            terrain.pour(rng.randrange(len(heights)))
        assert max(terrain.level(c) for c in range(len(heights))) <= max(heights)
        assert sum(terrain.water()) + terrain.spilled() == units


def test_every_level_has_visible_and_hidden_cases():
    for level in (1, 2, 3, 4):
        at_level = [case for case in CASES if case["level"] == level]
        assert any(case.get("visible") for case in at_level)
        assert sum(not case.get("visible") for case in at_level) >= 2
