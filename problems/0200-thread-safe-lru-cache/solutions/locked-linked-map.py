import threading
from collections import OrderedDict


class LRUCache:
    def __init__(self, capacity: int) -> None:
        self._capacity = capacity
        self._entries: OrderedDict[int, int] = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key: int) -> int:
        with self._lock:
            if key not in self._entries:
                return -1
            self._entries.move_to_end(key)
            return self._entries[key]

    def put(self, key: int, value: int) -> None:
        with self._lock:
            self._entries[key] = value
            self._entries.move_to_end(key)
            if len(self._entries) > self._capacity:
                self._entries.popitem(last=False)

    def size(self) -> int:
        with self._lock:
            return len(self._entries)
