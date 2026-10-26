from bisect import bisect_right
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class _Version:
    """One write to a field: a value (None for a deletion), from `since` until `expires_at`."""

    since: int
    value: str | None
    expires_at: int | None

    def visible_at(self, moment: int) -> bool:
        if self.value is None:
            return False
        return self.expires_at is None or moment < self.expires_at


class _FieldHistory:
    """Every version of one field, oldest first; timestamps arrive in increasing order."""

    def __init__(self) -> None:
        self._versions: list[_Version] = []

    def record(self, version: _Version) -> None:
        self._versions.append(version)

    def value_at(self, moment: int) -> str | None:
        position = bisect_right(self._versions, moment, key=lambda version: version.since)
        if position == 0:
            return None
        version = self._versions[position - 1]
        return version.value if version.visible_at(moment) else None


class InMemoryDatabase:
    def __init__(self) -> None:
        self._records: dict[str, dict[str, _FieldHistory]] = {}

    # Level 1
    def set(self, timestamp: int, key: str, field: str, value: str) -> None:
        self._write(key, field, _Version(timestamp, value, None))

    def get(self, timestamp: int, key: str, field: str) -> str:
        return self._value_at(key, field, timestamp) or ""

    def remove(self, timestamp: int, key: str, field: str) -> bool:
        if self._value_at(key, field, timestamp) is None:
            return False
        self._write(key, field, _Version(timestamp, None, None))
        return True

    # Level 2
    def scan(self, timestamp: int, key: str) -> list[str]:
        return self._scan(key, "", timestamp)

    def scan_by_prefix(self, timestamp: int, key: str, prefix: str) -> list[str]:
        return self._scan(key, prefix, timestamp)

    # Level 3
    def set_with_ttl(self, timestamp: int, key: str, field: str, value: str, ttl: int) -> None:
        self._write(key, field, _Version(timestamp, value, timestamp + ttl))

    # Level 4
    def get_at(self, timestamp: int, key: str, field: str, at_timestamp: int) -> str:
        return self._value_at(key, field, at_timestamp) or ""

    def scan_at(self, timestamp: int, key: str, at_timestamp: int) -> list[str]:
        return self._scan(key, "", at_timestamp)

    def _write(self, key: str, field: str, version: _Version) -> None:
        fields = self._records.setdefault(key, {})
        fields.setdefault(field, _FieldHistory()).record(version)

    def _value_at(self, key: str, field: str, moment: int) -> str | None:
        history = self._records.get(key, {}).get(field)
        return history.value_at(moment) if history else None

    def _scan(self, key: str, prefix: str, moment: int) -> list[str]:
        entries = []
        for field, history in self._records.get(key, {}).items():
            if field.startswith(prefix) and (value := history.value_at(moment)) is not None:
                entries.append((field, value))
        return [f"{field}({value})" for field, value in sorted(entries)]
