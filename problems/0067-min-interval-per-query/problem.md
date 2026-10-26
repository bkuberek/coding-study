# Smallest Interval per Query

## Statement

You are given a list of closed integer intervals, `intervals[i] = [left, right]`, and a list of integer points, `queries`. The size of an interval is the number of integers it contains, `right - left + 1`.

For every query point, find the smallest size among the intervals that contain it, where `[left, right]` contains `x` when `left <= x <= right`. If no interval contains the point, the answer for it is `-1`. Return the answers in the order the queries are given.

Both lists can hold 10^5 entries, so checking every interval for every query is too slow; aim for roughly `(n + q) log(n + q)` steps.

Reference: this is our own wording of LeetCode problem 1851, [Minimum Interval to Include Each Query](https://leetcode.com/problems/minimum-interval-to-include-each-query/).

## Input

- `intervals`: closed intervals `[left, right]`, in any order; they may overlap or repeat
- `queries`: the points to answer, in any order; they may repeat

## Output

An array `answer` of the same length as `queries`, where `answer[j]` is the smallest size of an interval containing `queries[j]`, or `-1` when none contains it.

## Examples

### Example 1

<!-- case: ex1 -->

Point 4 lies in `[2, 5]` (size 4), `[4, 4]` (size 1) and `[3, 9]` (size 7), so its answer is 1. Point 6 lies only in `[3, 9]`, size 7. No interval contains 1, so its answer is `-1`. Point 8 lies in `[3, 9]` and `[7, 8]`, and the smaller one has size 2.

### Example 2

<!-- case: ex2 -->

The short interval `[15, 16]` (size 2) wins for 16 and for 15, its own endpoints. Point 10 is only in `[10, 20]`, of size 11, and 21 lies beyond every interval.

## Constraints

- `1 <= intervals.length <= 10^5`
- `1 <= queries.length <= 10^5`
- `intervals[i].length == 2`
- `1 <= left <= right <= 10^7`
- `1 <= queries[j] <= 10^7`

## Follow-ups

- If the queries arrived one at a time and had to be answered immediately, what would you change?
- Can you solve it by processing the intervals from smallest to largest instead of processing the queries in order?

## Hints

### Hint 1

The answers do not depend on the order of the queries. Would it help to answer them sorted by value, and put the answers back in place afterwards?

### Hint 2

Sweep the query points from left to right. Which intervals become relevant when the sweep reaches a point, and which ones can never be relevant again?

### Hint 3

When the sweep reaches `x`, add every interval with `left <= x` to a min-heap keyed by size. Before reading the top, discard intervals whose `right` is below `x`: they will never contain a later point either.
