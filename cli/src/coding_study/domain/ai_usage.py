"""What a request costs the daily token cap, and the usage a day's requests add up to
(docs/specs/ai.md#usage-and-the-daily-token-cap)."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from coding_study.domain.ai import AiTask, Provider
from coding_study.domain.ai_models import Usage
from coding_study.domain.ai_records import CallOutcome, ModelCall
from coding_study.domain.ai_routing import task_spec

BYTES_PER_TOKEN = 4


def estimate_input_tokens(text: str) -> int:
    """The request's text in bytes divided by 4, rounded up."""
    return -(-len(text.encode("utf-8")) // BYTES_PER_TOKEN)


def estimate_tokens(text: str, max_output_tokens: int) -> int:
    """What the cap counts for a request before it leaves, and for one with no usage report: the
    input estimate plus the task's output limit."""
    return estimate_input_tokens(text) + max_output_tokens


def counted_tokens(usage: Usage | None, estimate: int) -> int:
    """The reported input and output tokens; the estimate when the provider reported none."""
    return usage.total_tokens if usage is not None else estimate


def cap_refusal(task: AiTask, counted_today: int, estimate: int, cap: int) -> str | None:
    """The refusal when today's counted tokens and the request's estimate would pass the cap;
    None when it fits."""
    if counted_today + estimate <= cap:
        return None
    return (
        f"the daily token cap is reached: {counted_today:,} of {cap:,} tokens today, and this "
        f"{task_spec(task).noun} needs up to {estimate:,}; raise ai.daily_token_cap or wait "
        "until tomorrow"
    )


@dataclass(frozen=True, slots=True)
class UsageCounters:
    """A set of requests added up."""

    requests: int = 0
    failed: int = 0
    """Requests that failed or were interrupted."""
    input_tokens: int = 0
    """As reported; a request without a usage report adds none."""
    output_tokens: int = 0
    counted_tokens: int = 0
    """What the daily cap counts."""
    cost_usd: float | None = None
    """The sum of the costs providers reported; None when none did."""
    requests_without_cost: int = 0


def add_up(calls: Iterable[ModelCall]) -> UsageCounters:
    requests = failed = input_tokens = output_tokens = counted = without_cost = 0
    cost: float | None = None
    for call in calls:
        requests += 1
        failed += call.outcome is not CallOutcome.OK
        input_tokens += call.input_tokens or 0
        output_tokens += call.output_tokens or 0
        counted += call.counted_tokens
        if call.cost_usd is None:
            without_cost += 1
        else:
            cost = (cost or 0.0) + call.cost_usd
    return UsageCounters(requests, failed, input_tokens, output_tokens, counted, cost, without_cost)


@dataclass(frozen=True, slots=True)
class UsageRow:
    """One local day, provider, model and purpose with a request."""

    day: date
    provider: Provider
    model: str
    purpose: AiTask
    counters: UsageCounters


def usage_rows(calls: Iterable[ModelCall]) -> tuple[UsageRow, ...]:
    """One row per day, provider, model and purpose, oldest day first, then by provider, model
    and purpose."""
    groups: dict[tuple[date, Provider, str, AiTask], list[ModelCall]] = {}
    for call in calls:
        key = (call.local_day, call.provider, call.model, call.purpose)
        groups.setdefault(key, []).append(call)
    return tuple(
        UsageRow(day, provider, model, purpose, add_up(groups[(day, provider, model, purpose)]))
        for day, provider, model, purpose in sorted(groups)
    )
