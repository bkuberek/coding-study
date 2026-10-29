# Interval List Intersections: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| all-pairs | brute | O(m * n) | O(1) | both lists are tiny, or as a correctness oracle |
| search-partners | intermediate | O(m log n + k) | O(1) | one list is much shorter than the other |
| two-pointers | optimal | O(m + n) | O(1) | default answer |

`m` and `n` are the two lengths and `k` the number of intersections. Space excludes the output, which can hold up to m + n - 1 intervals.

## Approach: all-pairs (Intersect every pair)

### Intuition

Every common free time is the intersection of one interval from each list, and the intersection of `[a, b]` and `[c, d]` is `[max(a, c), min(b, d)]` when non-empty. Try every pair.

### Algorithm

1. For each interval `A` of `firstList`, for each interval `B` of `secondList`:
   1. Let `start = max(A.start, B.start)` and `end = min(A.end, B.end)`.
   2. If `start <= end`, append `[start, end]`.
2. Return the collected intervals.

### Correctness

Every pair is examined, and a point lies in both lists exactly when it lies in some `A` and some `B`, so the output covers exactly the common points. Within one list the intervals are separate, so the intersections lying inside one `A` are separate from those inside a later `A`, and they appear in the order of `A`; inside one `A`, they appear in the order of `B`, which is sorted and separate. So the loop order already produces the sorted output, with no extra sort.

### Complexity

- Time: O(m * n) — every pair is checked once. With the total size split at random, that is up to n^2/4 checks for a total of n intervals.
- Space: O(1) — beyond the output.

### Trade-offs

Simple and independent of the sorting, which makes it the oracle. It ignores the order of both lists, so most of its work compares intervals that are far apart.

### Pitfalls and edge cases

- Use `start <= end`, not `<`: touching intervals intersect in a single point.
- Empty lists give an empty answer without entering the inner loop.

### Language notes

- Python and Kotlin: destructuring the pairs (`for first_start, first_end in ...`, `for ((firstStart, firstEnd) in ...)`) keeps the arithmetic readable.
- Java: an `ArrayList<int[]>` collects the output; `toArray(new int[0][])` returns `int[][]`.

## Approach: search-partners (Binary search the partners of each interval)

### Intuition

For an interval `A`, the intervals of `secondList` that meet it form one consecutive run: they start with the first interval that ends at or after `A.start`, and continue while their start is at most `A.end`. The ends in `secondList` are increasing, so the first one can be found by binary search; the rest are collected by walking forward.

### Algorithm

1. For each interval `A` of `firstList`:
   1. Binary search the smallest index `p` with `secondList[p].end >= A.start`.
   2. While `p < n` and `secondList[p].start <= A.end`, append the intersection of `A` and `secondList[p]` and advance `p`.
2. Return the collected intervals.

### Correctness

Intervals of `secondList` before `p` end before `A` starts and cannot meet it. From `p` on, an interval meets `A` exactly when it starts at or before `A.end`, and once one starts after `A.end`, every later one does too. So the walk collects exactly the intersections inside `A`, in order, and the outer loop over sorted `firstList` keeps the output sorted, as in the brute force.

### Complexity

- Time: O(m log n + k) — one binary search per interval of `firstList`, plus one step per reported intersection (and at most one failed check per interval).
- Space: O(1) — beyond the output.

### Trade-offs

Better than the two-pointer walk when `firstList` is short and `secondList` is long (m log n is far below m + n), for example a few meetings checked against a long calendar. With lists of similar size it is slower by a log factor, and it is more code than the walk.

### Pitfalls and edge cases

- Search on the ends of `secondList`, not the starts: an interval that starts before `A.start` may still reach into `A`.
- One interval of `secondList` may meet several intervals of `firstList`; each search starts fresh, so it is reported once per partner, as required.

### Language notes

- Python and TypeScript: the search is written out; `bisect` would need a separate list of ends.
- Kotlin: `val (secondStart, secondEnd) = secondList[partner]` destructures an `IntArray`.
- Go: `sort.Search(n, pred)` returns the first index where `pred` holds, so the search runs over `secondList` itself with no separate list of ends; the loop that follows is a plain `for` with a post statement.
- Rust: `partition_point` is the same search over the sorted `Vec`, and `second_list[partner..].iter().take_while(..)` walks the partners that start by `first_end`.

## Approach: two-pointers (Walk both lists with two pointers)

### Intuition

Look at the current interval of each list and report their intersection if any. Then drop the one that ends first: every later interval of the other list starts after the other current interval ends, and that one ends no earlier, so the dropped interval cannot meet anything else. Each step drops one interval, so the walk is linear.

### Algorithm

1. Set `i = j = 0`.
2. While `i < m` and `j < n`:
   1. Let `start = max(first[i].start, second[j].start)` and `end = min(first[i].end, second[j].end)`; if `start <= end`, append `[start, end]`.
   2. If `first[i].end < second[j].end`, advance `i`; otherwise advance `j`.
3. Return the collected intervals.

### Correctness

Suppose `first[i]` ends first, at `e <= second[j].end`. Every later interval of `secondList` starts after `second[j].end >= e`, so it cannot meet `first[i]`, and all earlier ones were already dropped. So `first[i]` has no unreported partner left and may be discarded; the symmetric case drops `second[j]` (on a tie, either may go, since neither can meet a later interval of the other list). Every pair that intersects is therefore current at the same time at some step and gets reported. Reported intersections come out sorted: each one ends at `min(first[i].end, second[j].end)`, the smaller current end, and current ends only increase.

### Complexity

- Time: O(m + n) — each iteration advances one pointer, so there are at most m + n iterations of O(1) work.
- Space: O(1) — two pointers, beyond the output.

### Trade-offs

The expected answer: linear, short and allocation-free apart from the output. It is the same "advance whichever ends first" idea as merging two sorted lists, and it generalizes to `k` lists with a heap of current intervals.

### Pitfalls and edge cases

- Advance by end, not by start: advancing the interval that starts first can skip a partner of the other one.
- Points (`[t, t]`) need no special handling: the intersection test `start <= end` and the end comparison treat them like any interval.
- Stop as soon as either list is exhausted; nothing can intersect an empty list.

### Language notes

- Kotlin: destructuring both current intervals into named values keeps the loop body close to the prose.
- Java and TypeScript: index access `first[i][0]` on nested arrays; no copies are made until an intersection is reported.
