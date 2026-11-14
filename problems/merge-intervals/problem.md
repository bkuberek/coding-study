# Merge Intervals

## Statement

You are given a list of closed intervals, each written as `[start, end]` with `start <= end`. The list is in no particular order and intervals may overlap. Two intervals overlap when they share at least one point; in particular, `[1, 3]` and `[3, 7]` overlap because both contain 3.

Replace every group of overlapping intervals by the single interval that covers exactly the same points, repeating until no two intervals overlap. Return the resulting intervals.

Reference: this is our own wording of LeetCode problem 56, [Merge Intervals](https://leetcode.com/problems/merge-intervals/).

## Input

- `intervals`: a list of pairs `[start, end]`, in any order

## Output

The merged intervals: no two of them share a point, and together they cover exactly the points covered by the input. They may be returned in any order.

## Examples

### Example 1

<!-- case: ex1 -->

`[1, 4]` and `[3, 6]` share the points 3 and 4, so they merge into `[1, 6]`. `[14, 14]` is a single point inside `[12, 15]`, so it disappears into it. `[8, 10]` touches nothing and stays as it is.

### Example 2

<!-- case: ex2 -->

The two intervals meet at the single point 5, which counts as overlapping, so they merge into `[2, 9]`.

## Constraints

- `1 <= intervals.length <= 10^4`
- `intervals[i].length == 2`
- `0 <= intervals[i][0] <= intervals[i][1] <= 10^9`

## Follow-ups

- Merging pairs until nothing changes works, but how many comparisons can it take? What single preparation step makes one pass enough?
- How would you handle a stream of intervals arriving one at a time, answering "merged set so far" after each?

## Hints

### Hint 1

If the intervals were sorted by their start, where could an interval that overlaps the current one appear?

### Hint 2

After sorting by start, walk the list once while keeping the last merged interval. Each new interval either extends it or starts a new one.

### Hint 3

An interval extends the last merged one exactly when its start is not greater than the merged end. Extend the end with the maximum of the two ends, because the new interval may lie entirely inside the merged one.
