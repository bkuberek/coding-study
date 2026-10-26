# Median of Two Sorted Arrays

## Statement

You are given two arrays `nums1` and `nums2`, each sorted in non-decreasing order. Either of them may be empty, but not both. Consider the combined collection of all their values. Return its median.

The median of `t` sorted values is the middle one when `t` is odd, and the average of the two middle ones when `t` is even. For instance, the median of `1, 3, 8` is 3, and the median of `1, 3, 8, 10` is 5.5.

Merging the arrays is the obvious route, but the median can be found with a number of steps proportional to the logarithm of the shorter array's length.

Reference: this is our own wording of LeetCode problem 4, [Median of Two Sorted Arrays](https://leetcode.com/problems/median-of-two-sorted-arrays/).

## Input

- `nums1`: the first sorted array, of length `m`
- `nums2`: the second sorted array, of length `n`

## Output

The median of the `m + n` values, as a floating-point number. Answers within a relative tolerance of `10^-6` are accepted.

## Examples

### Example 1

<!-- case: ex1 -->

Together the values are `1, 2, 4, 7, 9`. There are five of them, so the median is the third, 4.

### Example 2

<!-- case: ex2 -->

Together the values are `3, 5, 6, 8`. The two middle values are 5 and 6, so the median is their average, 5.5.

## Constraints

- `0 <= m, n <= 10^5`
- `1 <= m + n`
- `-10^6 <= nums1[i], nums2[i] <= 10^6`
- Both arrays are sorted in non-decreasing order.

## Follow-ups

- Can you find the median without building the merged array, using O(1) extra space?
- Can you do it in O(log(min(m, n))) time?
- How would you generalize your method to the `k`-th smallest value of the two arrays?

## Hints

### Hint 1

The median splits the combined values into a lower half and an upper half of equal size (the lower half gets the extra value when the total is odd).

### Hint 2

If you take the first `i` values of `nums1` for the lower half, the size of the lower half forces how many values `j` you take from `nums2`. Only `i` is free.

### Hint 3

A choice of `i` is right exactly when the largest value taken from each array is no greater than the smallest value left in the other array. If `nums1[i - 1]` is too big, `i` must shrink; if `nums2[j - 1]` is too big, `i` must grow. Binary search `i` over the shorter array.

### Hint 4

Treat a missing neighbor (when `i` or `j` is 0 or at the end of its array) as minus or plus infinity, so the edge cases need no special branches.
