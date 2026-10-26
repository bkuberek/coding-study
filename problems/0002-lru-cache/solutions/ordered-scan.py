class LRUCache:
    def __init__(self, capacity: int) -> None:
        self.capacity = capacity
        # Parallel lists ordered from least to most recently used.
        self.keys: list[int] = []
        self.values: list[int] = []

    def get(self, key: int) -> int:
        index = self._index_of(key)
        if index < 0:
            return -1
        value = self._remove(index)
        self._append(key, value)
        return value

    def put(self, key: int, value: int) -> None:
        index = self._index_of(key)
        if index >= 0:
            self._remove(index)
        elif len(self.keys) == self.capacity:
            self._remove(0)
        self._append(key, value)

    def _index_of(self, key: int) -> int:
        try:
            return self.keys.index(key)
        except ValueError:
            return -1

    def _remove(self, index: int) -> int:
        del self.keys[index]
        return self.values.pop(index)

    def _append(self, key: int, value: int) -> None:
        self.keys.append(key)
        self.values.append(value)
