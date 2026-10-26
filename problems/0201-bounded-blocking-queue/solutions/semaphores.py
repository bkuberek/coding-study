import threading
from collections import deque


class BoundedBlockingQueue:
    def __init__(self, capacity: int) -> None:
        self._items: deque[int] = deque()
        self._mutex = threading.Lock()
        self._free_slots = threading.Semaphore(capacity)
        self._stored = threading.Semaphore(0)

    def put(self, value: int) -> None:
        self._free_slots.acquire()
        with self._mutex:
            self._items.append(value)
        self._stored.release()

    def take(self) -> int:
        self._stored.acquire()
        with self._mutex:
            value = self._items.popleft()
        self._free_slots.release()
        return value

    def size(self) -> int:
        with self._mutex:
            return len(self._items)
