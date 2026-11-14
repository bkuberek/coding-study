# Minimum Size Subarray Sum

## Statement

You get a positive integer `target` and an array `nums` of positive integers. Find the shortest contiguous run of elements of `nums` whose sum is at least `target`, and return its length.

If no run reaches `target`, not even the whole array, return 0.

Reference: this is our own wording of LeetCode problem 209, [Minimum Size Subarray Sum](https://leetcode.com/problems/minimum-size-subarray-sum/).

## Input

- `target`: the sum a run must reach
- `nums`: the positive values, in order

## Output

The smallest length of a contiguous subarray with sum at least `target`, or 0 when none exists.

## Examples

### Example 1

<!-- case: ex1 -->

No single element reaches 10, but the neighbors 5 and 9 sum to 14, so two elements suffice. Other pairs such as 9 and 2 also work; the answer is the length, not the run.

### Example 2

<!-- case: ex2 -->

The whole array sums to 35, which is below 50, so no run can reach the target.

## Constraints

- `1 <= target <= 10^9`
- `1 <= nums.length <= 10^5`
- `1 <= nums[i] <= 10^4`

## Follow-ups

- Checking every start is quadratic. Can you find the answer in one linear pass?
- Prefix sums of positive values are strictly increasing. How can that give an O(n log n) solution?
- Which part of the linear solution breaks if `nums` may contain negative values?

## Hints

### Hint 1

For a fixed start, extend the run until its sum reaches `target`. Extending further only makes it longer.

### Hint 2

All values are positive, so removing an element from the left of a run always lowers its sum, and adding one on the right always raises it.

### Hint 3

Keep a window and its sum. Add elements on the right; whenever the sum reaches `target`, record the length and drop elements from the left while the sum still reaches it.
