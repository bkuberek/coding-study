from collections import OrderedDict


class _Memory:
    """One memory: its texts so far (the last is current), its write time and its expiry."""

    __slots__ = ("expires_at", "versions", "words", "written_at")

    def __init__(self, text: str, written_at: int, expires_at: int | None) -> None:
        self.versions = [text]
        self.words = frozenset(text.split())
        self.written_at = written_at
        self.expires_at = expires_at

    def is_live_at(self, moment: int) -> bool:
        return self.expires_at is None or moment < self.expires_at

    def write(self, text: str, moment: int) -> None:
        self.versions.append(text)
        self.words = frozenset(text.split())
        self.written_at = moment


class MemoryStore:
    def __init__(self) -> None:
        # Each user's memories, least recently used first.
        self._users: dict[str, OrderedDict[str, _Memory]] = {}
        self._quotas: dict[str, int] = {}

    # Level 1
    def add(self, timestamp: int, user_id: str, memory_id: str, text: str) -> bool:
        return self._insert(timestamp, user_id, memory_id, _Memory(text, timestamp, None))

    def get(self, timestamp: int, user_id: str, memory_id: str) -> str:
        memory = self._use(timestamp, user_id, memory_id)
        return memory.versions[-1] if memory else ""

    def update(self, timestamp: int, user_id: str, memory_id: str, text: str) -> bool:
        memory = self._use(timestamp, user_id, memory_id)
        if memory is None:
            return False
        memory.write(text, timestamp)
        return True

    def remove(self, timestamp: int, user_id: str, memory_id: str) -> bool:
        if self._live(timestamp, user_id, memory_id) is None:
            return False
        del self._users[user_id][memory_id]
        return True

    # Level 2
    def search(self, timestamp: int, user_id: str, query: str, k: int) -> list[str]:
        terms = frozenset(query.split())
        ranked = []
        for memory_id, memory in self._users.get(user_id, {}).items():
            matched = len(terms & memory.words)
            if matched and memory.is_live_at(timestamp):
                ranked.append((-matched, -memory.written_at, memory_id))
        ranked.sort()
        return [memory_id for _, _, memory_id in ranked[:k]]

    # Level 3
    def add_with_ttl(
        self, timestamp: int, user_id: str, memory_id: str, text: str, ttl: int
    ) -> bool:
        memory = _Memory(text, timestamp, timestamp + ttl)
        return self._insert(timestamp, user_id, memory_id, memory)

    # Level 4
    def history(self, timestamp: int, user_id: str, memory_id: str) -> list[str]:
        memory = self._live(timestamp, user_id, memory_id)
        return list(memory.versions) if memory else []

    def rollback(self, timestamp: int, user_id: str, memory_id: str, version: int) -> bool:
        memory = self._live(timestamp, user_id, memory_id)
        if memory is None or not 1 <= version < len(memory.versions):
            return False
        self._users[user_id].move_to_end(memory_id)
        memory.write(memory.versions[version - 1], timestamp)
        return True

    def set_quota(self, timestamp: int, user_id: str, limit: int) -> list[str]:
        self._quotas[user_id] = limit
        return self._evict_down_to(timestamp, user_id, limit)

    def _live(self, timestamp: int, user_id: str, memory_id: str) -> _Memory | None:
        """The memory if it exists and has not expired; an expired one is dropped for good."""
        memories = self._users.get(user_id, {})
        memory = memories.get(memory_id)
        if memory is None:
            return None
        if not memory.is_live_at(timestamp):
            del memories[memory_id]
            return None
        return memory

    def _use(self, timestamp: int, user_id: str, memory_id: str) -> _Memory | None:
        """`_live`, and marks the memory as the user's most recently used one."""
        memory = self._live(timestamp, user_id, memory_id)
        if memory is not None:
            self._users[user_id].move_to_end(memory_id)
        return memory

    def _insert(self, timestamp: int, user_id: str, memory_id: str, memory: _Memory) -> bool:
        if self._live(timestamp, user_id, memory_id) is not None:
            return False
        quota = self._quotas.get(user_id)
        if quota is not None:
            self._evict_down_to(timestamp, user_id, quota - 1)
        self._users.setdefault(user_id, OrderedDict())[memory_id] = memory
        return True

    def _evict_down_to(self, timestamp: int, user_id: str, size: int) -> list[str]:
        """Drops the user's expired memories, then least recently used ones until `size` remain."""
        memories = self._users.get(user_id, OrderedDict())
        expired = [key for key, memory in memories.items() if not memory.is_live_at(timestamp)]
        for memory_id in expired:
            del memories[memory_id]
        evicted = []
        while len(memories) > size:
            memory_id, _ = memories.popitem(last=False)
            evicted.append(memory_id)
        return evicted
