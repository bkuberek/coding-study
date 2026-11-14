from typing import NamedTuple

ACCEPTED = 1
REFUSED = 0
NO_VALUE = ""


class _Entry(NamedTuple):
    version: int
    value: str


NEVER_CHANGED = _Entry(0, NO_VALUE)


class MemoryStore:
    def __init__(self) -> None:
        # A forgotten key keeps its entry, with no value, so its version never goes back.
        self._entries: dict[str, _Entry] = {}

    def get(self, key: str) -> str:
        return self._entries.get(key, NEVER_CHANGED).value

    def version(self, key: str) -> int:
        return self._entries.get(key, NEVER_CHANGED).version

    def write(self, key: str, expected_version: int, value: str) -> list[int]:
        return self._change(key, expected_version, value)

    def forget(self, key: str, expected_version: int) -> list[int]:
        return self._change(key, expected_version, NO_VALUE)

    def _change(self, key: str, expected_version: int, value: str) -> list[int]:
        current = self.version(key)
        if expected_version != current:
            return [REFUSED, current]
        self._entries[key] = _Entry(current + 1, value)
        return [ACCEPTED, current + 1]
