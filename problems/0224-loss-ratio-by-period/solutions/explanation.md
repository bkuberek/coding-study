# Loss Ratio by Period: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| period-buckets | optimal | O(e + l + p) | O(p) | default answer |

`e` and `l` are the numbers of earned-premium and loss entries, and `p` is the number of reported periods.

## Approach: period-buckets (Number the periods arithmetically and sum into buckets)

### Intuition

Periods aligned to January are just integer division of a month counter, so each entry goes straight to its bucket without any date arithmetic.

### Algorithm

1. The period number of a day is `(year * 12 + month - 1) div periodMonths`.
2. Number the period of `fromDate` (the first) and of `toDate`; the count is the difference plus one.
3. Make two zeroed arrays of that length, for earned premium and for losses.
4. Add each entry to its bucket (its period number minus the first) when that falls inside the array.
5. For each bucket, report `-1` when the premium is zero, otherwise losses divided by premium, rounded to 4 decimal places, half up.

### Correctness

The month counter increases with the calendar, and every run of `periodMonths` consecutive counter values that starts at a multiple of `periodMonths` is one period, because `periodMonths` divides 12. The period number is therefore exact and consecutive, and each entry is added to exactly one bucket. Dividing the exact totals and rounding once is the defined answer.

### Complexity

- Time: O(e + l + p) — each entry is bucketed in constant time, and each of the p periods yields one ratio.
- Space: O(p) — two totals per period.

### Trade-offs

A hash map keyed by period number works too but needs a separate pass to emit the empty periods in order. Sorting the entries first costs O(n log n) for nothing. Deriving the earned premium from policies is a bigger problem (see `earned-premium-as-of`).

### Pitfalls and edge cases

- Clipping entries to the exact dates instead of counting whole periods (`h1`, `h2`).
- A premium total of zero, including one written `0.00`, must not be divided by (`ex2`, `h4`, `h9`).
- Half-up rounding at 4 places (`h3`, `h8`).
- Ratios above 1 (`h7`).
- Periods of 2, 4, 6 and 12 months (`h11`, `h5`, `h6`, `ex3`).
- Year boundaries (`h6`, `h10`) and the leap day (`h8`).
- Java's `BigDecimal.equals(BigDecimal.ZERO)` is false for `0.00`; test with `signum()`.
- Kotlin's `/` on `BigDecimal`.

### Language notes

- Python: `(day.year * 12 + day.month - 1) // period_months`. `Decimal` division is exact enough at the default 28 digits for these sizes, so `(loss / premium).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)` is the rounded exact ratio. `premium == 0` compares by value.
- TypeScript: the period number comes from `Number(day.slice(0, 4)) * 12 + Number(day.slice(5, 7)) - 1`, then `Math.floor(... / periodMonths)`. Zero test: `earned.eq(new Decimal(0))`. `loss.div(earned, 4, "HALF_UP")` divides and rounds in one call.
- Java: `day.getYear() * 12 + day.getMonthValue() - 1`. Test for zero with `signum() == 0`, never `equals(BigDecimal.ZERO)`: a `0.00` total is not equal to `ZERO`, and dividing by it throws. `loss.divide(earned, 4, RoundingMode.HALF_UP)` rounds in one call; the result is a `List<BigDecimal>`.
- Kotlin: the same calls with `signum() == 0` and `divide(earned, 4, RoundingMode.HALF_UP)`. `loss / earned` keeps the loss's scale and rounds half-even: 1200 / 3000 would become 0 (`ex1`).
