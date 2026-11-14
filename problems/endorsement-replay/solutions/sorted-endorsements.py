from bisect import bisect_left, bisect_right
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
OUTSIDE_TERM = Decimal(-1)


class EndorsedPolicy:
    def __init__(self, term_start: date, term_end: date, full_term_premium: Decimal) -> None:
        self._term_start = term_start
        self._term_end = term_end
        self._term_days = (term_end - term_start).days
        # Parallel lists sorted by date: the full-term premium in force from each date on.
        self._dates = [term_start]
        self._premiums = [full_term_premium]

    def endorse(self, effective_date: date, full_term_premium: Decimal) -> bool:
        if not self._term_start <= effective_date < self._term_end:
            return False
        slot = bisect_left(self._dates, effective_date)
        if slot < len(self._dates) and self._dates[slot] == effective_date:
            self._premiums[slot] = full_term_premium  # same date: the later endorsement corrects it
        else:
            self._dates.insert(slot, effective_date)
            self._premiums.insert(slot, full_term_premium)
        return True

    def premium_on(self, on_date: date) -> Decimal:
        if not self._term_start <= on_date < self._term_end:
            return OUTSIDE_TERM
        return self._premiums[bisect_right(self._dates, on_date) - 1]

    def written_premium(self) -> Decimal:
        return self.earned_premium(self._term_end)

    def earned_premium(self, as_of_date: date) -> Decimal:
        cutoff = min(max(as_of_date, self._term_start), self._term_end)
        weighted = Decimal(0)  # sum of premium * days over the segments before the cutoff, exact
        for segment, (start, premium) in enumerate(zip(self._dates, self._premiums)):
            if start >= cutoff:
                break
            end = self._dates[segment + 1] if segment + 1 < len(self._dates) else self._term_end
            weighted += premium * (min(end, cutoff) - start).days
        return (weighted / self._term_days).quantize(CENT, rounding=ROUND_HALF_UP)
