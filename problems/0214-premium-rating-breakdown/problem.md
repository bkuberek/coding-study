# Premium Rating Breakdown

## Statement

An underwriter quotes a construction policy and wants two things: the premium, and a trail that shows how that premium was reached. The quote is rated in five steps, always in this order:

1. **Base premium.** `payroll / 1000 * baseRate`, where `baseRate` is the rate listed for `classCode` (a rate per 1,000 of payroll).
2. **Size factor.** Find the size band whose lower bound is the largest bound that is still `<= payroll`. A payroll exactly on a bound belongs to that bound's band. Multiply the running amount by the band's factor.
3. **Experience modifier.** Multiply the running amount by `experienceMod`.
4. **Schedule credit.** Multiply the running amount by `1 - scheduleCredit`. A negative credit is a debit and raises the premium.
5. **Minimum and rounding.** If the amount after step 4 is below `minimumPremium`, use `minimumPremium` instead. Then round to cents, half up (a tie such as `2500.025` goes to `2500.03`). This is the only rounding.

Return the trail `[base, afterSize, afterExperience, afterSchedule, final]`. The first four entries are the exact running amounts, never rounded. The last entry is the rounded premium.

If `classCode` is not in the class table, or `payroll` is below the lowest band's bound, the quote cannot be rated: return an empty list.

## Input

The rating tables are passed in as parallel arrays, because the data belongs to the caller and not to the code.

- `classCode`: the class of work being quoted
- `payroll`: the estimated annual payroll
- `experienceMod`: the experience modifier
- `scheduleCredit`: the schedule credit (or debit, when negative) as a fraction of the premium
- `classCodes`, `baseRates`: `baseRates[i]` is the rate per 1,000 of payroll for `classCodes[i]`
- `bandLowerBounds`, `bandFactors`: `bandFactors[i]` applies to payrolls from `bandLowerBounds[i]` up to (not including) `bandLowerBounds[i + 1]`; the last band has no upper limit
- `minimumPremium`: the smallest premium the policy can be sold for

Decimals are exact base-10 numbers. In the examples below they are shown as quoted strings, which is how the tests carry them.

## Output

A list of five decimals `[base, afterSize, afterExperience, afterSchedule, final]`, or an empty list when the quote cannot be rated. Amounts are compared by value, so `19237.50` and `19237.5` are the same answer.

## Examples

### Example 1

<!-- case: ex1 -->

A payroll of 2,000,000 at 12.50 per 1,000 gives a base premium of 25,000. The payroll falls in the band that starts at 1,000,000, whose factor 0.95 brings it to 23,750. The experience modifier 0.90 gives 21,375, and a 10% credit leaves 90% of that, 19,237.50. The minimum of 2,500 does not apply.

### Example 2

<!-- case: ex2 -->

The base premium is 1,250 and none of the later factors change it. That is below the 2,500 minimum, so the final entry is 2,500 while the first four entries still show the real rating.

### Example 3

<!-- case: ex3 -->

Class `9999` is not in the class table, so there is nothing to rate and the result is empty.

## Constraints

- `0 <= classCodes.length == baseRates.length <= 100`; the codes are distinct and 1 to 8 characters long.
- `0 < baseRates[i] < 1000`, with at most 2 fractional digits.
- `1 <= bandLowerBounds.length == bandFactors.length <= 20`; the bounds are strictly ascending, `>= 0`, with at most 2 fractional digits.
- `0 < bandFactors[i] < 10`, with at most 3 fractional digits.
- `0 <= payroll <= 10^9`, with at most 2 fractional digits.
- `0.5 <= experienceMod <= 2`, with at most 3 fractional digits.
- `-0.25 <= scheduleCredit <= 0.25`, with at most 3 fractional digits.
- `0 <= minimumPremium <= 10^6`, with at most 2 fractional digits.
- These bounds keep every intermediate product within 28 significant digits, so the first four entries are exact.

## Follow-ups

- What changes if every step is rounded to cents instead of only the last? Which of the five entries move, and by how much?
- Return labelled steps (name and amount) for an audit log instead of five positions.
- Load the tables from versioned storage, so an old quote can be rated again with the tables that were in force then (see `versioned-rate-table`).

## Hints

### Hint 1

Turn the class table into a lookup before you rate anything.

### Hint 2

The size band is the last lower bound that is `<= payroll`. That is an upper-bound binary search, minus one.

### Hint 3

Keep full precision until the very last step, and round only the final amount.
