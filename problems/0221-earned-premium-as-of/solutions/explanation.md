# Earned Premium As Of: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| per-policy-proration | optimal | O(n) | O(1) | default answer |

## Approach: per-policy-proration (Prorate each policy by the days earned and round it before summing)

### Intuition

A policy earns one equal share of its premium per day of its term, and the book is the sum of its policies, each posted in cents the way a ledger posts it.

### Algorithm

1. Start with a total of 0.
2. For each policy, compute the term days and the earned days: the days from the start to the valuation date, clamped into the range from 0 to the term days.
3. Compute `premium * earnedDays / termDays`, round it to cents, half up, and add it to the total.
4. Return the total.

### Correctness

The clamp covers the three cases: before the term nothing is earned, inside the term the days before the valuation date are earned, and after the term every day is. The term is half-open, so the daily shares add up to the whole premium. Rounding each policy on its own is the defined answer, and adding rounded amounts is exact.

### Complexity

- Time: O(n) — constant work per policy.
- Space: O(1) — a running total.

### Trade-offs

Rounding once on the total gives a different number (`ex3`) and cannot be posted per policy. Looping over the days of each term would be O(days) per policy for the same result.

### Pitfalls and edge cases

- Counting the valuation day as earned is off by one.
- Negative days before the start of the term (`ex2`) and more days than the term after its end (`h3`).
- Leap years change the term days (`h4`, `h5`).
- Half-cent ties round up, not to even (`ex3`, `h9`).
- An empty book returns 0 (`h1`).
- One-day terms (`h7`) and a valuation exactly on a start or an end (`h2`).
- Floating point cannot hold these shares exactly.
- Kotlin's `/` on `BigDecimal`.

### Language notes

- Python: `(valuation_date - start).days` counts days, `min(max(days, 0), term_days)` clamps, and `quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)` rounds each policy.
- TypeScript: a date is an `IsoDate`, a plain ISO string. Date-only ISO strings parse as UTC, so `(Date.parse(b) - Date.parse(a)) / 86_400_000` is a whole number of days with no daylight-saving gaps. `premium.times(earned).div(termDays, 2, "HALF_UP")` divides and rounds in one call, and `plus` accumulates.
- Java: `ChronoUnit.DAYS.between(a, b)` counts days and `Math.min(Math.max(...), termDays)` clamps. `multiply(...).divide(BigDecimal.valueOf(termDays), 2, RoundingMode.HALF_UP)` divides and rounds in one call.
- Kotlin: the same calls, with `coerceIn(0, termDays)` for the clamp. A plain `/` would keep the premium's scale and round half-even: 101.00 / 200 would give 0.50 instead of 0.51 (`h9`).
- Go: count days as `(end.Unix() - start.Unix()) / 86400`, because `end.Sub(start)` is a `time.Duration`, which holds at most about 292 years. The built-in `min` and `max` (Go 1.21 and newer) clamp the earned days. `DivRound(termDays, 2)` divides once and rounds half away from zero, which is `HALF_UP`; `Div` would round to 16 places first and the cents rounding would be a second rounding (case `h9`).
- Rust: `(valuation_date - term[0]).num_days()` is an `i64`, and `Ord::clamp(0, term_days)` bounds it (it panics only if the bounds are reversed, and `start < end`). `/` on `Decimal` keeps 28 significant digits, so `round_dp_with_strategy(2, RoundingStrategy::MidpointAwayFromZero)` after it is the exact `HALF_UP` result; round each policy before adding it to the total.
