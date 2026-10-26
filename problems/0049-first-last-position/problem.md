# First and Last Position

## Statement

You are given an array `nums` sorted in non-decreasing order, so equal values sit next to each other, and a value `target`. Find the block of positions that hold `target`: the index of its first occurrence and the index of its last occurrence.

If `target` does not occur, report that with `[-1, -1]`. The intended solution takes a number of steps proportional to the logarithm of the length, even when `target` fills most of the array.

Reference: this is our own wording of LeetCode problem 34, [Find First and Last Position of Element in Sorted Array](https://leetcode.com/problems/find-first-and-last-position-of-element-in-sorted-array/).

## Input

- `nums`: integers in non-decreasing order; the array may be empty
- `target`: the value whose block of positions you must find

## Output

A two-element array `[first, last]` with the smallest and the largest index `i` such that `nums[i] == target`, or `[-1, -1]` when there is no such index. When `target` occurs once, `first` and `last` are equal.

## Examples

### Example 1

<!-- case: ex1 -->

The value 3 occupies positions 1, 2 and 3, so the block runs from 1 to 3.

### Example 2

<!-- case: ex2 -->

The value 5 would fit between 4 and 9 but does not occur, so the answer is `[-1, -1]`.

## Constraints

- `0 <= nums.length <= 10^5`
- `-10^9 <= nums[i] <= 10^9`
- `-10^9 <= target <= 10^9`
- `nums[i] <= nums[i + 1]` for every valid `i`.

## Follow-ups

- If you find one occurrence with binary search and then walk left and right, how slow can that get?
- How would you count the occurrences of `target` with the same two searches?

## Hints

### Hint 1

The first occurrence of `target` is the first position whose value is not less than `target`, provided that position holds `target`.

### Hint 2

The last occurrence is just before the first position whose value is greater than `target`.

### Hint 3

Both positions are boundaries of a monotone condition, so each can be found with one binary search that keeps going after it sees `target` instead of stopping.
