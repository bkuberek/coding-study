"""The estimate, the cap and the usage a day's requests add up to
(docs/specs/ai.md#usage-and-the-daily-token-cap)."""

from datetime import UTC, date, datetime

import pytest

from coding_study.domain.ai import AiTask, Provider
from coding_study.domain.ai_models import ProviderErrorKind, Usage
from coding_study.domain.ai_records import CallOutcome, ModelCall
from coding_study.domain.ai_usage import (
    UsageCounters,
    add_up,
    cap_refusal,
    counted_tokens,
    estimate_input_tokens,
    estimate_tokens,
    usage_rows,
)

DAY = date(2026, 11, 16)
INSTANT = datetime(2026, 11, 16, 10, 0, tzinfo=UTC)


def call(
    day: date = DAY,
    provider: Provider = Provider.ANTHROPIC,
    model: str = "m",
    purpose: AiTask = AiTask.REVIEW,
    outcome: CallOutcome = CallOutcome.OK,
    input_tokens: int | None = 100,
    output_tokens: int | None = 20,
    counted: int = 120,
    cost: float | None = None,
) -> ModelCall:
    return ModelCall(
        purpose=purpose,
        provider=provider,
        model=model,
        tier=None,
        attempt_id=None,
        local_day=day,
        started_at=INSTANT,
        ended_at=INSTANT,
        outcome=outcome,
        error=None if outcome is CallOutcome.OK else ProviderErrorKind.TIMEOUT,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        counted_tokens=counted,
        cost_usd=cost,
    )


@pytest.mark.parametrize(
    ("text", "tokens"),
    [("", 0), ("a", 1), ("abcd", 1), ("abcde", 2), ("é" * 4, 2), ("日本", 2), ("x" * 4001, 1001)],
)
def test_the_estimate_is_the_bytes_over_four_rounded_up(text, tokens):
    assert estimate_input_tokens(text) == tokens


def test_a_request_is_estimated_at_its_input_plus_its_output_limit():
    assert estimate_tokens("x" * 8, 16_000) == 16_002


def test_counted_tokens_are_the_reported_ones_else_the_estimate():
    assert counted_tokens(Usage(900, 100, 0.5), 5_000) == 1_000
    assert counted_tokens(Usage(0, 0), 5_000) == 0
    assert counted_tokens(None, 5_000) == 5_000


def test_a_request_that_reaches_the_cap_exactly_still_goes():
    assert cap_refusal(AiTask.REVIEW, 481_200, 18_800, 500_000) is None
    assert cap_refusal(AiTask.REVIEW, 0, 500_000, 500_000) is None


def test_a_request_one_token_over_the_cap_is_refused_with_the_figures():
    assert cap_refusal(AiTask.REVIEW, 481_201, 18_800, 500_000) is not None
    assert cap_refusal(AiTask.REVIEW, 498_120, 18_800, 500_000) == (
        "the daily token cap is reached: 498,120 of 500,000 tokens today, and this review needs "
        "up to 18,800; raise ai.daily_token_cap or wait until tomorrow"
    )


def test_the_cap_names_the_check_as_a_check():
    assert "this check needs up to 1,010" in (cap_refusal(AiTask.CHECK, 10, 1_010, 1_000) or "")


def test_nothing_adds_up_to_zero_and_an_unknown_cost():
    assert add_up([]) == UsageCounters()
    assert UsageCounters().cost_usd is None


def test_requests_add_up_with_failures_tokens_and_the_costs_providers_reported():
    counters = add_up(
        [
            call(cost=0.00002),
            call(cost=0.00001, input_tokens=40, output_tokens=12, counted=52),
            call(outcome=CallOutcome.FAILED, input_tokens=None, output_tokens=None, counted=5_000),
            call(outcome=CallOutcome.INTERRUPTED, input_tokens=None, output_tokens=None, counted=7),
        ]
    )
    assert counters.requests == 4
    assert counters.failed == 2
    assert counters.input_tokens == 140
    assert counters.output_tokens == 32
    assert counters.counted_tokens == 120 + 52 + 5_000 + 7
    assert counters.cost_usd == pytest.approx(0.00003)
    assert counters.requests_without_cost == 2


def test_a_zero_cost_is_a_known_cost():
    counters = add_up([call(cost=0.0)])
    assert counters.cost_usd == 0.0
    assert counters.requests_without_cost == 0


def test_requests_without_a_reported_cost_leave_the_cost_unknown():
    counters = add_up([call(), call()])
    assert counters.cost_usd is None
    assert counters.requests_without_cost == 2


def test_rows_group_by_day_provider_model_and_purpose_in_that_order():
    rows = usage_rows(
        [
            call(DAY, Provider.OPENROUTER, "b", AiTask.CHECK),
            call(date(2026, 11, 15), Provider.OPENROUTER, "b", AiTask.CHECK),
            call(DAY, Provider.ANTHROPIC, "z", AiTask.REVIEW),
            call(DAY, Provider.ANTHROPIC, "a", AiTask.REVIEW),
            call(DAY, Provider.ANTHROPIC, "a", AiTask.CHECK),
            call(DAY, Provider.ANTHROPIC, "a", AiTask.REVIEW),
        ]
    )
    assert [(r.day, r.provider, r.model, r.purpose, r.counters.requests) for r in rows] == [
        (date(2026, 11, 15), Provider.OPENROUTER, "b", AiTask.CHECK, 1),
        (DAY, Provider.ANTHROPIC, "a", AiTask.CHECK, 1),
        (DAY, Provider.ANTHROPIC, "a", AiTask.REVIEW, 2),
        (DAY, Provider.ANTHROPIC, "z", AiTask.REVIEW, 1),
        (DAY, Provider.OPENROUTER, "b", AiTask.CHECK, 1),
    ]


def test_a_row_adds_up_its_requests():
    (row,) = usage_rows([call(counted=120), call(counted=30, input_tokens=20, output_tokens=10)])
    assert row.counters.counted_tokens == 150
    assert row.counters.input_tokens == 120


def test_no_requests_make_no_rows():
    assert usage_rows([]) == ()
