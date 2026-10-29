# Rate Change Impact: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| index-and-diff | optimal | O(n log n) | O(n) | default answer |

## Approach: index-and-diff (Index both tables by code then diff and sort)

### Intuition

A diff of two maps, then a presentation problem: an exact percent, one rounding, a fixed text format and a numeric sort.

### Algorithm

1. Index the old and the new table by code.
2. For each code in both tables whose rates differ by value, compute `(new - old) * 100 / old`, rounded to two decimal places, half up. A result of zero is written without a sign.
3. Codes only in the new table are added; codes only in the old table are removed.
4. Sort the changed rows by percent descending as numbers, ties by code; sort the added and the removed codes by code.
5. Format each percent with exactly two fractional digits and concatenate the three groups.

### Correctness

Every code lands in exactly one group, or in none when its rate is unchanged. The sort key of the changed rows is the rounded number that is displayed, so the order of the rows matches the values a reader sees; ties are broken by code, which makes the order total. One rounding of the exact quotient is the defined percent.

### Complexity

- Time: O(n log n) — building the indexes is linear; sorting the rows dominates.
- Space: O(n) — the two indexes and the output.

### Trade-offs

Two tables sorted by code can be merged in O(n) time without hash maps. Sorting by the exact change instead of the rounded one can order rows that look equal in a different way (`h10`).

### Pitfalls and edge cases

- Equality that is sensitive to scale: `12.50` and `12.5` are the same rate (`ex2`, `h2`).
- A tiny decrease rounds to `-0.00`; report `0.00` (`h3`).
- Half-up ties round away from zero on both signs: 0.005 becomes 0.01 and -0.005 becomes -0.01 (`h4`).
- Sorting the percent as text puts `9.00` above `10.00`; sort the numbers (`h5`).
- Extreme changes (`h7`, `h8`) and empty tables (`ex3`, `h1`, `h6`).
- Codes order as text (`h9`).
- Different changes that round to the same percent order by code (`h10`).
- Kotlin's `/` and `!=` on `BigDecimal`.

### Language notes

- Python: `Decimal` compares by value, so `rate != old[code]` is the change test. `quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)` keeps both digits when printed with `str`, but a tiny decrease quantizes to `Decimal("-0.00")`, whose text is `-0.00`, so take `abs` when the result is zero. `f"{x:.2f}"` on an unrounded `Decimal` rounds half-even (`f"{Decimal('0.125'):.2f}"` is `0.12`), so quantize first.
- TypeScript: `newRate.minus(oldRate).times(new Decimal(100)).div(oldRate, 2, "HALF_UP")`. `toString()` keeps the scale (`"4.80"`), and the underlying `bigint` has no negative zero. Sort with `b.percent.cmp(a.percent)` and fall back to a code comparison written with `<`, not `localeCompare`.
- Java: two `HashMap<String, BigDecimal>`. The change test is `compareTo(...) != 0`, because `equals` treats `12.50` and `12.5` as different. `subtract(old).multiply(BigDecimal.valueOf(100)).divide(old, 2, RoundingMode.HALF_UP).toPlainString()` has no negative zero. Sort with `Comparator.comparing(Change::percent, Comparator.reverseOrder()).thenComparing(Change::code)`: calling `reversed()` on the whole chain would reverse the tie-break too.
- Kotlin: `!=` on `BigDecimal` is `equals`, so use `compareTo(...) != 0`. Sort with `compareByDescending<Change> { it.percent }.thenBy { it.code }`. A plain `/` rounds half-even at the dividend's scale: `h4` (1.00 / 200 would become 0.00) catches it.
