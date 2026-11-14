# Tax Owed Under Brackets: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| unit-by-unit | brute | O(n + income) | O(1) | the income is tiny, or as a correctness oracle |
| bracket-slices | optimal | O(n) | O(1) | default answer |

Here `n` is the number of brackets. The generator keeps the income below 10n, so both approaches are linear on the ladder, but the unit-by-unit walk is the slower one: it does about 5.5 steps per bracket.

## Approach: unit-by-unit (Tax each unit of income at its bracket's rate)

### Intuition

The definition made executable: unit number `u` of income (from `u` to `u + 1`) is taxed at the rate of the first bracket whose limit is above `u`. Walk the units one by one with a bracket pointer that only ever moves forward.

### Algorithm

1. Set `cents = 0` and the bracket pointer to the first bracket.
2. For each unit `u` from 0 to `income - 1`, move the pointer forward while the bracket's limit is at most `u`.
3. Add that bracket's percent to `cents`: one unit at `p` percent is `p` hundredths.
4. Return `cents` as a decimal with two decimal places.

### Correctness

The pointer invariant is that the limit of the current bracket is above `u` and the limit of the previous bracket is at most `u`, which picks exactly the bracket that contains the unit. Each unit contributes its bracket's percent in hundredths, so the sum is the total tax in hundredths, an integer, and converting it to a decimal with scale 2 is exact.

### Complexity

- Time: O(n + income) — the pointer moves at most `n` times and the walk visits `income` units.
- Space: O(1) — two counters.

### Trade-offs

Obviously correct, and the cost grows with the income instead of the bracket count, which makes it a poor idea for large incomes. It is useful as an oracle because it shares no arithmetic with the sliced version.

### Pitfalls and edge cases

- A unit equal to a limit belongs to the next bracket: unit `u` is in the bracket whose limit is *above* `u`.
- An income of 0 walks no units and returns 0.

### Language notes

- Sum the hundredths in an `int` (at most 10^6 * 100 = 10^8) and build the decimal once at the end. Never divide by 100 in floating point.
- Python: `Decimal(cents).scaleb(-2)`.
- TypeScript: `new Decimal(BigInt(cents), 2)` from `#support`, the `(unscaled, scale)` constructor.
- Java: `BigDecimal.valueOf(cents, 2)`. Kotlin: `BigDecimal.valueOf(cents.toLong(), 2)`.
- Go: `decimal.New(int64(cents), -2)`, where the second argument is an exponent, the negated scale. The sum is at most 10^8, which fits an `int` on any platform.
- Rust: `Decimal::new(cents, 2)` from an `i64` count of hundredths. The brackets are `i32`, and a slice times a rate is at most 10^8, so the product fits; the running total is an `i64` anyway.
- The runner prints decimals canonically, so the scale-2 result `3.10` passes as `3.1`.

## Approach: bracket-slices (Tax each bracket's slice of the income at once)

### Intuition

Each bracket taxes one slice of the income: from the previous limit up to the smaller of its own limit and the income. Multiply the slice length by the rate and add up.

### Algorithm

1. Set `cents = 0` and `lower = 0`.
2. For each bracket `[upper, percent]`: stop if `lower >= income`.
3. Add `(min(upper, income) - lower) * percent` to `cents` and set `lower = upper`.
4. Return `cents` as a decimal with two decimal places.

### Correctness

The slices `[lower, min(upper, income))` partition the interval `[0, income)` by bracket, and the slice of a bracket is taxed at exactly its percent. Stopping once `lower >= income` skips brackets that would contribute an empty or negative slice. The sum is the total tax in hundredths.

### Complexity

- Time: O(n) — one pass over the brackets, stopping early when the income is exhausted.
- Space: O(1) — two counters.

### Trade-offs

The answer to give. It never touches individual units, so the income can be as large as the last limit at no extra cost.

### Pitfalls and edge cases

- Forgetting the `min` with `income` taxes the whole last bracket.
- Forgetting to stop adds negative slices once `lower` passes `income`.
- Binary floating point gives `3.0999999999999996` for example 1, so keep integer hundredths until the end.

### Language notes

- Use the same conversions as above: `Decimal(cents).scaleb(-2)` in Python, `new Decimal(BigInt(cents), 2)` in TypeScript, `BigDecimal.valueOf(cents, 2)` in Java and `BigDecimal.valueOf(cents.toLong(), 2)` in Kotlin.
- Java imports `java.math.BigDecimal`, Kotlin imports the same class, and TypeScript imports `Decimal` from `#support`.
- Go builds the result with `decimal.New(int64(cents), -2)` and uses the built-in `min` (Go 1.21 and newer) for the end of the slice. Rust builds it with `Decimal::new(cents, 2)`, and `bracket[0].min(income)` is `Ord::min` on `i32`.
- Never build a decimal from a `double`.
