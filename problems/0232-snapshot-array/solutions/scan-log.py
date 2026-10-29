class SnapshotArray:
    def __init__(self, length: int) -> None:
        self.log: list[tuple[int, int, int]] = []  # (index, value, snap id current at the write)
        self.snaps = 0

    def set(self, index: int, value: int) -> None:
        self.log.append((index, value, self.snaps))

    def snap(self) -> int:
        self.snaps += 1
        return self.snaps - 1

    def get(self, index: int, snap_id: int) -> int:
        # The newest write to index that happened before snapshot snap_id was taken.
        for written, value, current in reversed(self.log):
            if written == index and current <= snap_id:
                return value
        return 0
