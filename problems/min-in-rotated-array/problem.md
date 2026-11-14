# Minimum in Rotated Sorted Array

## Statement

An increasing array of distinct integers has been rotated an unknown number of times. One rotation moves the last element to the front, so rotating `[2, 5, 7, 9]` once gives `[9, 2, 5, 7]`, and rotating it four times gives the original array back.

Given the rotated array `nums`, return its smallest value. Try to do it in a number of steps proportional to the logarithm of the length.

Reference: this is our own wording of LeetCode problem 153, [Find Minimum in Rotated Sorted Array](https://leetcode.com/problems/find-minimum-in-rotated-sorted-array/).

## Input

- `nums`: distinct integers forming a rotated increasing sequence

## Output

The minimum value of `nums` (the value, not its index).

## Examples

### Example 1

<!-- case: ex1 -->

The array is `[2, 9, 14, 27, 31, 40]` after three rotations. The values climb to 40, drop to 2, and climb again; the drop lands on the minimum, 2.

### Example 2

<!-- case: ex2 -->

This array has been rotated a multiple of four times, so it is fully sorted and the minimum is its first element.

## Constraints

- `1 <= nums.length <= 10^5`
- `-10^9 <= nums[i] <= 10^9`
- All values in `nums` are distinct.
- `nums` is an increasing array rotated any number of times.

## Follow-ups

- How does your answer change if values may repeat, as in `[3, 3, 1, 3]`? Can the worst case still be logarithmic?
- Can you return the number of rotations instead of the minimum value?

## Hints

### Hint 1

The minimum is the only element that is smaller than the element before it (or the first element, when nothing was rotated).

### Hint 2

Look at a middle element and the last element. If the middle one is larger, where must the drop be?

### Hint 3

If `nums[middle]` is smaller than the last element, everything from `middle` to the end is increasing, so the minimum is `middle` itself or somewhere to its left. Keep `middle` in the range.
