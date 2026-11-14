from bisect import bisect_right
from operator import itemgetter


class SnapshotArray:
    def __init__(self, length: int) -> None:
        # history[i] holds (snap id, value) pairs with strictly increasing snap ids.
        self.history: list[list[tuple[int, int]]] = [[] for _ in range(length)]
        self.snaps = 0

    def set(self, index: int, value: int) -> None:
        entries = self.history[index]
        if entries and entries[-1][0] == self.snaps:
            entries[-1] = (self.snaps, value)
        else:
            entries.append((self.snaps, value))

    def snap(self) -> int:
        self.snaps += 1
        return self.snaps - 1

    def get(self, index: int, snap_id: int) -> int:
        entries = self.history[index]
        position = bisect_right(entries, snap_id, key=itemgetter(0))
        return entries[position - 1][1] if position else 0
