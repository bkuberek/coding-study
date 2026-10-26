# Stock Trading With Cooldown

## Statement

`prices[i]` is the price of one share of a stock on day `i`. You may trade as often as you like under three rules:

- You hold at most one share at a time, so you must sell the share you own before buying again.
- Each day you may buy, sell, or do nothing, but not more than one of these.
- The day after you sell, you are in a cooldown and may not buy.

Return the largest total profit (money from sales minus money spent on purchases) you can end with. Doing nothing at all is allowed and earns 0, and a share still held at the end earns nothing.

Reference: this is our own wording of LeetCode problem 309, [Best Time to Buy and Sell Stock with Cooldown](https://leetcode.com/problems/best-time-to-buy-and-sell-stock-with-cooldown/).

## Input

- `prices`: the share price on each day, in order

## Output

The maximum total profit achievable under the rules.

## Examples

### Example 1

<!-- case: ex1 -->

Without the cooldown you would buy at 1, sell at 4, buy at 2 and sell at 7, for 3 + 5 = 8. Here buying at 2 on day 2 is forbidden, because day 2 follows the sale on day 1. The best plan is a single trade: buy at 1 and sell at 7, for a profit of 6.

### Example 2

<!-- case: ex2 -->

Buy at 2 and sell at 5 (+3), sit out day 2 as the cooldown, then buy at 1 on day 3 and sell at 6 on day 4 (+5): 8 in total.

### Example 3

<!-- case: ex3 -->

Prices only fall, so every purchase would lose money. The best plan is to never trade.

## Constraints

- `1 <= prices.length <= 2000`
- `0 <= prices[i] <= 1000`

## Follow-ups

- Without the cooldown, adding up every rise between consecutive days gives the answer. Why does the cooldown break that greedy rule?
- Describe the problem as a small state machine: which states can you be in at the end of a day, and which moves connect them?
- How would the solution change if every sale also paid a fixed fee?

## Hints

### Hint 1

At the end of each day you are in one of three situations: holding a share, having just sold today, or resting without a share (and free to buy tomorrow).

### Hint 2

Write the best profit for each situation on day `i` in terms of the three values for day `i - 1`. For example, "holding" comes from holding yesterday, or from resting yesterday and buying today.

### Hint 3

Each day only needs the previous day's three values, so three variables are enough.
