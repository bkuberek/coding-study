# Search in Rotated Sorted Array

## Statement

An array of distinct integers was sorted in increasing order and then rotated: some number of elements were taken off its front, keeping their order, and appended to its back. For instance, rotating `[1, 4, 6, 8, 9]` by two positions gives `[6, 8, 9, 1, 4]`. The rotation amount is unknown and may be zero, in which case the array is still fully sorted.

Given such an array `nums` and a value `target`, return the index of `target` in `nums`, or `-1` if it does not occur. Aim for a number of steps that grows with the logarithm of the length, not with the length itself.

Reference: this is our own wording of LeetCode problem 33, [Search in Rotated Sorted Array](https://leetcode.com/problems/search-in-rotated-sorted-array/).

## Input

- `nums`: distinct integers forming a rotated increasing sequence
- `target`: the value to locate

## Output

The index `i` with `nums[i] == target`, or `-1` when `target` is not in `nums`.

## Examples

### Example 1

<!-- case: ex1 -->

The array is `[3, 7, 11, 15, 18, 22]` rotated by three positions. The value 7 sits in the second sorted run, at index 4.

### Example 2

<!-- case: ex2 -->

The two sorted runs are `[40, 50]` and `[10, 20, 30]`. The value 35 would belong between 30 and 40, so it appears in neither run and the answer is `-1`.

## Constraints

- `1 <= nums.length <= 10^5`
- `-10^9 <= nums[i] <= 10^9`
- `-10^9 <= target <= 10^9`
- All values in `nums` are distinct.
- `nums` is an increasing array rotated by some amount between 0 and `nums.length - 1`.

## Follow-ups

- Can you find the answer with a single binary search instead of two?
- What breaks if the values may repeat, for example `[2, 2, 2, 0, 2]`? What is the best worst case you can still guarantee?

## Hints

### Hint 1

Split the array at any index. At least one of the two parts is sorted with no break inside it. How can you tell which one by comparing a few elements?

### Hint 2

Once you know a part is sorted, comparing `target` with its two ends tells you for certain whether `target` can be inside it.

### Hint 3

Alternatively, first locate the smallest element with a binary search: the array is then two sorted runs, and `target` can belong to only one of them.
