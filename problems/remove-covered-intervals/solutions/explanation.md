# Remove Covered Intervals: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| all-pairs | brute | O(n^2) | O(1) | n is tiny, or as a correctness oracle |
| sort-and-sweep | optimal | O(n log n) | O(n) | default answer |

## Approach: all-pairs (Check each interval against all the others)

### Intuition

Apply the definition directly. An interval survives when no other interval of the list contains it, so for each interval look for one that does.

### Algorithm

1. For each interval `[a, b]`, scan the other intervals `[c, d]` for one with `c <= a` and `b <= d`.
2. Count the intervals for which the scan finds none.
3. Return the count.

### Correctness

Covering is transitive: if `x` is covered by `y` and `y` by `z`, then `z` covers `x`. So removing covered intervals in any order leaves exactly the intervals that no interval of the original list covers: a covered interval is removed whether or not its coverer is removed first, since the coverer's own coverer takes over. The scan tests the definition for every interval.

### Complexity

- Time: O(n^2) — each of the n intervals is compared with up to n - 1 others.
- Space: O(1) — only counters; no copy of the input.

### Trade-offs

Almost no code and no sorting, so it is a trustworthy oracle. About 10^7 comparisons at n = 5000 make it unusable at the full constraint of 10^4 intervals when time is tight.

### Pitfalls and edge cases

- Skip the interval itself (`j != i`); otherwise every interval covers itself and the answer is always 0.
- Sharing an endpoint counts as covered: `[1, 6]` covers `[2, 6]` and `[1, 5]`.

### Language notes

- Python: the inner scan is an `any(...)` over `enumerate`.
- Java, TypeScript and Kotlin: stop the inner scan as soon as a cover is found (`return true` in a helper, `some`, `any`). About half of the generated intervals have no cover and scan all the others, which keeps the work quadratic.

## Approach: sort-and-sweep (Sort by start with longer intervals first and track the furthest end)

### Intuition

Sort by start ascending and, for equal starts, by end descending. Then an interval that covers another always comes before it. Sweeping in that order, an interval is covered exactly when an earlier one reaches at least as far to the right.

### Algorithm

1. Sort the intervals by `(start, -end)`.
2. Keep `reach`, the largest end seen so far, starting at -1.
3. For each interval, if `end > reach` it remains: count it and set `reach = end`. Otherwise it is covered.
4. Return the count.

### Correctness

If `end <= reach`, the interval that set `reach` starts at or before this one (sorted order) and ends at or after it, so it covers it. If `end > reach`, every earlier interval ends before this one ends, so none of them covers it. Every later interval either starts later, or has the same start and, because equal starts are sorted by end descending and the intervals are distinct, ends earlier; so no later interval covers it either.

### Complexity

- Time: O(n log n) — sorting dominates; the sweep is one pass.
- Space: O(n) — the sorted copy.

### Trade-offs

One pass after the sort and a single running maximum. Sorting in place would save the copy at the price of mutating the input.

### Pitfalls and edge cases

- With ascending ends for equal starts, `[1, 3]` would be counted before `[1, 8]` and wrongly survive; the descending end order is what makes the sweep correct.
- Use `>` and not `>=`: an equal end means the interval is covered.
- The first interval always remains, since `reach` starts below every end.

### Language notes

- Python: `sorted(intervals, key=lambda interval: (interval[0], -interval[1]))`.
- TypeScript: `[...intervals].sort((a, b) => a[0] - b[0] || b[1] - a[1])`; the comparator must return a number, not a boolean.
- Java: `Arrays.sort` on `intervals.clone()` with an explicit comparator that uses `Integer.compare` on starts and then on ends in reverse.
- Kotlin: `intervals.sortedWith(compareBy<IntArray>({ it[0] }, { -it[1] }))`; destructuring `(_, end)` skips the start.
- Go: `slices.Clone` plus `slices.SortFunc` with `cmp.Or(cmp.Compare(a[0], b[0]), cmp.Compare(b[1], a[1]))`; swapping `a` and `b` in the second comparison is the "longer first" order, and the comparator must return a negative, zero or positive `int`, not a boolean.
- Rust: the function owns its vector, so `sort_unstable_by(|a, b| a[0].cmp(&b[0]).then(b[1].cmp(&a[1])))` sorts it in place; `Ordering::then` chains the tie-break.
