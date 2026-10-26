# Two Sum on Sorted Input

## Statement

You get an integer array `numbers`, already sorted in non-decreasing order, and an integer `target`. Exactly one pair of different positions holds two values that add up to `target`. Return those two positions, smaller first.

Positions are 0-based. Two positions may hold equal values; they still count as different positions. Aim for a solution that uses only a constant amount of extra memory.

Reference: this is our own wording of LeetCode problem 167, [Two Sum II - Input Array Is Sorted](https://leetcode.com/problems/two-sum-ii-input-array-is-sorted/).

## Input

- `numbers`: the values, sorted from smallest to largest
- `target`: the sum that exactly one pair of positions reaches

## Output

An array `[i, j]` with `i < j` and `numbers[i] + numbers[j] == target`.

## Examples

### Example 1

<!-- case: ex1 -->

The values at positions 2 and 3 are 3 and 5, and 3 + 5 = 8. The only other way to reach 8 would need -1 or 7, which do not appear.

### Example 2

<!-- case: ex2 -->

The two 2s sit at different positions, so they form a valid pair. The answer lists the smaller position first.

## Constraints

- `2 <= numbers.length <= 10^5`
- `-10^9 <= numbers[i] <= 10^9`
- `numbers[i] <= numbers[i + 1]` for every valid `i`
- `-10^9 <= target <= 10^9`
- Exactly one pair of different positions adds up to `target`.

## Follow-ups

- A hash map solves the unsorted version in O(n) time and O(n) memory. Can you use the order to get O(n) time with O(1) memory?
- For each element, a binary search can find its partner. How does that compare with a single linear pass?
- How would you count all pairs with a sum at most `target`?

## Hints

### Hint 1

Look at the smallest and the largest value. If their sum is too small, which of the two can never be part of the answer?

### Hint 2

If the sum of the outer pair is too large, the largest value is too large for every partner. Discard it.

### Hint 3

Keep one index at each end and move exactly one of them inward per step, depending on whether the current sum is below or above the target.
