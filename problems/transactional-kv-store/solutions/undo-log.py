from bisect import bisect_right
from collections import Counter


class TransactionalStore:
    def __init__(self) -> None:
        self._data: dict[str, str] = {}  # the current view, open transactions included
        self._counts: Counter[str] = Counter()
        # One undo log per open transaction, innermost last: key -> value before its first change.
        self._undo: list[dict[str, str | None]] = []
        # Permanent values per key as (sequence, value or None); a commit or an outside write
        # advances the sequence, and a snapshot remembers the sequence of its commit.
        self._history: dict[str, list[tuple[int, str | None]]] = {}
        self._sequence = 0
        self._snapshots: list[int] = []

    # Level 1
    def set(self, timestamp: int, key: str, value: str) -> None:
        self._change(key, value)

    def get(self, timestamp: int, key: str) -> str:
        return self._data.get(key, "")

    def remove(self, timestamp: int, key: str) -> bool:
        if key not in self._data:
            return False
        self._change(key, None)
        return True

    def count(self, timestamp: int, value: str) -> int:
        return self._counts[value]

    # Level 2
    def begin(self, timestamp: int) -> None:
        self._undo.append({})

    def rollback(self, timestamp: int) -> bool:
        if not self._undo:
            return False
        for key, previous in self._undo.pop().items():
            self._assign(key, previous)
        return True

    # Level 3
    def depth(self, timestamp: int) -> int:
        return len(self._undo)

    # Level 4
    def commit(self, timestamp: int) -> int:
        if not self._undo:
            return -1
        changed = self._undo.pop()
        if self._undo:
            for key, previous in changed.items():
                self._undo[-1].setdefault(key, previous)
            return 0
        self._make_permanent(changed.keys())
        self._snapshots.append(self._sequence)
        return len(self._snapshots)

    def get_snapshot(self, timestamp: int, version: int, key: str) -> str:
        if not 1 <= version <= len(self._snapshots):
            return ""
        history = self._history.get(key, [])
        position = bisect_right(history, self._snapshots[version - 1], key=lambda entry: entry[0])
        return (history[position - 1][1] if position else None) or ""

    def _change(self, key: str, value: str | None) -> None:
        if self._undo:
            self._undo[-1].setdefault(key, self._data.get(key))
            self._assign(key, value)
        else:
            self._assign(key, value)
            self._make_permanent([key])

    def _assign(self, key: str, value: str | None) -> None:
        previous = self._data.get(key)
        if previous is not None:
            self._counts[previous] -= 1
        if value is None:
            self._data.pop(key, None)
        else:
            self._data[key] = value
            self._counts[value] += 1

    def _make_permanent(self, keys) -> None:
        self._sequence += 1
        for key in keys:
            self._history.setdefault(key, []).append((self._sequence, self._data.get(key)))
