# Insert Interval

## Statement

You are given a list `intervals` of closed intervals `[start, end]` that are already in good shape: sorted by start, and pairwise separate, so each interval ends before the next one begins (they do not even share an endpoint). You are also given one more closed interval, `newInterval`.

Add `newInterval` to the list and return the list in the same good shape: sorted by start and with no two intervals sharing a point. Wherever the new interval overlaps or touches existing intervals, they must be combined into one.

Reference: this is our own wording of LeetCode problem 57, [Insert Interval](https://leetcode.com/problems/insert-interval/).

## Input

- `intervals`: sorted, pairwise separate intervals `[start, end]`; the list may be empty
- `newInterval`: the interval `[start, end]` to add

## Output

The intervals after the insertion, sorted by start, with no two sharing a point, covering exactly the points of `intervals` and `newInterval` together.

## Examples

### Example 1

<!-- case: ex1 -->

`[7, 11]` overlaps both `[6, 8]` and `[10, 14]`, so the three combine into `[6, 14]`. `[1, 3]` is untouched.

### Example 2

<!-- case: ex2 -->

`[5, 7]` falls in the gap between `[2, 4]` and `[9, 12]`, overlaps neither, and is simply placed between them.

## Constraints

- `0 <= intervals.length <= 10^5`
- `intervals[i].length == 2` and `newInterval.length == 2`
- `0 <= start <= end <= 10^9` for every interval, including `newInterval`
- `intervals[i][1] < intervals[i + 1][0]` for every valid `i`.

## Follow-ups

- The input is already sorted and merged. Can you avoid sorting it again?
- Can you find which existing intervals are affected in O(log n)? Why does the overall cost stay O(n)?

## Hints

### Hint 1

The existing intervals fall into three runs: those that end before the new interval starts, those that overlap it, and those that start after it ends.

### Hint 2

Copy the first run unchanged, fold the middle run into the new interval by taking the smallest start and the largest end, then copy the last run.

### Hint 3

Because the intervals are sorted and separate, both their starts and their ends are increasing, so the borders of the middle run can also be found with binary search.
