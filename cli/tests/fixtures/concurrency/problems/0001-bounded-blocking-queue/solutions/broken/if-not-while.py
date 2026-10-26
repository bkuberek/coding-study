import threading
from collections import deque


class BoundedBlockingQueue:
    def __init__(self, capacity: int) -> None:
        self._capacity = capacity
        self._items: deque[int] = deque()
        self._changed = threading.Condition()

    def put(self, value: int) -> None:
        with self._changed:
            if len(self._items) >= self._capacity:
                self._changed.wait()
            self._items.append(value)
            self._changed.notify_all()

    def take(self) -> int:
        with self._changed:
            if not self._items:
                self._changed.wait()
            value = self._items.popleft()
            self._changed.notify_all()
            return value

    def size(self) -> int:
        with self._changed:
            return len(self._items)
