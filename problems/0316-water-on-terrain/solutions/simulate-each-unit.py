STAY = -1
SPILL = -2


class Terrain:
    """Water is kept as a depth per column, and a column's level is its height plus its water.

    One unit of water is one walk: try to the left, then to the right, one column at a time and
    never uphill, and note where the final flat stretch of the walk begins. The walk either
    reaches an edge (the unit falls off), ends lower than it began (the unit settles at the start
    of the final flat stretch) or ends where it began (this direction does nothing).
    """

    def __init__(self, heights: list[int]) -> None:
        self._heights = list(heights)
        self._water = [0] * len(heights)
        self._spilled = 0

    # Level 1
    def render(self) -> list[str]:
        return self._picture(0, len(self._heights) - 1)

    def tallest(self) -> int:
        return max(self._heights, default=0)

    # Level 2
    def pour(self, column: int) -> list[int]:
        self._drop(column)
        return list(self._water)

    def water(self) -> list[int]:
        return list(self._water)

    def spilled(self) -> int:
        return self._spilled

    # Level 3
    def pour_many(self, column: int, units: int) -> list[int]:
        for _ in range(units):
            self._drop(column)
        return list(self._water)

    # Level 4
    def render_window(self, first: int, last: int) -> list[str]:
        return self._picture(first, last)

    def _level(self, column: int) -> int:
        return self._heights[column] + self._water[column]

    def _drop(self, column: int) -> None:
        for step in (-1, 1):
            landing = self._walk(column, step)
            if landing == SPILL:
                self._spilled += 1
                return
            if landing != STAY:
                self._water[landing] += 1
                return
        self._water[column] += 1

    def _walk(self, column: int, step: int) -> int:
        at = column
        flat_start = column
        while True:
            ahead = at + step
            if ahead < 0 or ahead >= len(self._heights):
                return SPILL
            if self._level(ahead) > self._level(at):
                break
            if self._level(ahead) < self._level(at):
                flat_start = ahead
            at = ahead
        return flat_start if self._level(flat_start) < self._level(column) else STAY

    def _picture(self, first: int, last: int) -> list[str]:
        top = max((h + w for h, w in zip(self._heights, self._water, strict=True)), default=0)
        rows = []
        for row in range(top, 0, -1):
            cells = []
            for column in range(first, last + 1):
                if self._heights[column] >= row:
                    cells.append("#")
                elif self._level(column) >= row:
                    cells.append("~")
                else:
                    cells.append(".")
            rows.append("".join(cells))
        return rows
