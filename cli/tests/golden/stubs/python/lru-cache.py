"""LRU Cache.

Build a key-value cache with a fixed number of slots that discards
the entry unused for the longest time when it is full.

Statement: .statements/lru-cache.md
Run: cstudy test lru-cache
"""


class LRUCache:
    def __init__(self, capacity: int) -> None:
        pass

    def get(self, key: int) -> int:
        raise NotImplementedError

    def put(self, key: int, value: int) -> None:
        raise NotImplementedError
