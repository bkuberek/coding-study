# Can Attend All Meetings: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| all-pairs | brute | O(n^2) | O(1) | n is tiny, or as a correctness oracle |
| sort-and-scan | optimal | O(n log n) | O(n) | default answer |

## Approach: all-pairs (Compare every pair of meetings)

### Intuition

Two half-open meetings share a moment exactly when each one starts before the other one ends. If no pair does, the whole day can be attended, so test every pair.

### Algorithm

1. For every pair of meetings `i < j`, test `start_i < end_j` and `start_j < end_i`.
2. Return `false` on the first pair that passes both tests.
3. Return `true` if no pair does.

### Correctness

The overlap test is exact for half-open intervals: `[a, b)` and `[c, d)` have a common moment if and only if `a < d` and `c < b`. Every unordered pair is tested, so the function returns `false` exactly when some two meetings overlap.

### Complexity

- Time: O(n^2) — n(n - 1) / 2 pair tests in the worst case, which is when the answer is `true`.
- Space: O(1) — only loop counters and the four values of the current pair.

### Trade-offs

No sorting and no extra memory, and the code is short enough to trust as an oracle. It does about 1.25 * 10^7 tests at n = 5000 and falls over long before the usual list sizes of a real calendar.

### Pitfalls and edge cases

- Using `<=` in the overlap test would reject back-to-back meetings such as `[8, 10]` and `[10, 12]`.
- The empty list and a single meeting have no pairs, so the answer is `true`.

### Language notes

- Python: the pairs are unpacked once per loop level with tuple assignment.
- Java and Kotlin: indexing `intervals[i][0]` directly avoids allocating anything in the inner loop.

## Approach: sort-and-scan (Sort by start and compare neighbors)

### Intuition

Once the meetings are sorted by start, a clash can only start between meetings that sit next to each other in the list: if the first meeting overlaps a later one, it also overlaps the meeting right after it. So one pass over neighbors is enough.

### Algorithm

1. Sort a copy of the meetings by start (ties in any order).
2. For each neighboring pair, check `previous.end <= next.start`.
3. Return `false` if some pair fails the check, `true` otherwise.

### Correctness

Suppose meeting `a` overlaps meeting `b` and `a` is sorted before `b`. Every meeting between them in the list starts in `[a.start, b.start]`, which is before `a.end` because `b` starts before `a` ends. The meeting listed right after `a` therefore starts before `a.end`, so that neighbor pair fails the check. Conversely, a neighbor pair that fails the check is an overlapping pair, so the scan reports `false` exactly when an overlap exists.

### Complexity

- Time: O(n log n) — sorting dominates; the scan is a single pass.
- Space: O(n) — the sorted copy. Sorting the input in place would bring this down to O(1) extra (or O(log n) for the sort itself), at the price of mutating the caller's list.

### Trade-offs

Faster than the pairwise check by a factor of n / log n. The references copy the input before sorting so the caller's order is untouched. If the meetings already arrive sorted, the scan alone is O(n).

### Pitfalls and edge cases

- Compare with `<=` in the passing condition (`previous.end <= next.start`), so touching meetings are accepted.
- The empty list must return `true`: the scan simply has no neighbor pairs.

### Language notes

- Python: `sorted` plus `itertools.pairwise` expresses the neighbor check in one `all(...)`.
- TypeScript: always pass a numeric comparator, `[...intervals].sort((a, b) => a[0] - b[0])`; the default sort compares as strings, so `1000` would come before `999`.
- Java: `intervals.clone()` is shallow, which is enough to keep the caller's order; `Arrays.sort` with `Comparator.comparingInt` sorts the copy.
- Kotlin: `sortedBy { it[0] }` returns a new list, and `zipWithNext().all { (earlier, later) -> ... }` is empty, hence `true`, for fewer than two meetings.
