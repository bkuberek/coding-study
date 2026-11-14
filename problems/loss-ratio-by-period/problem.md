# Loss Ratio by Period

## Statement

An underwriter compares a contractor program's incurred losses with its earned premium, period by period.

Divide the calendar into periods of `periodMonths` months aligned to January: with 3, the periods are the quarters January to March, April to June, and so on. Earned premium arrives as dated postings, and losses as dated incurred amounts.

For every period from the one that contains `fromDate` through the one that contains `toDate`, add up the earned premium and the losses dated in that period, and report losses / earned premium, rounded to 4 decimal places, half up. Whole periods count: an entry in the first or last period counts even when it falls before `fromDate` or after `toDate`. Entries in other periods are ignored.

A period whose earned premium totals zero reports `-1`.

## Input

- `earnedDates`, `earnedAmounts`: `earnedAmounts[i]` of earned premium was posted on `earnedDates[i]`
- `lossDates`, `lossAmounts`: `lossAmounts[i]` of losses was incurred on `lossDates[i]`
- `fromDate`, `toDate`: the first and the last day of the range; both mark a whole period
- `periodMonths`: the length of a period in months

## Output

One ratio per period, as a list of decimals, in calendar order, including periods with no entries. Decimals are compared by value, so `0.5000` and `0.5` are the same answer.

## Examples

### Example 1

<!-- case: ex1 -->

The range starts in mid-January but covers the whole first quarter. Quarter one earned 3000 and incurred 1200 of losses: 1200 / 3000 = 0.4. Quarter two earned 3000 and incurred 600 + 900 = 1500: 0.5.

### Example 2

<!-- case: ex2 -->

The periods are months. January has premium and no losses, so its ratio is 0. February has a loss and no premium, so it reports -1. March earned 700 and incurred 350: 0.5.

### Example 3

<!-- case: ex3 -->

The periods are calendar years. In 2025 the premium is 3000 and the losses are 2000: 0.6666..., which rounds to 0.6667. In 2026 the premium is 900 and the losses are 1200.50: 1.33388..., which rounds to 1.3339.

## Constraints

- `0 <= earnedDates.length == earnedAmounts.length <= 1000`, and the same for the losses.
- `0 <= amounts <= 10^6`, with at most 2 fractional digits.
- `periodMonths` is one of 1, 2, 3, 4, 6 or 12.
- `fromDate <= toDate`, and the range spans at most 120 periods.
- Dates fall between `2000-01-01` and `2100-12-31`.

## Follow-ups

- Derive the earned premium from policies instead of postings: allocate each policy by days (see `earned-premium-as-of`).
- A rolling twelve-month ratio.
- Periods aligned to a fiscal year that starts in April.

## Hints

### Hint 1

Turn a date into a period number with integer arithmetic on its year and month.

### Hint 2

Keep two arrays of totals, one slot per reported period.
