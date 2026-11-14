# Remove Covered Intervals

## Statement

You are given a list of distinct intervals `[left, right]`. The interval `[a, b]` is covered by the interval `[c, d]` when `c <= a` and `b <= d`, that is, when it lies inside the other one; sharing an endpoint is allowed.

Remove every interval that is covered by another interval of the list, and return how many intervals remain. Covering is transitive, so the answer is the number of intervals that no other interval covers, whatever order the removals happen in.

Reference: this is our own wording of LeetCode problem 1288, [Remove Covered Intervals](https://leetcode.com/problems/remove-covered-intervals/).

## Input

- `intervals`: distinct `[left, right]` pairs, in any order

## Output

The number of intervals that are not covered by any other interval.

## Examples

### Example 1

<!-- case: ex1 -->

The interval `[3, 5]` lies inside `[2, 9]`, and `[10, 11]` lies inside `[6, 12]`. Neither `[2, 9]` nor `[6, 12]` lies inside another interval, so 2 intervals remain.

### Example 2

<!-- case: ex2 -->

Each interval starts later and ends later than the one before it, so none lies inside another and all 3 remain.

## Constraints

- `1 <= intervals.length <= 10^4`
- `intervals[i].length == 2`
- `0 <= intervals[i][0] < intervals[i][1] <= 10^5`
- All the intervals are distinct.

## Follow-ups

- Can you return the remaining intervals themselves?
- What changes if the list may contain duplicates (two equal intervals cover each other)?

## Hints

### Hint 1

After sorting by start, which intervals can cover a given one?

### Hint 2

Among intervals with the same start, which order makes the rule "an earlier interval covers me" complete?

### Hint 3

Sort by start, and by end descending for equal starts. An interval is covered exactly when the largest end seen so far is at least its end.
