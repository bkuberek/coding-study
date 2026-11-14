# Installment Schedule

## Statement

A contractor pays a policy's premium in monthly installments. Split `premium` into `installmentCount` installments and give each one a due date.

Amounts are whole cents. Every installment gets the same base amount, and the cents left over go one each to the earliest installments, so the amounts add up exactly to the premium and never grow along the schedule.

The first installment is due on `firstDueDate`. Each later one is due one month after the previous one, on the same day of the month as `firstDueDate`, or on the last day of the month when that month is too short: an anchor of 31 January is due on 28 or 29 February, and then on 31 March.

Return one row `[dueDate, amount]` per installment, in order. With zero installments, return an empty list.

## Input

- `premium`: the premium to split
- `installmentCount`: the number of installments
- `firstDueDate`: the due date of the first installment, which also fixes the day of the month of the others

## Output

Rows `[dueDate, amount]`: the date as `YYYY-MM-DD` text, and the amount as text with exactly two digits after the point and no sign or separators (`"1200.00"`, `"0.07"`).

## Examples

### Example 1

<!-- case: ex1 -->

1000 is 100000 cents. Three installments get 33333 cents each, and one cent is left over, which goes to the first installment: 333.34, 333.33, 333.33. The due date is the 15th every month.

### Example 2

<!-- case: ex2 -->

The anchor is 31 January. February has no 31st, so that installment falls on 28 February; March has a 31st again, so the third is due on 31 March, and April's is due on 30 April. 1200 splits evenly, with no leftover cent.

### Example 3

<!-- case: ex3 -->

The anchor is 30 November 2027, and the fourth installment lands in the leap year 2028, so it is due on 29 February. 100 is 10000 cents over 6 installments: 1666 each and 4 cents left over, so the first four get 16.67 and the last two get 16.66.

## Constraints

- `0 <= premium <= 10^9`, with at most 2 fractional digits.
- `0 <= installmentCount <= 120`.
- `firstDueDate` falls between `2000-01-01` and `2089-12-31`, so every due date stays before 2100.

## Follow-ups

- Put the leftover cents on the last installment instead (a true-up). Which convention does a billing team prefer, and why?
- Quarterly schedules: every `k` months instead of every month.
- A down payment of a percentage of the premium, then equal installments for the rest.
- Move a due date that falls on a weekend to the next business day.

## Hints

### Hint 1

Convert the premium to whole cents first; integer division and the remainder do the rest.

### Hint 2

Compute each due date from the first one (add `k` months), not from the previous due date.

### Hint 3

The last day of a month is the day before the first day of the next month.
