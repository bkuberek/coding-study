import time
from datetime import UTC, date, datetime


class SystemClock:
    """`Clock` from the system time and the local time zone."""

    def now(self) -> datetime:
        return datetime.now(UTC)

    def local_date(self, instant: datetime) -> date:
        return instant.astimezone().date()

    def monotonic(self) -> float:
        return time.monotonic()
