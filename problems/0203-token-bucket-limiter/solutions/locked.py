import threading


class TokenBucket:
    def __init__(self, capacity: int, refill_per_second: int) -> None:
        self._capacity = capacity
        self._refill_per_second = refill_per_second
        self._lock = threading.Lock()
        self._stored = capacity
        self._last_refill = 0

    def try_acquire(self, timestamp: int, tokens: int) -> bool:
        with self._lock:
            self._refill(timestamp)
            if self._stored < tokens:
                return False
            self._stored -= tokens
            return True

    def available(self, timestamp: int) -> int:
        with self._lock:
            self._refill(timestamp)
            return self._stored

    def _refill(self, timestamp: int) -> None:
        if timestamp <= self._last_refill:
            return
        elapsed = timestamp - self._last_refill
        self._stored = min(self._capacity, self._stored + elapsed * self._refill_per_second)
        self._last_refill = timestamp
