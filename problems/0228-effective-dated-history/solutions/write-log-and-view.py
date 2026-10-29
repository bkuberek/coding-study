from bisect import bisect_left, bisect_right
from collections.abc import Callable
from datetime import date


class FieldHistory:
    def __init__(self) -> None:
        self.write_times: list[int] = []  # every write, in timestamp order
        self.writes: list[tuple[date, str]] = []
        self.dates: list[date] = []  # current view: one value per effective date, sorted
        self.values: list[str] = []

    def write(self, timestamp: int, effective_date: date, value: str) -> None:
        self.write_times.append(timestamp)
        self.writes.append((effective_date, value))
        slot = bisect_left(self.dates, effective_date)
        if slot < len(self.dates) and self.dates[slot] == effective_date:
            self.values[slot] = value  # a correction replaces the value for that date
        else:
            self.dates.insert(slot, effective_date)
            self.values.insert(slot, value)

    def current(self, on_date: date) -> str:
        slot = bisect_right(self.dates, on_date)
        return self.values[slot - 1] if slot else ""

    def as_known(self, on_date: date, known_at: int) -> str:
        best_date, best_value = None, ""
        known = bisect_right(self.write_times, known_at)  # writes made at or before known_at
        for effective_date, value in self.writes[:known]:
            # >= lets a later write for the same date replace an earlier one
            if effective_date <= on_date and (best_date is None or effective_date >= best_date):
                best_date, best_value = effective_date, value
        return best_value


class RecordHistory:
    def __init__(self) -> None:
        self._records: dict[str, dict[str, FieldHistory]] = {}

    def set_value(self, timestamp: int, record_id: str, field: str, effective_date: date, value: str) -> None:
        fields = self._records.setdefault(record_id, {})
        fields.setdefault(field, FieldHistory()).write(timestamp, effective_date, value)

    def get_value(self, timestamp: int, record_id: str, field: str, on_date: date) -> str:
        history = self._records.get(record_id, {}).get(field)
        return history.current(on_date) if history else ""

    def snapshot(self, timestamp: int, record_id: str, on_date: date) -> list[str]:
        return self._snapshot(record_id, lambda history: history.current(on_date))

    def get_value_as_known(self, timestamp: int, record_id: str, field: str, on_date: date, known_at: int) -> str:
        history = self._records.get(record_id, {}).get(field)
        return history.as_known(on_date, known_at) if history else ""

    def snapshot_as_known(self, timestamp: int, record_id: str, on_date: date, known_at: int) -> list[str]:
        return self._snapshot(record_id, lambda history: history.as_known(on_date, known_at))

    def _snapshot(self, record_id: str, read: Callable[[FieldHistory], str]) -> list[str]:
        fields = self._records.get(record_id, {})
        entries = ((field, read(fields[field])) for field in sorted(fields))
        return [f"{field}={value}" for field, value in entries if value]
