import threading


class Counts:
    """Counts per key; every change happens under one lock."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counts: dict[str, int] = {}

    def add(self, key: str, amount: int) -> int:
        with self._lock:
            count = self._counts.get(key, 0) + amount
            self._counts[key] = count
            return count

    def get(self, key: str) -> int:
        with self._lock:
            return self._counts.get(key, 0)

    def take(self, key: str, amount: int) -> bool:
        with self._lock:
            count = self._counts.get(key, 0)
            if count < amount:
                return False
            self._counts[key] = count - amount
            return True
