from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def rate_change_impact(
    old_codes: list[str], old_rates: list[Decimal], new_codes: list[str], new_rates: list[Decimal]
) -> list[list[str]]:
    old = dict(zip(old_codes, old_rates, strict=True))
    new = dict(zip(new_codes, new_rates, strict=True))
    changed = []
    for code, rate in new.items():
        if code in old and rate != old[code]:  # Decimal equality is by value: 12.50 == 12.5
            percent = ((rate - old[code]) * 100 / old[code]).quantize(CENT, rounding=ROUND_HALF_UP)
            if percent == 0:
                percent = abs(percent)  # a tiny decrease rounds to -0.00; report it as 0.00
            changed.append((percent, code))
    changed.sort(key=lambda entry: (-entry[0], entry[1]))  # numeric order, not text order
    added = sorted(code for code in new if code not in old)
    removed = sorted(code for code in old if code not in new)
    return (
        [[code, "changed", str(percent)] for percent, code in changed]
        + [[code, "added", ""] for code in added]
        + [[code, "removed", ""] for code in removed]
    )
