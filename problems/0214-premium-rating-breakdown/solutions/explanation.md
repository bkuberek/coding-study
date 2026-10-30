# Premium Rating Breakdown: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| table-lookup | optimal | O(c + log b) | O(c) | default answer |

`c` is the number of class codes and `b` the number of size bands.

## Approach: table-lookup (Index the class table and binary-search the size bands)

### Intuition

Rating is a pipeline of multiplications over two table lookups: a rate by class code and a factor by size band. If every intermediate amount is kept as it is produced, the explanation of the premium comes for free: it is the list of running amounts.

### Algorithm

1. Build a lookup from class code to base rate.
2. Binary-search the band bounds for the last bound `<= payroll`. If the code is unknown or no bound qualifies, return an empty list.
3. Compute the base premium: `payroll / 1000 * rate`. Record it.
4. Multiply by the band factor, then by `experienceMod`, then by `1 - scheduleCredit`, recording the running amount after each multiplication.
5. Take the larger of the last amount and `minimumPremium`, round it to cents half up, and record it as the fifth entry.

### Correctness

The binary search returns the last bound that is not greater than the payroll, which is the band the statement defines (a payroll exactly on a bound uses that bound's band). Every multiplication is by an exact decimal and the constraints keep each product within 28 significant digits, so the four unrounded entries have no error. Rounding happens once, on the final amount, after the minimum has been compared with the unrounded value.

### Complexity

- Time: O(c + log b) — building the class lookup is linear in c, and the band search is logarithmic in b; the rating itself is a fixed number of multiplications.
- Space: O(c) — the class lookup; the trail has a fixed five entries.

### Trade-offs

A linear scan of the class table needs no extra memory and is fine for at most 100 classes. The lookup pays off when one table rates many quotes, because it can be built once. A linear scan of the bands is also acceptable for 20 bands; the binary search is the shape that keeps working when a table has thousands of rows.

### Pitfalls and edge cases

- Floating point: `0.1`-style rates and factors do not add or multiply exactly in binary floats. Use the decimal type of the language.
- Rounding every step instead of once at the end changes the result (`h2`, `h12`).
- A payroll exactly on a band's lower bound belongs to that band (`h1`, `h3`). A lower-bound search (`bisect_left`) puts it in the band below.
- A negative schedule credit is a debit and raises the premium (`h5`).
- The minimum is compared with the amount after the credit, not with the base premium (`h6`), and an amount exactly equal to the minimum is fine (`h7`).
- Half-cent ties round up, not to even (`h4`: `2500.025` becomes `2500.03`).
- A payroll below the lowest band (`h8`) and an empty class table (`h10`) both return an empty list.
- Zero payroll with a zero minimum is a valid quote that rates to zero (`h9`).

### Language notes

- Python: `Decimal` arithmetic is exact within the default 28-digit context. `bisect_right(bounds, payroll) - 1` is the band index, and `quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)` rounds the final amount.
- TypeScript: `Decimal` from `#support` has `times`, `minus` and `round(2, "HALF_UP")`, and `payroll.movePointLeft(3)` divides by 1000 exactly, as in Java. There is no standard binary search, so the loop is written out with `cmp`.
- Java: use `compareTo`, never `equals`, which also compares the scale (`2.0` and `2.00` are not equal). `payroll.movePointLeft(3)` divides by 1000 exactly; `divide` without a scale throws for non-terminating results.
- Kotlin: `BigDecimal / BigDecimal` is `divide(other, RoundingMode.HALF_EVEN)` and keeps the dividend's scale, so `BigDecimal("999999") / BigDecimal(1000)` is `1000`, not `999.999`. Use `movePointLeft(3)` (case `h2` catches the mistake). `maxOf` works because `BigDecimal` is `Comparable`.
- Go: `sort.Search(len(bounds), func(i int) bool { return bounds[i].GreaterThan(payroll) })` is the upper bound, one past the last band that starts at or below the payroll. `payroll.Shift(-3)` moves the point exactly, and `Round(2)` rounds ties away from zero, which is Java's `HALF_UP`. Compare decimals with `GreaterThan` and the like, never `==`, which compares the representation.
- Rust: `partition_point(|bound| *bound <= payroll)` is the same upper bound. `Decimal` compares by value (`1.50 == 1.5`),. `payroll * Decimal::new(1, 3)` moves the point exactly, and `round_dp_with_strategy(2, RoundingStrategy::MidpointAwayFromZero)` is `HALF_UP`: `format!("{:.2}", x)` would truncate instead. The nine parameters of the fixed signature trip clippy's `too_many_arguments`, so the reference allows it.
