# Merge Intervals: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| absorb | brute | O(n^2) | O(n) | intervals arrive one at a time and n stays small, or as a correctness oracle |
| sort-and-sweep | optimal | O(n log n) | O(n) | default answer |

## Approach: absorb (Absorb each interval into the merged set)

### Intuition

Maintain the merged set for the intervals seen so far; it never contains two overlapping intervals. A new interval may overlap several of them at once. Fold all of those into the new interval (taking the smallest start and largest end), drop them, and add the grown interval. The set stays overlap-free after every step.

### Algorithm

1. Start with an empty list `merged`.
2. For each input interval `[start, end]`:
   1. For each interval `[s, e]` in `merged`: if `s <= end` and `start <= e` (they share a point), set `start = min(start, s)` and `end = max(end, e)`; otherwise keep `[s, e]` aside.
   2. Replace `merged` with the kept intervals plus `[start, end]`.
3. Return `merged`.

### Correctness

Invariant: after processing a prefix of the input, `merged` covers exactly the points of that prefix and no two of its intervals share a point. Adding interval `x`, every merged interval that shares a point with `x` is folded into it. Each folded interval overlaps `x`, so their union with `x` is one contiguous range, and folding replaces them by exactly that range: coverage is preserved. Could a kept interval `y` share a point `p` with the grown range? Every point of the range lies in `x` or in a folded interval. `p` cannot lie in a folded interval, because `y` and that interval are both in `merged` and therefore disjoint; so `p` lies in `x`, and `y` would have been folded. Hence the new list is still pairwise disjoint. Testing each merged interval against the growing range, as most references do, folds the same set, because of this same argument.

### Complexity

- Time: O(n^2) — interval `i` is compared with every interval currently in `merged`, which can hold up to i - 1 intervals. The generator keeps about n/4 separate groups, so the merged set holds about n/4 intervals for most of the input, about n^2/8 comparisons in total.
- Space: O(n) — the merged list and its rebuilt copy.

### Trade-offs

It needs no sorting and handles intervals in arrival order, so it is a reasonable incremental structure for tiny sets, and it is easy to check by hand, which makes it the oracle. It is quadratic as soon as the merged set grows, and every insertion rebuilds the list.

### Pitfalls and edge cases

- Overlap is `s <= end && start <= e` with closed intervals: touching endpoints (`[1, 3]` and `[3, 7]`) merge.
- Do not stop at the first overlapping merged interval: one new interval can bridge several, as `[3, 6]` bridges `[1, 4]` and `[5, 8]`.
- An interval contained in another (`[14, 14]` inside `[12, 15]`) must not shrink it: take `min` of starts and `max` of ends.

### Language notes

- Python: tuple unpacking `for start, end in intervals` reads each pair without indexing.
- Kotlin: `partition` splits the merged list into overlapping and separate intervals in one call. It tests against the original interval only, which the correctness argument shows is enough.
- Java: `merged.toArray(new int[0][])` converts the list to `int[][]`.

## Approach: sort-and-sweep (Sort by start and sweep once)

### Intuition

Sort the intervals by start. Then everything that can overlap the current merged interval comes right after it: an interval that starts after the merged end cannot overlap it, and neither can any later interval, since they start even later. So one left-to-right pass either extends the last merged interval or opens a new one.

### Algorithm

1. Sort the intervals by start.
2. For each interval `[start, end]` in that order:
   1. If `merged` is non-empty and `start <= last.end`, set `last.end = max(last.end, end)`.
   2. Otherwise append `[start, end]` to `merged`.
3. Return `merged`.

### Correctness

Invariant: after processing the first `i` sorted intervals, `merged` is the merged form of those intervals, sorted, and its last interval ends at the largest end seen so far among the intervals that formed it. The next interval starts at or after every start seen so far. If it starts at or before `last.end`, it shares the point `start` with the last merged interval, so they belong together; it cannot overlap an earlier merged interval, because those end before `last` starts, which is at most `start`. If it starts after `last.end`, it overlaps nothing in `merged`, and no later interval can bridge the gap to `last`, since later intervals start at least at `start`.

### Complexity

- Time: O(n log n) — the sort dominates; the sweep is O(n).
- Space: O(n) — the sorted copy and the output (the sort itself is O(log n) to O(n) depending on the language).

### Trade-offs

This is the expected answer: short, fast, and the base of most interval problems (`insert-interval`, `non-overlapping-intervals`, `min-meeting-rooms`). It needs all intervals up front; for a stream, a balanced tree keyed by start supports insertion with merging in O(log n) amortized.

### Pitfalls and edge cases

- Use `max(last.end, end)`, not `end`: a contained interval such as `[2, 3]` after `[1, 10]` would otherwise shrink the merged end.
- Use `<=` for the overlap test so that touching intervals merge.
- Sort a copy, or accept that the input is reordered; the references sort a copy in TypeScript and Java and use `sorted` in Python and Kotlin.

### Language notes

- Python: `sorted(intervals)` sorts pairs lexicographically, by start and then by end, which is all the sweep needs.
- TypeScript: `sort((a, b) => a[0] - b[0])` is numeric; the default `sort()` would compare `"10,12"` and `"9,11"` as strings.
- Java: `Comparator.comparingInt(interval -> interval[0])` avoids the overflow risk of `a[0] - b[0]` with large values; endpoints here reach 10^9, so subtraction could overflow for negative inputs in a variant.
- Kotlin: `sortedBy { it[0] }` returns a sorted `List<IntArray>` and leaves the input array untouched; destructuring `(start, end)` works on `IntArray`.
