class TimeMap:
    def __init__(self) -> None:
        self.history: dict[str, list[tuple[int, str]]] = {}

    def set(self, key: str, value: str, timestamp: int) -> None:
        self.history.setdefault(key, []).append((timestamp, value))

    def get(self, key: str, timestamp: int) -> str:
        for written_at, value in reversed(self.history.get(key, [])):
            if written_at <= timestamp:
                return value
        return ""
