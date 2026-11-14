# Target Sum

## Statement

You get an array of non-negative integers `nums` and an integer `target`. Put a sign, `+` or `-`, in front of every number and add them all up. Count how many of the `2^n` sign assignments produce exactly `target`.

Two assignments are different if some position gets a different sign, even when the numbers there are equal; in particular `+0` and `-0` count as two assignments.

Reference: this is our own wording of LeetCode problem 494, [Target Sum](https://leetcode.com/problems/target-sum/).

## Input

- `nums`: the numbers to sign, in order
- `target`: the required signed total

## Output

The number of sign assignments whose total equals `target`.

## Examples

### Example 1

<!-- case: ex1 -->

`+2 + 1 - 1` and `+2 - 1 + 1` both give 2. The two ones are at different positions, so these are different assignments. No assignment with `-2` reaches 2.

### Example 2

<!-- case: ex2 -->

The four possible totals are 7, 1, -1 and -7. None of them is 2.

## Constraints

- `1 <= nums.length <= 20`
- `0 <= nums[i] <= 1000`
- `sum(nums) <= 1000`
- `-1000 <= target <= 1000`

## Follow-ups

- Trying all `2^n` assignments works for 20 numbers. What if there were 200 numbers with the same small total?
- Different prefixes often reach the same running total. How can you exploit that?
- If `P` is the sum of the numbers with a plus sign, what does `target` tell you about `P`?

## Hints

### Hint 1

The future of a partial assignment depends only on the next index and the running total so far, not on which signs produced that total.

### Hint 2

Count, for every prefix length and every possible running total between `-sum` and `sum`, how many assignments reach it.

### Hint 3

With `P` the plus part and `N` the minus part, `P + N = sum` and `P - N = target`, so `P = (sum + target) / 2`. Count the subsets that add up to `P`, a classic one-dimensional knapsack.
