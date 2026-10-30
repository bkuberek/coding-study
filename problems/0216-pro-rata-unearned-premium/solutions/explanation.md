# Pro-Rata Unearned Premium: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| day-count | optimal | O(1) | O(1) | default answer |

## Approach: day-count (Count days with the date library and round once)

### Intuition

The refund is the premium times the share of the term that has not been used, and the share is measured in days: the days from the change date to the end of the term, over the days of the whole term.

### Algorithm

1. If `changeDate` is before `termStart` or after `termEnd`, return `-1`.
2. `remaining` is the number of days from `changeDate` to `termEnd`; `termDays` is the number of days from `termStart` to `termEnd`.
3. Multiply `termPremium` by `remaining`, divide by `termDays`, and round the result to cents, half up.

### Correctness

The term is half-open, so every day of it is counted exactly once and the shares of consecutive days add up to the whole term: a change on `termStart` has `remaining == termDays` and refunds the whole premium, and a change on `termEnd` has `remaining == 0` and refunds nothing. Multiplying first keeps the product exact, and one rounding of the exact quotient is the defined answer.

### Complexity

- Time: O(1) — two date differences and one division.
- Space: O(1) — a few scalars.

### Trade-offs

A 365-day basis gives a different share to every day of a leap year, and a term-length basis (as here) makes the whole term always add up to exactly the premium. Rounding once is also a choice: refunding each day separately and summing the rounded amounts can differ from the whole by a few cents.

### Pitfalls and edge cases

- Treating the end date as covered is off by one day.
- Floating point cannot hold `1200 * 183 / 365` exactly, and rounds ties unpredictably. Use the decimal type.
- Leap years change the number of days of the term (`h1`, `h2`, `h9`).
- Half-cent ties round up, not to even (`h3`, `h4`).
- Dividing before multiplying loses precision in the intermediate result.
- A change date before the term or after it returns `-1` (`h5`, `h6`), while the first and last day of the range are valid (`ex2`, `ex3`).
- A one-day term (`h8`) and a zero premium (`h10`) are valid.

### Language notes

- Python: `(term_end - change_date).days` counts days between two `date` values; `quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)` rounds once.
- TypeScript: a date is an `IsoDate`, a plain ISO string, so dates compare chronologically. Date-only ISO strings parse as UTC, so `(Date.parse(b) - Date.parse(a)) / 86_400_000` is a whole number of days with no daylight-saving gaps. `div(other, 2, "HALF_UP")` divides and rounds in one call.
- Java: `ChronoUnit.DAYS.between(a, b)` counts days; `divide(termDays, 2, RoundingMode.HALF_UP)` divides and rounds in one call.
- Kotlin: `BigDecimal / BigDecimal` is `divide(other, RoundingMode.HALF_EVEN)` and keeps the dividend's scale, so it rounds half-even to the premium's own scale. Use `divide(termDays, 2, RoundingMode.HALF_UP)` (cases `h3` and `h4` catch the mistake).
- Go: dates are `time.Time` at midnight UTC, compared with `Before` and `After`. Count days as `(end.Unix() - start.Unix()) / 86400`, because `end.Sub(start)` is a `time.Duration`, which holds at most about 292 years. `DivRound(termDays, 2)` divides once and rounds half away from zero, which is `HALF_UP`. `Div` would round to 16 places first, and a later `Round(2)` would round a second time.
- Rust: `(term_end - change_date).num_days()` counts days between two `NaiveDate` values, as an `i64`. `/` on `Decimal` keeps 28 significant digits, so `round_dp_with_strategy(2, RoundingStrategy::MidpointAwayFromZero)` after it gives the exact `HALF_UP` result: the digits between the two roundings would have to be all 9s to change it, and a quotient by a day count never has that. `format!("{:.2}", x)` truncates and would fail the tie case.
