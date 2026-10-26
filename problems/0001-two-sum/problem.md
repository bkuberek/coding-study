# Two Sum

## Statement

You get an integer array `nums` and an integer `target`. Exactly two positions in `nums` hold values that add up to `target`. Find those two positions and return them.

A position can be used only once: you cannot pair an element with itself, even when doubling its value would reach `target`. Two different positions may hold the same value, and such a pair is valid.

Reference: this is our own wording of LeetCode problem 1, [Two Sum](https://leetcode.com/problems/two-sum/).

## Input

- `nums`: the integers to search, in the order given
- `target`: the sum that exactly one pair of positions must reach

## Output

An array of two distinct indices `i` and `j` with `nums[i] + nums[j] == target`. The two indices may come in either order: `[i, j]` and `[j, i]` are both accepted.

## Examples

### Example 1

<!-- case: ex1 -->

The values at positions 1 and 2 are 9 and 2, and 9 + 2 = 11. No other pair reaches 11: for instance, 4 + 8 = 12.

### Example 2

<!-- case: ex2 -->

Equal values at different positions form a valid pair: 5 + 5 = 10 uses positions 0 and 1.

## Constraints

- `2 <= nums.length <= 10^5`
- `-10^9 <= nums[i] <= 10^9`
- `-10^9 <= target <= 10^9`
- Exactly one pair of distinct positions adds up to `target`.

## Follow-ups

- Checking every pair is quadratic. Can you find the answer in a single pass over the array?
- If `nums` were sorted, could you solve it with O(1) extra space? What would you have to give up to return the original positions?
- How would you report every pair that reaches `target` when several exist?

## Hints

### Hint 1

Fix one element. Which single value would complete the sum with it?

### Hint 2

Scanning the rest of the array for that value repeats work. What structure answers "have I seen this value, and where?" in constant time?

### Hint 3

Walk the array once. Before storing the current value, look up the value that would pair with it among the ones already stored.
