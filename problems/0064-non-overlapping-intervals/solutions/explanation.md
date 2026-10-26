# Non-Overlapping Intervals: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| chain-dp | brute | O(n^2) | O(n) | intervals carry weights (the DP generalizes, the greedy does not), or as a correctness oracle |
| earliest-end | optimal | O(n log n) | O(n) | default answer: the classic interval-scheduling greedy |
| drop-longer-end | optimal | O(n log n) | O(n) | the list is already sorted by start, for example after a merge step |

Removing the fewest intervals is the same as keeping the most pairwise non-conflicting intervals, so every approach computes that maximum `kept` and returns `n - kept`.

## Approach: chain-dp (Longest compatible chain by dynamic programming)

### Intuition

Sort by start. A set of non-conflicting intervals, listed by start, is a chain in which each interval begins at or after the previous one ends. So the largest such set is the longest chain, which a longest-increasing-subsequence style DP finds: the best chain ending with interval `i` extends the best chain ending with some earlier compatible interval `j`.

### Algorithm

1. Sort the intervals by start (then by end).
2. For each `i`, set `longest[i] = 1 + max(longest[j])` over all `j < i` with `end[j] <= start[i]`, or 1 if there is none.
3. Return `n - max(longest)`.

### Correctness

In a non-conflicting set sorted by start, each interval ends at or before the next one starts, so the set is a chain in the sorted order. Conversely, a chain built by step 2 is non-conflicting: consecutive members do not overlap, and since each member ends after it starts, every later member starts after every earlier one ends. By induction over `i`, `longest[i]` is the size of the longest chain ending at `i`: its predecessor is some compatible `j < i` whose best chain can be used unchanged. The maximum over `i` is therefore the largest non-conflicting set.

### Complexity

- Time: O(n^2) — every pair `j < i` is checked once, after an O(n log n) sort.
- Space: O(n) — the sorted copy and the DP table.

### Trade-offs

Slow, but it is the version that survives a change in the problem: with a value per interval ("maximize the total value kept"), replace `+1` with `+ value[i]` and the DP still works, while the greedy does not. (That weighted variant is usually solved in O(n log n) by sorting by end and binary searching the latest compatible interval.)

### Pitfalls and edge cases

- Use `end[j] <= start[i]`: touching intervals are compatible here, unlike in `merge-intervals`.
- The answer is `n - max(longest)`, not `n - longest[n - 1]`: the best chain need not end with the interval that starts last.

### Language notes

- Python: the inner maximum is a generator expression with `default=0` for the first interval.
- TypeScript: the comparator `a[0] - b[0] || a[1] - b[1]` breaks ties by end; differences of values within ±10^9 are exact doubles.
- Java: `Comparator.<int[]>comparingInt(...).thenComparingInt(...)` needs the explicit type witness for the chained lambda.
- Kotlin: `compareBy<IntArray>({ it[0] }, { it[1] })` builds the two-key comparator.

## Approach: earliest-end (Greedy by earliest end)

### Intuition

Of all intervals, keep the one that ends first: whatever an optimal solution keeps first, swapping it for the earliest-ending interval cannot cause a new conflict, because it ends no later. Then discard everything that conflicts with it and repeat on the rest. Sorting by end makes "repeat" a single pass: keep an interval whenever it starts at or after the end of the last kept one.

### Algorithm

1. Sort the intervals by end.
2. Set `kept = 0` and `lastEnd = -infinity`.
3. For each interval in that order, if `start >= lastEnd`, keep it: `kept += 1`, `lastEnd = end`.
4. Return `n - kept`.

### Correctness

Exchange argument. Let the greedy keep `g1, g2, ...` and let an optimal solution, sorted by end, be `o1, o2, ...`. Claim: for every `k`, `gk` ends no later than `ok`. For `k = 1`, `g1` is the earliest-ending interval overall. If `gk` ends no later than `ok`, then `o(k+1)`, which starts at or after `ok` ends, also starts at or after `gk` ends, so it was available to the greedy at step `k + 1`; the greedy picks the earliest-ending available interval, so `g(k+1)` ends no later than `o(k+1)`. Hence the greedy keeps at least as many intervals as the optimum, and it is itself non-conflicting by construction.

### Complexity

- Time: O(n log n) — the sort; the pass is O(n).
- Space: O(n) — the sorted copy (Python's `sorted` and the copies in the other languages).

### Trade-offs

This is the canonical answer (activity selection). It is a few lines, and the exchange argument is a good thing to be able to state out loud. It only works for counting: with weights, use the DP.

### Pitfalls and edge cases

- Sort by end, not by start: by start, a long early interval would be kept and block many short ones.
- `start >= lastEnd` with `>=`, because touching does not conflict.
- Initialize `lastEnd` below every possible start. The starts can be as low as -10^9, so 0 or -1 would be wrong; the references use minus infinity, `Long.MIN_VALUE`, or "nothing kept yet".

### Language notes

- Python: `None` stands for "nothing kept yet", which avoids picking a sentinel value.
- TypeScript: `-Infinity` compares below every number.
- Java: `lastEnd` is a `long` so that `Long.MIN_VALUE` is a safe sentinel against `int` starts.
- Kotlin: the same `Long.MIN_VALUE` sentinel; an `Int` start compares with a `Long` directly in Kotlin, and `end.toLong()` widens for the assignment.

## Approach: drop-longer-end (Sort by start and drop the later-ending interval)

### Intuition

Sort by start and walk the list while keeping one "current" interval. When the next interval conflicts with the current one, one of the two must go. Drop whichever ends later: the one that ends first leaves more room for everything after it, by the same exchange argument as before.

### Algorithm

1. Sort the intervals by start; let the first one be current, with `keptEnd = end`.
2. For each following interval:
   1. If `start < keptEnd` (conflict), count one removal and set `keptEnd = min(keptEnd, end)`.
   2. Otherwise set `keptEnd = end`.
3. Return the number of removals.

### Correctness

Invariant: after processing a prefix in start order, the kept intervals of that prefix are pairwise non-conflicting, their number is the maximum possible for the prefix, and among all maximum selections the kept one has the smallest last end, `keptEnd`. A non-conflicting next interval can be added to it. A conflicting next interval cannot be added to any maximum selection with last end `keptEnd`; keeping the earlier-ending of the two preserves the count and gives the smallest possible last end, because the next interval starts no earlier than any interval in the prefix.

### Complexity

- Time: O(n log n) — the sort; the pass is O(n).
- Space: O(n) — the sorted copy.

### Trade-offs

Equivalent to the earliest-end greedy and equally fast. It is convenient when the data is already sorted by start (as in many interval pipelines) and it counts removals directly. The earliest-end version is easier to justify, so present that one first.

### Pitfalls and edge cases

- On a conflict, take `min(keptEnd, end)`: if the new interval is nested inside the current one, the current one is the one to drop.
- The comparison is strict `start < keptEnd`; touching is not a conflict.
- The list has at least one interval, so reading the first element is safe.

### Language notes

- Python: `sorted(intervals)` orders by start and then end; the tie order does not affect the count.
- Kotlin: `ordered.drop(1)` iterates everything after the first interval, with destructuring into `(start, end)`.
- Java and TypeScript: an index loop from 1 skips the first interval without copying.
