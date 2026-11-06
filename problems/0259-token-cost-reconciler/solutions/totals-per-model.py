from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")
TOKENS_PER_RATE = 1_000_000
NO_AMOUNT = "-"


def reconcile_usage(
    price_models: list[str],
    prices: list[list[Decimal]],
    call_models: list[str],
    call_tokens: list[list[int]],
    reported_models: list[str],
    reported_tokens: list[list[int]],
    reported_costs: list[Decimal],
    tolerance: Decimal,
) -> list[list[str]]:
    rates_of = dict(zip(price_models, prices, strict=True))
    logged = _token_totals(call_models, call_tokens)
    reported = _token_totals(reported_models, reported_tokens)
    charged: dict[str, Decimal] = {}
    for model, cost in zip(reported_models, reported_costs, strict=True):
        charged[model] = charged.get(model, Decimal(0)) + cost

    rows = []
    for model in sorted(logged.keys() | reported.keys()):
        tokens, rates, cost = logged.get(model), rates_of.get(model), charged.get(model)
        computed = _cost(tokens, rates) if tokens is not None and rates is not None else None
        status = _status(tokens, computed, reported.get(model), cost, tolerance)
        rows.append([model, status, _amount(computed), _amount(cost)])
    return rows


def _token_totals(models: list[str], tokens: list[list[int]]) -> dict[str, list[int]]:
    totals: dict[str, list[int]] = {}
    for model, row in zip(models, tokens, strict=True):
        total = totals.setdefault(model, [0, 0, 0])
        for column, count in enumerate(row):
            total[column] += count
    return totals


def _cost(tokens: list[int], rates: list[Decimal]) -> Decimal:
    input_tokens, cached_tokens, output_tokens = tokens
    input_rate, cached_rate, output_rate = rates
    exact = (
        (input_tokens - cached_tokens) * input_rate
        + cached_tokens * cached_rate
        + output_tokens * output_rate
    )
    return (exact / TOKENS_PER_RATE).quantize(CENT, rounding=ROUND_HALF_UP)


def _status(
    tokens: list[int] | None,
    computed: Decimal | None,
    reported_tokens: list[int] | None,
    charged: Decimal | None,
    tolerance: Decimal,
) -> str:
    if tokens is None:
        return "not-in-log"
    if computed is None:
        return "unpriced-model"  # it has calls, so only a missing price leaves no computed cost
    if reported_tokens is None or charged is None:
        return "missing-from-report"
    if tokens != reported_tokens:
        return "token-mismatch"
    return "cost-mismatch" if abs(computed - charged) > tolerance else "ok"


def _amount(value: Decimal | None) -> str:
    return NO_AMOUNT if value is None else f"{value:.2f}"
