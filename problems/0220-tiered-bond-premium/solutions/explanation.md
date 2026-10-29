# Tiered Bond Premium: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| band-walk | optimal | O(b) | O(1) | default answer |

`b` is the number of bands.

## Approach: band-walk (Walk the bands and charge the slice of the price inside each)

### Intuition

This is how income-tax brackets work. A rate applies only to the slice of the price inside its band, so crossing a floor never makes the whole price dearer, only the part above it.

### Algorithm

1. Start with a running total of 0.
2. For each band in order, stop once the price is at or below the band's floor.
3. Otherwise add `(min(price, next floor) - floor) * rate` to the total, using the price itself as the ceiling of the last band.
4. Divide the total by 1,000 and round it once to cents, half up.

### Correctness

The slices partition the interval from `bandFloors[0]` to `contractPrice`, so each unit of price is charged exactly once, at its own band's rate. Products and sums of exact decimals have no error, and dividing by 1,000 only moves the decimal point; the single rounding is the defined answer.

### Complexity

- Time: O(b) — one pass over the bands.
- Space: O(1) — a running total.

### Trade-offs

Precomputing the cumulative charge at every floor and binary-searching the price's band answers many quotes in O(log b) each, which pays off when one table prices many bonds. Rounding each band's charge instead of the total changes some results (`h12`). A step schedule is simpler but unfair just above a floor: one extra cent of price can raise the premium by thousands.

### Pitfalls and edge cases

- Charging the whole price at the top band's rate instead of only its slice.
- A price exactly on a floor: the band starting there gets an empty slice (`ex2`, `h11`).
- A price below the first floor pays nothing, and a price just above it pays only for the slice above (`h4`, `h5`).
- Half-cent ties round up, not to even (`h2`, `h12`).
- One cent on either side of a floor (`h6`, `h7`).
- A zero price and a zero rate (`h1`, `h9`).
- Floating point cannot hold these rates exactly.
- Kotlin's `/` on `BigDecimal`.

### Language notes

- Python: `Decimal` arithmetic is exact for these sizes; `total / 1000` only moves the point, and `quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)` rounds once.
- TypeScript: accumulate `slice.times(rate)` with `plus`, compare with `lt` and `lte`, and finish with `total.movePointLeft(3).round(2, "HALF_UP")`. `movePointLeft` is exact, so it cannot lose a digit before the one rounding.
- Java: `contractPrice.min(upper).subtract(lower).multiply(rate)`, stop with `compareTo(lower) <= 0`, and finish with `total.movePointLeft(3).setScale(2, RoundingMode.HALF_UP)`.
- Kotlin: `(minOf(contractPrice, upper) - lower) * rate`, then `movePointLeft(3).setScale(2, RoundingMode.HALF_UP)`. Do not write `total / BigDecimal(1000)`: Kotlin's `/` keeps the dividend's scale and rounds half-even, so `h2` (0.005 becomes 0.00) and `h12` (1.005 becomes 1.00) fail.
