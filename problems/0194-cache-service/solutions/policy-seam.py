import heapq
from collections import OrderedDict
from dataclasses import dataclass
from typing import Protocol


class EvictionPolicy(Protocol):
    """Tracks the live keys and names the one to evict when the cache is full."""

    def admit(self, key: str) -> None: ...

    def touch(self, key: str) -> None: ...

    def forget(self, key: str) -> None: ...

    def victim(self) -> str: ...


class LruPolicy:
    def __init__(self) -> None:
        self._order: OrderedDict[str, None] = OrderedDict()  # least recently used first

    def admit(self, key: str) -> None:
        self._order[key] = None

    def touch(self, key: str) -> None:
        self._order.move_to_end(key)

    def forget(self, key: str) -> None:
        del self._order[key]

    def victim(self) -> str:
        return next(iter(self._order))


class FifoPolicy(LruPolicy):
    def touch(self, key: str) -> None:
        """Using a key does not change its place: the oldest insertion goes first."""


class LfuPolicy:
    """Least frequently used first; among equal counts, least recently used first."""

    def __init__(self) -> None:
        self._counts: dict[str, int] = {}
        self._buckets: dict[int, OrderedDict[str, None]] = {}
        self._lowest = 1  # never above the lowest count in use

    def admit(self, key: str) -> None:
        self._place(key, 1)
        self._lowest = 1

    def touch(self, key: str) -> None:
        count = self._counts[key]
        self._unplace(key, count)
        self._place(key, count + 1)

    def forget(self, key: str) -> None:
        self._unplace(key, self._counts.pop(key))

    def victim(self) -> str:
        while not self._buckets.get(self._lowest):
            self._lowest += 1
        return next(iter(self._buckets[self._lowest]))

    def _place(self, key: str, count: int) -> None:
        self._counts[key] = count
        self._buckets.setdefault(count, OrderedDict())[key] = None

    def _unplace(self, key: str, count: int) -> None:
        del self._buckets[count][key]


POLICIES: dict[str, type[EvictionPolicy]] = {"LRU": LruPolicy, "LFU": LfuPolicy, "FIFO": FifoPolicy}


@dataclass(slots=True)
class _Entry:
    value: str
    expires_at: int | None

    def expired(self, now: int) -> bool:
        return self.expires_at is not None and now >= self.expires_at


class CacheService:
    def __init__(self, capacity: int, policy: str) -> None:
        self._capacity = capacity
        self._policy: EvictionPolicy = POLICIES[policy]()
        self._entries: dict[str, _Entry] = {}
        self._expiries: list[tuple[int, str]] = []  # min-heap; stale pairs are skipped
        self._hits = self._misses = self._evictions = self._expirations = 0

    def put(self, timestamp: int, key: str, value: str, ttl: int) -> None:
        expires_at = timestamp + ttl if ttl > 0 else None
        entry = self._live(timestamp, key)
        if entry is not None:
            entry.value, entry.expires_at = value, expires_at
            self._policy.touch(key)
        else:
            self._make_room(timestamp)
            self._entries[key] = _Entry(value, expires_at)
            self._policy.admit(key)
        if expires_at is not None:
            heapq.heappush(self._expiries, (expires_at, key))

    def get(self, timestamp: int, key: str) -> str:
        entry = self._live(timestamp, key)
        if entry is None:
            self._misses += 1
            return ""
        self._hits += 1
        self._policy.touch(key)
        return entry.value

    def remove(self, timestamp: int, key: str) -> bool:
        if self._live(timestamp, key) is None:
            return False
        self._drop(key)
        return True

    def size(self, timestamp: int) -> int:
        self._purge_expired(timestamp)
        return len(self._entries)

    def stats(self) -> list[int]:
        return [self._hits, self._misses, self._evictions, self._expirations]

    def _live(self, now: int, key: str) -> _Entry | None:
        entry = self._entries.get(key)
        if entry is not None and entry.expired(now):
            self._expire(key)
            return None
        return entry

    def _make_room(self, now: int) -> None:
        if len(self._entries) < self._capacity:
            return
        self._purge_expired(now)
        if len(self._entries) >= self._capacity:
            self._drop(self._policy.victim())
            self._evictions += 1

    def _purge_expired(self, now: int) -> None:
        while self._expiries and self._expiries[0][0] <= now:
            expires_at, key = heapq.heappop(self._expiries)
            entry = self._entries.get(key)
            if entry is not None and entry.expires_at == expires_at:
                self._expire(key)

    def _expire(self, key: str) -> None:
        self._drop(key)
        self._expirations += 1

    def _drop(self, key: str) -> None:
        del self._entries[key]
        self._policy.forget(key)
