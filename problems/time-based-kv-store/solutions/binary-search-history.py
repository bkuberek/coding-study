from bisect import bisect_right


class TimeMap:
    def __init__(self) -> None:
        # Per key, parallel lists sorted by timestamp (writes arrive in time order).
        self.timestamps: dict[str, list[int]] = {}
        self.values: dict[str, list[str]] = {}

    def set(self, key: str, value: str, timestamp: int) -> None:
        self.timestamps.setdefault(key, []).append(timestamp)
        self.values.setdefault(key, []).append(value)

    def get(self, key: str, timestamp: int) -> str:
        times = self.timestamps.get(key)
        if times is None:
            return ""
        # Number of writes at or before timestamp; the last of them is the answer.
        count = bisect_right(times, timestamp)
        return self.values[key][count - 1] if count > 0 else ""
