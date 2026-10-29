# Installment Schedule: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| cent-split | optimal | O(n) | O(n) | default answer |

## Approach: cent-split (Split the premium in whole cents and clamp each due date from the anchor day)

### Intuition

Money only splits exactly in whole cents, so split the cents and hand out the remainder by a fixed rule. Due dates are month arithmetic with clamping, always relative to a fixed anchor, so a short month never moves the later due dates.

### Algorithm

1. If `installmentCount` is 0, return an empty list.
2. Convert the premium to cents and compute `base, leftover = divmod(cents, installmentCount)`.
3. For each installment `k` from 0: the amount is `base + 1` while `k < leftover`, else `base`. The due date is `firstDueDate` plus `k` months, with the day clamped to the length of the target month.
4. Format the date as ISO text and the amount as dollars and two-digit cents, and append the row.

### Correctness

`n * base + leftover = cents` with `0 <= leftover < n`, so giving one extra cent to exactly the first `leftover` installments makes the amounts add up to the premium, differ by at most one cent, and never increase along the schedule. The month index `month - 1 + k` gives the right year and month, and `min(anchorDay, monthLength)` is a real day of that month that equals the anchor day whenever the month has it.

### Complexity

- Time: O(n) — constant work per installment.
- Space: O(n) — the output rows.

### Trade-offs

Rounding `premium / n` for every installment breaks the total: 1000 in three gives three times 333.33, which is 999.99. Putting the leftover cents on the last installment is the other common convention (a true-up); this problem uses the first installments so the schedule never increases. Chaining due dates, each one month after the previous, is simpler but drifts after a short month: 31 January, 28 February, then 28 March instead of 31 March.

### Pitfalls and edge cases

- Floating point cannot hold the premium or its shares; use the decimal type, or integer cents.
- Rounding each share separately instead of splitting the cents.
- Chaining months instead of counting from the anchor (`h6`).
- The 29th, 30th and 31st in short months, and 29 February in leap and common years (`ex3`, `h5`, `h10`).
- A schedule that crosses a year boundary (`h8`).
- Zero installments return an empty list (`h3`).
- Fewer cents than installments: the last installments get `0.00` (`h1`, `h11`).
- A zero premium (`h4`) and the largest premium (`h7`).

### Language notes

- Python: there is no month arithmetic in the standard library, so compute the target year and month from a month index and clamp the day with `calendar.monthrange`. `int(premium * 100)` is exact because the premium has at most two fractional digits, and `divmod` gives the base and the leftover. Format with an f-string: `f"{amount // 100}.{amount % 100:02d}"`.
- TypeScript: `premium.movePointRight(2).unscaled` is the cents as a `bigint`, divided with `/` and `%` on `BigInt`s. `new Decimal(amountCents, 2).toString()` keeps scale 2 (`"333.34"`, `"0.00"`). Month arithmetic uses `Date.UTC`, but `Date.UTC(2026, 1, 31)` rolls over into 3 March, so clamp the day with the month length first.
- Java: `premium.movePointRight(2).longValueExact()` gives the cents; `BigDecimal.valueOf(amountCents, 2).toPlainString()` prints two digits. `firstDueDate.plusMonths(k)` clamps to the last day of the month and counts from the anchor; never call `plusMonths(1)` in a loop on the previous due date.
- Kotlin: the same `java.time` calls (`plusMonths(k.toLong())`) and `BigDecimal.valueOf(cents, 2).toPlainString()`. Build the rows with `Array(n) { k -> arrayOf(dueText, amountText) }`, which is `Array<Array<String>>`.
