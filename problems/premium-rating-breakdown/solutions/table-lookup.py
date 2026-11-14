from bisect import bisect_right
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def rate_premium(
    class_code: str,
    payroll: Decimal,
    experience_mod: Decimal,
    schedule_credit: Decimal,
    class_codes: list[str],
    base_rates: list[Decimal],
    band_lower_bounds: list[Decimal],
    band_factors: list[Decimal],
    minimum_premium: Decimal,
) -> list[Decimal]:
    rates = dict(zip(class_codes, base_rates, strict=True))
    # Index of the last lower bound <= payroll; -1 when payroll is below every band.
    band = bisect_right(band_lower_bounds, payroll) - 1
    if class_code not in rates or band < 0:
        return []
    running = payroll / 1000 * rates[class_code]  # exact: dividing by 1000 only moves the point
    trail = [running]
    for factor in (band_factors[band], experience_mod, 1 - schedule_credit):
        running *= factor
        trail.append(running)
    trail.append(max(running, minimum_premium).quantize(CENT, rounding=ROUND_HALF_UP))
    return trail
