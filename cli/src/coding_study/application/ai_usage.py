"""Usage by day, from the requests this workspace stored
(docs/specs/ai.md#usage-and-the-daily-token-cap)."""

from dataclasses import dataclass
from datetime import date, timedelta

from coding_study.application.environment import Environment
from coding_study.domain.ai_usage import UsageCounters, UsageRow, add_up, usage_rows
from coding_study.domain.errors import UsageError

MIN_DAYS = 1
MAX_DAYS = 366
DEFAULT_DAYS = 7


@dataclass(frozen=True, slots=True)
class UsageReport:
    days: int
    first: date
    """The first day covered."""
    last: date
    """The last day covered: today."""
    cap: int
    rows: tuple[UsageRow, ...]
    """Oldest day first; a day, provider, model and purpose with no request has none."""
    total: UsageCounters


def usage_report(environment: Environment, days: int = DEFAULT_DAYS) -> UsageReport:
    """The requests of the last `days` local days, today included. Raises UsageError for a number
    of days outside 1 to 366."""
    if not MIN_DAYS <= days <= MAX_DAYS:
        raise UsageError(f"--days must be from {MIN_DAYS} to {MAX_DAYS}")
    today = environment.clock.local_date(environment.clock.now())
    first = today - timedelta(days=days - 1)
    calls = environment.ai_store.calls_between(first, today)
    return UsageReport(
        days, first, today, environment.config.ai.daily_token_cap, usage_rows(calls), add_up(calls)
    )
