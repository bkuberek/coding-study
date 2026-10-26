# Coin Change Combinations

## Statement

A cash register holds coins of several distinct values, given in `coins`, and an unlimited supply of each. Count the different ways to pay exactly `amount` with these coins.

A way is a combination, not a sequence: it is described by how many coins of each value it uses, so paying 2 + 5 and paying 5 + 2 is the same way. Paying an amount of 0 has exactly one way, using no coins. If the amount cannot be paid, the answer is 0.

Reference: this is our own wording of LeetCode problem 518, [Coin Change II](https://leetcode.com/problems/coin-change-ii/).

## Input

- `amount`: the total to pay
- `coins`: the distinct coin values available

## Output

The number of combinations of coins whose values add up to `amount`.

## Examples

### Example 1

<!-- case: ex1 -->

Seven can be paid as 2 + 5 or as 2 + 2 + 3. Orders such as 5 + 2 or 3 + 2 + 2 are the same combinations and do not count again.

### Example 2

<!-- case: ex2 -->

Every sum of 2s is even, so 3 cannot be paid.

## Constraints

- `1 <= coins.length <= 300`
- `1 <= coins[i] <= 5000`, and all values are distinct
- `0 <= amount <= 2000`
- For every total from 0 to `amount`, the number of combinations fits in a signed 32-bit integer, so no counting order overflows.

## Follow-ups

- Counting sequences of coins is a different problem with a different answer. How do you make sure every combination is counted once?
- Can you count with a single array indexed by amount?
- How would the loops change to count ordered sequences instead?

## Hints

### Hint 1

Fix an order of the coin values. Every combination either uses no coin of the first value, or at least one.

### Hint 2

Let `W(i, a)` be the number of ways to pay `a` with the coins from index `i` on. Then `W(i, a) = W(i + 1, a) + W(i, a - coins[i])`, where the second term is used only when `a >= coins[i]`.

### Hint 3

With one array over the amounts, loop over the coins outside and over the amounts inside, increasing: `ways[a] += ways[a - coin]`.
