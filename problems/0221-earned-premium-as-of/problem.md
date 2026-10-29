# Earned Premium As Of

## Statement

An insurer values its book of contractor policies at the start of `valuationDate`. A policy earns its premium evenly over the days of its term `[start, end)`: `start` is the first covered day and `end` is not covered.

A policy's earned premium is `premium * d / termDays`, where `termDays` is the number of days of the term and `d` is the number of term days before `valuationDate`: 0 when the valuation is on or before the start, all the term days once it is on or after the end. Round each policy's earned premium to cents, half up, for that policy alone, and return the total of the rounded amounts.

## Input

- `premiums`: `premiums[i]` is the premium of policy `i`
- `terms`: `terms[i] = [start, end]` is the term of policy `i`
- `valuationDate`: the day the book is valued; the day itself has not been earned yet

## Output

The book's earned premium as a decimal: a sum of amounts in cents. Decimals are compared by value, so `600.00` and `600` are the same answer.

## Examples

### Example 1

<!-- case: ex1 -->

The first policy has run 182 days of 365, so it earned 1200 * 182 / 365 = 598.35616..., which rounds to 598.36. The second has run 92 days of 365 and earned 3650 * 92 / 365 = 920. The book earned 1518.36.

### Example 2

<!-- case: ex2 -->

The book is valued before both terms start, so nothing is earned yet.

### Example 3

<!-- case: ex3 -->

Each policy is two days long and one day has been earned, so each earned half a cent, which rounds to 0.01. The total is 0.03; rounding the sum of the exact amounts (0.015) once would give 0.02.

## Constraints

- `0 <= premiums.length == terms.length <= 10^4`.
- `0 <= premiums[i] <= 10^7`, with at most 2 fractional digits.
- `start < end` for every term, and a term is at most 5 years long.
- Dates fall between `2000-01-01` and `2100-12-31`.

## Follow-ups

- The unearned premium reserve is written premium minus earned premium: how do the rounded amounts affect it?
- Earned premium per month for the whole book (see `loss-ratio-by-period`).
- A premium that changes during the term (see `endorsement-replay`).

## Hints

### Hint 1

Clamp the number of days before the valuation date into the range from 0 to the term's days.

### Hint 2

Round each policy, then add.
