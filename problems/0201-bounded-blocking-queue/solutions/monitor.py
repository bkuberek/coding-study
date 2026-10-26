import threading
from collections import deque


class BoundedBlockingQueue:
    def __init__(self, capacity: int) -> None:
        self._capacity = capacity
        self._items: deque[int] = deque()
        lock = threading.Lock()
        self._lock = lock
        self._not_full = threading.Condition(lock)
        self._not_empty = threading.Condition(lock)

    def put(self, value: int) -> None:
        with self._lock:
            while len(self._items) >= self._capacity:
                self._not_full.wait()
            self._items.append(value)
            self._not_empty.notify()

    def take(self) -> int:
        with self._lock:
            while not self._items:
                self._not_empty.wait()
            value = self._items.popleft()
            self._not_full.notify()
            return value

    def size(self) -> int:
        with self._lock:
            return len(self._items)
