class RangeModule:
    def __init__(self) -> None:
        # Disjoint, non-touching half-open intervals (start, end), sorted by start.
        self.intervals: list[tuple[int, int]] = []

    def add_range(self, left: int, right: int) -> None:
        merged: list[tuple[int, int]] = []
        placed = False
        for start, end in self.intervals:
            if end < left:
                merged.append((start, end))
            elif right < start:
                if not placed:
                    merged.append((left, right))
                    placed = True
                merged.append((start, end))
            else:
                # Overlapping or touching: absorb it into the new interval.
                left, right = min(left, start), max(right, end)
        if not placed:
            merged.append((left, right))
        self.intervals = merged

    def query_range(self, left: int, right: int) -> bool:
        # Stored intervals never touch, so a covered range lies inside a single one.
        return any(start <= left and right <= end for start, end in self.intervals)

    def remove_range(self, left: int, right: int) -> None:
        kept: list[tuple[int, int]] = []
        for start, end in self.intervals:
            if end <= left or right <= start:
                kept.append((start, end))
                continue
            if start < left:
                kept.append((start, left))
            if right < end:
                kept.append((right, end))
        self.intervals = kept
