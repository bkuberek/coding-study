# Coin Change

## Statement

A cashier has an unlimited supply of coins of each value listed in `coins` and must pay out exactly `amount`. Return the smallest number of coins whose values add up to `amount`. If no combination of the available values reaches `amount` exactly, return `-1`.

Paying an amount of 0 needs no coins at all.

Reference: this is our own wording of LeetCode problem 322, [Coin Change](https://leetcode.com/problems/coin-change/).

## Input

- `coins`: the distinct coin values, in no particular order; each value can be used any number of times
- `amount`: the exact total to pay

## Output

The minimum number of coins that sum to `amount`, or `-1` when `amount` cannot be formed.

## Examples

### Example 1

<!-- case: ex1 -->

Two coins of 3 make 6. Grabbing the largest coin first (4, then 1 and 1) also makes 6 but uses three coins, so the greedy choice is not optimal here.

### Example 2

<!-- case: ex2 -->

Every sum of 4s and 6s is even, so the odd amount 9 cannot be paid.

### Example 3

<!-- case: ex3 -->

An amount of 0 is paid with zero coins, whatever the coin values are.

## Constraints

- `1 <= coins.length <= 12`
- `1 <= coins[i] <= 2^31 - 1`, and the values are distinct
- `0 <= amount <= 2000`

## Follow-ups

- Why does "always take the largest coin that fits" fail, and for which coin systems does it happen to work?
- Can you view the remainders as nodes of a graph and find the answer as a shortest path?
- How would you count the number of different combinations that pay `amount` instead of the fewest coins?

## Hints

### Hint 1

The last coin paid has some value `c`. Whatever it is, the coins before it pay exactly `amount - c`, and they should do so with as few coins as possible.

### Hint 2

Let `fewest(x)` be the answer for amount `x`. Then `fewest(x) = 1 + min(fewest(x - c))` over the coin values `c <= x`, with `fewest(0) = 0`. Mark amounts that cannot be formed so they never win the minimum.

### Hint 3

Fill `fewest` for `x = 0, 1, ..., amount` in increasing order, so every value it reads is already known.
