# Maximum Subarray

## Statement

You get an integer array `nums`. A subarray is a non-empty run of consecutive elements. Return the largest sum that any subarray has.

The array may contain negative numbers, and the answer may be negative when every element is.

Reference: this is our own wording of LeetCode problem 53, [Maximum Subarray](https://leetcode.com/problems/maximum-subarray/).

## Input

- `nums`: the values, in order

## Output

The maximum sum over all non-empty subarrays of `nums`.

## Examples

### Example 1

<!-- case: ex1 -->

The run 5, -1, 2 sums to 6. Adding the 3 and -4 in front of it would lower the total, and so would extending it to the right.

### Example 2

<!-- case: ex2 -->

Every value is negative, so the best subarray is the single largest value, -1. The empty subarray is not allowed.

## Constraints

- `1 <= nums.length <= 10^5`
- `-10^4 <= nums[i] <= 10^4`

## Follow-ups

- Checking every subarray is O(n^2). When is a running sum not worth keeping?
- Can you solve it in one pass with O(1) extra memory?
- Can you solve it by divide and conquer, and what does that approach make easy that the one-pass version does not?

## Hints

### Hint 1

Fix the end of the subarray. The best subarray ending at index `i` either is `nums[i]` alone or extends the best subarray ending at `i - 1`.

### Hint 2

If the best sum ending at `i - 1` is negative, it only drags `nums[i]` down: start fresh at `i`.
