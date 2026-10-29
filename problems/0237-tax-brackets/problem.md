# Tax Owed Under Brackets

## Statement

Income is taxed in brackets. `brackets[i] = [limit, percent]`, sorted by strictly increasing `limit`. The first bracket taxes the income from 0 up to `limit_0` at `percent_0` percent. Bracket `i` taxes the income between `limit_(i-1)` and `limit_i` at `percent_i` percent. Every bracket taxes only the part of the income that falls inside it.

Return the total tax on `income`. The income never exceeds the last limit.

The result is exact: the income is a whole number of units and every rate is a whole percent, so the tax is a whole number of hundredths. It has at most two decimal places and no rounding happens.

Reference: this is our own wording of LeetCode problem 2303, [Calculate Amount Paid in Taxes](https://leetcode.com/problems/calculate-amount-paid-in-taxes/).

## Input

- `brackets`: `[limit, percent]` pairs in increasing order of limit
- `income`: the income in whole units

## Output

The tax as an exact decimal, for example `3.1`, which is the same value as `3.10`. Only the value is compared, not the scale.

## Examples

### Example 1

<!-- case: ex1 -->

The first 4 units are taxed at 10% (0.4), the next 6 units at 20% (1.2) and the last 5 units at 30% (1.5), which makes 3.1 in total.

### Example 2

<!-- case: ex2 -->

All 3 units fall in the first bracket, which is taxed at 0%, so the tax is 0. The second bracket is never reached.

## Constraints

- `1 <= brackets.length <= 10^5`
- `brackets[i].length == 2`
- `1 <= brackets[0][0] < brackets[1][0] < ... <= 10^6`
- `0 <= brackets[i][1] <= 100`
- `0 <= income <= brackets[brackets.length - 1][0]`

## Follow-ups

- If rates could be fractional percents such as 12.5%, what scale would the result need, and where would you round?
- If you had to tax many incomes against the same brackets, what would you precompute? Think of prefix sums of the taxes of full brackets, plus a binary search.

## Hints

### Hint 1

Each bracket taxes a slice of the income: from the previous limit up to the smaller of its own limit and the income.

### Hint 2

Stop as soon as the previous limit reaches the income.

### Hint 3

Add `slice * percent` as an integer count of hundredths and convert it to a decimal once, at the end. That is exact and needs no rounding.
