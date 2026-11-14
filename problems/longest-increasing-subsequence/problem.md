# Longest Increasing Subsequence

## Statement

You get an integer array `nums`. A subsequence keeps some of the elements, in their original order, and drops the rest; the kept elements do not have to be next to each other. Return the length of the longest subsequence whose values are strictly increasing from left to right.

Equal values never both belong to a strictly increasing subsequence.

Reference: this is our own wording of LeetCode problem 300, [Longest Increasing Subsequence](https://leetcode.com/problems/longest-increasing-subsequence/).

## Input

- `nums`: the values, in order

## Output

The length of a longest strictly increasing subsequence of `nums`.

## Examples

### Example 1

<!-- case: ex1 -->

Both 4, 5, 6, 7 and 1, 2, 3, 7 are increasing subsequences of length 4, and no increasing subsequence has five elements.

### Example 2

<!-- case: ex2 -->

All values are equal, so any increasing subsequence holds a single element.

## Constraints

- `1 <= nums.length <= 2500`
- `-10^4 <= nums[i] <= 10^4`

## Follow-ups

- The quadratic dynamic program is the classic answer. Can you reach O(n log n) time?
- How would you return one longest subsequence instead of only its length?
- What changes if the subsequence only has to be non-decreasing?

## Hints

### Hint 1

Fix the last element of the subsequence. Which earlier elements could come right before it?

### Hint 2

Let `ending[i]` be the length of the longest increasing subsequence that ends at index `i`. It is 1 plus the largest `ending[j]` over `j < i` with `nums[j] < nums[i]`.

### Hint 3

For each length `L`, only the smallest possible last value of an increasing subsequence of length `L` matters. Those smallest last values are sorted, so a binary search can tell where each new element fits.
