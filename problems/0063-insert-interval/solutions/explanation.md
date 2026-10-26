# Insert Interval: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| append-and-merge | brute | O(n log n) | O(n) | you already have a merge routine and n is small, or as a correctness oracle |
| three-phase-scan | optimal | O(n) | O(n) | default answer |
| bound-search | optimal | O(n) | O(n) | the list is huge and stored where the untouched runs need not be copied (the search itself is O(log n)) |

The output has up to n + 1 intervals, so O(n) time and space is a lower bound for any approach that returns a new list.

## Approach: append-and-merge (Append, sort and merge again)

### Intuition

Ignore the fact that the list is already merged. Put the new interval in, sort by start, and run the standard merge sweep from `merge-intervals`.

### Algorithm

1. Append `newInterval` to a copy of `intervals` and sort the copy by start.
2. Sweep: for each interval, extend the last merged interval if the start is at most its end, otherwise append the interval.
3. Return the merged list.

### Correctness

The merge sweep on a list sorted by start returns the merged form of any set of intervals (see `merge-intervals`). The merged form of the old intervals plus the new one is exactly the required output, and the sweep emits it sorted by start.

### Complexity

- Time: O(n log n) — the sort dominates; the sweep is linear.
- Space: O(n) — the copy and the output.

### Trade-offs

It reuses a routine you may already have and is hard to get wrong, which makes it a solid oracle. It wastes the given order: the list is sorted and merged already, so a sort is never needed.

### Pitfalls and edge cases

- An empty `intervals` list produces just `[newInterval]`.
- Touching intervals merge, because the sweep tests `start <= last.end`.

### Language notes

- Kotlin: `intervals + newInterval` creates a new `Array<IntArray>` with one more element; `sortedBy { it[0] }` returns a sorted list.
- Java: `Arrays.copyOf(intervals, n + 1)` makes room for the new interval in a shallow copy.

## Approach: three-phase-scan (One pass: before, overlapping, after)

### Intuition

Because the list is sorted and separate, the old intervals split into three consecutive runs relative to the new interval: those that end before it starts, those that share a point with it, and those that start after it ends. Copy the first run, collapse the middle run together with the new interval into one interval, then copy the last run.

### Algorithm

1. Let `[start, end] = newInterval` and `index = 0`.
2. While `intervals[index].end < start`, copy `intervals[index]` to the result and advance.
3. While `intervals[index].start <= end`, set `start = min(start, intervals[index].start)`, `end = max(end, intervals[index].end)`, and advance.
4. Append `[start, end]`, then copy the remaining intervals.

### Correctness

Intervals copied in step 2 end before `start`, so they share no point with the new interval, and they come first in sorted order. In step 3, the first interval not copied ends at or after `start`; it overlaps the (growing) new interval exactly when it starts at or before the current `end`. Each absorbed interval keeps the merged interval contiguous. The first interval that starts after `end` cannot overlap, and neither can any later one, since starts increase and `end` no longer grows. The remaining intervals are separate from each other already, and the merged interval ends before them, so the result is sorted and separate.

### Complexity

- Time: O(n) — every old interval is examined once.
- Space: O(n) — the output list.

### Trade-offs

This is the expected answer: one pass, no sorting, and three short loops whose conditions read like the problem statement. It visits the untouched intervals one by one; the bound-search version locates the middle run faster but still has to copy them.

### Pitfalls and edge cases

- The first loop uses a strict `<` (an interval ending exactly at `start` touches and must be merged); the second uses `<=` for the same reason.
- `newInterval` may swallow every interval, or none; both cases fall out of the loops.
- In the second loop `end` grows, so test each interval against the current `end`, not against `newInterval[1]`. With separate input intervals the absorbed interval can only extend `end` to its own end, which is below the next interval's start, so testing against the original end gives the same answer; the growing version is simply the one that is obviously right.

### Language notes

- Python: `result.extend(intervals[index:])` copies the last run in one call.
- Kotlin: `takeWhile` and `takeLastWhile` peel off the untouched runs by their predicates, and `slice` gives the overlapping middle; this works because the runs are contiguous.
- Java: an `ArrayList<int[]>` collects the result; `toArray(new int[0][])` converts it.

## Approach: bound-search (Binary search the overlapping window)

### Intuition

Sorted, separate intervals have increasing starts and increasing ends. The first interval that can touch the new one is the first whose end is at least `newInterval.start`; the first interval that comes entirely after it is the first whose start is greater than `newInterval.end`. Both are boundaries of monotone conditions, so two binary searches find the window of intervals to merge.

### Algorithm

1. `first` = the smallest index with `intervals[first].end >= newInterval.start` (or n).
2. `after` = the smallest index with `intervals[after].start > newInterval.end` (or n).
3. If `first < after`, the intervals in `[first, after)` overlap the new one: the merged interval is `[min(newStart, intervals[first].start), max(newEnd, intervals[after - 1].end)]`. Otherwise the merged interval is `newInterval` itself.
4. Return `intervals[0, first) + [merged] + intervals[after, n)`.

### Correctness

Intervals before `first` end before the new interval starts, and intervals from `after` on start after it ends: neither group shares a point with it. Every interval in `[first, after)` ends at or after `newStart` and starts at or before `newEnd`, so it shares a point with the new interval. Their union with the new interval is contiguous and runs from the smaller of the two leftmost starts to the larger of the two rightmost ends; starts and ends increase, so those are `intervals[first].start` and `intervals[after - 1].end`. When `first >= after`, no interval overlaps and the new interval slots in at position `first`.

### Complexity

- Time: O(n) — the two searches take O(log n), but building the output copies up to n intervals. (The Python reference also builds the two key lists in O(n) before searching.)
- Space: O(n) — the output.

### Trade-offs

Same asymptotic cost as the scan, because the output must be built. The search pays off when the representation does not force a copy, for example a balanced tree or a rope of intervals, or when only the merged interval or its position is needed. In an interview it is a good follow-up answer rather than the first one.

### Pitfalls and edge cases

- The two predicates are asymmetric on purpose: `end >= newStart` (touching counts) and `start > newEnd` (touching counts, so only a strictly later start is outside).
- `first == after` means no overlap; do not read `intervals[first]` for the merged bounds in that case.
- Both searches work on an empty list and return 0.

### Language notes

- Python: `bisect_left` on the list of ends and `bisect_right` on the list of starts implement the two predicates; building those lists is O(n), which a hand-written search over the intervals avoids.
- TypeScript: one generic `firstIndex` takes the predicate; spread syntax assembles the output.
- Java: a `Predicate<int[]>` passes the condition; `System.arraycopy` copies the untouched runs into a pre-sized `int[][]`.
- Kotlin: an `inline` search helper with a lambda costs nothing at runtime; `copyOfRange` and `+` assemble the output array.
