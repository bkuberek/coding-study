# Pro-Rata Unearned Premium

## Statement

A contractor cancels a policy partway through its term. The premium for the whole term was `termPremium`. Return the part of it that belongs to the days that are no longer covered: the refund.

The term covers the days `[termStart, termEnd)`: `termStart` is covered and `termEnd` is not. The cancellation takes effect at the start of `changeDate`, so `changeDate` and every later day of the term are refunded. Count actual calendar days (a term that contains 29 February has 366 days when it spans a whole year), and spread the premium evenly over the days of the term. Compute `termPremium * refundedDays / termDays` and round once to cents, half up (a tie such as `0.505` goes to `0.51`).

If `changeDate` is before `termStart` or after `termEnd`, the change is outside the term: return `-1`.

## Input

- `termPremium`: the premium for the whole term
- `termStart`: the first covered day
- `termEnd`: the day the coverage ends (not covered)
- `changeDate`: the day the cancellation takes effect

Dates and decimals are shown as quoted strings in the examples, which is how the tests carry them.

## Output

The refund as a decimal, `>= 0`, rounded to cents, or `-1` when `changeDate` is outside `[termStart, termEnd]`. Decimals are compared by value, so `1200.00` and `1200` are the same answer.

## Examples

### Example 1

<!-- case: ex1 -->

The term has 365 days. Cancelling on 2026-07-02 leaves 183 days (2026-07-02 up to 2027-01-01), so the refund is 1200 * 183 / 365 = 601.6438..., which rounds to 601.64.

### Example 2

<!-- case: ex2 -->

Cancelling on the end date leaves no days of the term, so the refund is 0.

### Example 3

<!-- case: ex3 -->

Cancelling on the first day of the term refunds the whole premium.

## Constraints

- `0 <= termPremium <= 10^7`, with at most 2 fractional digits.
- `termStart < termEnd`, and the term is at most 5 years long.
- Dates fall between `2000-01-01` and `2100-12-31`.

## Follow-ups

- An endorsement changes the premium partway through the term: charge or return the pro-rated difference. It can be negative, so what should an error look like?
- A short-rate cancellation keeps a penalty percentage on top of the pro-rata share.
- A 365-day basis, where a leap year no longer changes the share of a day.

## Hints

### Hint 1

Let the date library count days. Do not count months.

### Hint 2

Multiply before you divide, and round only once, at the end.
