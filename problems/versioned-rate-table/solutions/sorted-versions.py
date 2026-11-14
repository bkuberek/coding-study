from bisect import bisect_right
from datetime import date
from decimal import Decimal

NOT_FOUND = Decimal(-1)


class RateTable:
    def __init__(self) -> None:
        # Parallel lists sorted by effective date; equal dates stay in publish order.
        self._dates: list[date] = []
        self._versions: list[tuple[int, dict[str, Decimal]]] = []
        self._published = 0

    def publish(self, effective_date: date, class_codes: list[str], rates: list[Decimal]) -> None:
        self._published += 1
        slot = bisect_right(self._dates, effective_date)  # after any version with the same date
        self._dates.insert(slot, effective_date)
        # Copy into a fresh dict, so a published version never changes afterwards.
        self._versions.insert(slot, (self._published, dict(zip(class_codes, rates, strict=True))))

    def rate_as_of(self, on_date: date, class_code: str) -> Decimal:
        slot = bisect_right(self._dates, on_date)
        if slot == 0:
            return NOT_FOUND
        return self._versions[slot - 1][1].get(class_code, NOT_FOUND)

    def version_as_of(self, on_date: date) -> int:
        slot = bisect_right(self._dates, on_date)
        return self._versions[slot - 1][0] if slot > 0 else -1
