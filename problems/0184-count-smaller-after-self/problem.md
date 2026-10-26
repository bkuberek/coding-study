# Count Smaller Numbers After Self

## Statement

You get an integer array `nums`. For every position `i`, count how many values to the right of it are strictly smaller than `nums[i]`, and return those counts as an array of the same length.

Equal values do not count as smaller. The last position always gets 0, since nothing is to its right.

Reference: this is our own wording of LeetCode problem 315, [Count of Smaller Numbers After Self](https://leetcode.com/problems/count-of-smaller-numbers-after-self/).

## Input

- `nums`: the values

## Output

An array `counts` with `counts[i]` equal to the number of positions `j > i` such that `nums[j] < nums[i]`.

## Examples

### Example 1

<!-- case: ex1 -->

To the right of 7 are 3, 9, 3 and 5; three of them (3, 3 and 5) are smaller. To the right of 3 are 9, 3 and 5, and none is strictly smaller (the other 3 is equal). To the right of 9 are 3 and 5, both smaller. Then 3 has nothing smaller after it, 5 has nothing at all after it.

### Example 2

<!-- case: ex2 -->

In a strictly decreasing array, every value is larger than everything after it, so the counts are 3, 2, 1 and 0.

## Constraints

- `1 <= nums.length <= 10^5`
- `-10^9 <= nums[i] <= 10^9`

## Follow-ups

- Comparing every pair is O(n^2). Can you do O(n log n)?
- The values are spread over two billion possible numbers. How do you index a tree by value anyway?
- The total of all counts is the number of inversions of the array. How does merge sort count inversions while it sorts?

## Hints

### Hint 1

Walk from the right end to the left. When you reach position `i`, you have seen exactly the values to its right; you need to know how many of them are smaller than `nums[i]`.

### Hint 2

Replace every value by its rank among the distinct values (coordinate compression). Then "how many seen values are smaller" is a prefix count over ranks, which a Fenwick tree answers in O(log n) while you add values one at a time.

### Hint 3

Alternatively, sort positions by value with merge sort. When an element from the left half is placed, every element already taken from the right half is smaller and was to its right.
