from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def bond_premium(contract_price: Decimal, band_floors: list[Decimal], rates_per_thousand: list[Decimal]) -> Decimal:
    total = Decimal(0)  # sum of slice * rate, exact
    for band, (lower, rate) in enumerate(zip(band_floors, rates_per_thousand, strict=True)):
        if contract_price <= lower:
            break
        upper = band_floors[band + 1] if band + 1 < len(band_floors) else contract_price
        total += (min(contract_price, upper) - lower) * rate
    # Dividing by 1000 only moves the decimal point, so it is exact; round once, at the end.
    return (total / 1000).quantize(CENT, rounding=ROUND_HALF_UP)
