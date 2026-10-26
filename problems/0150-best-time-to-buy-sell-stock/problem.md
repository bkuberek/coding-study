# Best Time to Buy and Sell Stock

## Statement

`prices[i]` is the price of a stock on day `i`. You may buy one share on one day and sell it on a later day. Return the largest profit, selling price minus buying price, that a single such trade can make.

If every possible trade would lose money or break even, do not trade at all and return 0.

Reference: this is our own wording of LeetCode problem 121, [Best Time to Buy and Sell Stock](https://leetcode.com/problems/best-time-to-buy-and-sell-stock/).

## Input

- `prices`: the price on each day, in order

## Output

The maximum of `prices[j] - prices[i]` over all days `i < j`, or 0 if that maximum is negative or no such pair exists.

## Examples

### Example 1

<!-- case: ex1 -->

Buying at 1 on day 3 and selling at 5 on day 4 earns 4. Buying at 3 and selling at 6 earns only 3, and the buy must come before the sell, so buying at 1 and selling at 8 is not allowed.

### Example 2

<!-- case: ex2 -->

The price never rises from one day to any later day, so every trade loses or breaks even and the answer is 0.

## Constraints

- `1 <= prices.length <= 10^5`
- `0 <= prices[i] <= 10^4`

## Follow-ups

- Checking every pair of days takes O(n^2) time. For a fixed selling day, which buying day is best?
- Can you solve it in one pass with O(1) extra memory?
- How does this relate to finding the maximum-sum subarray of the day-to-day price changes?

## Hints

### Hint 1

Fix the day you sell. The best day to buy is the cheapest day before it.

### Hint 2

Walk through the days once, remembering the lowest price seen so far. Each day, compare today's price minus that minimum with the best profit so far.
