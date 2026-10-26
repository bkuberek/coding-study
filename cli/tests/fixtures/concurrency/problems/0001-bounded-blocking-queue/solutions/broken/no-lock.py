import time
from collections import deque


class BoundedBlockingQueue:
    def __init__(self, capacity: int) -> None:
        self._capacity = capacity
        self._items: deque[int] = deque()

    def put(self, value: int) -> None:
        while len(self._items) >= self._capacity:
            time.sleep(0)
        self._items.append(value)

    def take(self) -> int:
        while not self._items:
            time.sleep(0)
        return self._items.popleft()

    def size(self) -> int:
        return len(self._items)
