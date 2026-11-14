# Minimum Cost for Tickets

## Statement

You have planned your train trips for the coming year: `days` lists the days of the year (numbered 1 to 365) on which you will travel. The railway sells three kinds of passes:

- a 1-day pass for `costs[0]`,
- a 7-day pass for `costs[1]`,
- a 30-day pass for `costs[2]`.

A pass bought for day `d` covers `d` and the days right after it: a 7-day pass bought for day 10 covers days 10 through 16. Passes may extend past day 365, and you may buy as many as you like. Return the smallest total amount that covers every travel day.

Reference: this is our own wording of LeetCode problem 983, [Minimum Cost For Tickets](https://leetcode.com/problems/minimum-cost-for-tickets/).

## Input

- `days`: the travel days, strictly increasing, each between 1 and 365
- `costs`: the prices of the 1-day, 7-day and 30-day passes, in that order

## Output

The minimum total price of a set of passes that covers every day in `days`.

## Examples

### Example 1

<!-- case: ex1 -->

A 7-day pass bought for day 2 covers days 2 to 8, which includes four trips, for 15. Day 30 still needs a 1-day pass for 4, so the total is 19. Buying 1-day passes only would cost 5 * 4 = 20.

### Example 2

<!-- case: ex2 -->

Travel happens on every day from 1 to 30, and a single 30-day pass for 25 covers all of it.

## Constraints

- `1 <= days.length <= 365`
- `1 <= days[i] <= 365`, and `days` is strictly increasing
- `costs.length == 3`
- `1 <= costs[i] <= 1000`

## Follow-ups

- Why can a longer pass be cheaper than a shorter one in some inputs, and does your solution handle it without special cases?
- Can you work with the travel days only, instead of all 365 calendar days?
- How would the solution change if the calendar had 10^9 days?

## Hints

### Hint 1

Think about the first travel day that is not yet covered. Some pass must be bought for that day, and there are only three choices.

### Hint 2

Let `cost(d)` be the cheapest way to cover every travel day up to calendar day `d`. If you do not travel on day `d`, it equals `cost(d - 1)`. Otherwise, the pass covering day `d` was a 1-day, 7-day or 30-day pass ending on or after `d`.

### Hint 3

When you travel on day `d`, `cost(d) = min(cost(d - 1) + costs[0], cost(d - 7) + costs[1], cost(d - 30) + costs[2])`, treating negative days as 0.
