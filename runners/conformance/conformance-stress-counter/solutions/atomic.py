import threading


class StressCounter:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._count = 0

    def increment(self) -> int:
        with self._lock:
            count = self._count
            self._count = count + 1
            return count + 1
