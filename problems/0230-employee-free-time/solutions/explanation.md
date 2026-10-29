# Employee Free Time: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| elementary-segments | brute | O(n^2) | O(n) | n is tiny, or as a correctness oracle |
| flatten-and-sort | optimal | O(n log n) | O(n) | default answer |
| heap-merge | optimal | O(n log k) | O(k) | the employees' lists are long and few (k much smaller than n), or arrive as streams |

Here `n` is the total number of intervals and `k` the number of employees. The generator grows `k` with `n` (about n / 10 employees), so the measured class of `heap-merge` on the ladder is `n log n`.

## Approach: elementary-segments (Test every gap between neighboring endpoints against every interval)

### Intuition

Cut the timeline at every endpoint of every interval. Inside one piece nothing starts or ends, so the piece is either entirely busy or entirely free. A piece is free exactly when no interval covers it.

### Algorithm

1. Flatten all the intervals and collect the sorted distinct endpoints.
2. For each pair of neighboring endpoints `(left, right)`, check whether any interval has `start <= left < end`.
3. If none does, `[left, right]` is a free span.

### Correctness

No endpoint lies strictly inside `(left, right)`, so no interval starts or ends there: an interval either covers the whole piece or none of it, and covering `left` (with `start <= left < end`) means covering the piece. Two free pieces are never adjacent. The point between them is an endpoint of some interval, and that interval covers the piece on one side of it, so no merging of neighboring free pieces is needed. Pieces before the first start and after the last end do not exist, so they are never reported.

### Complexity

- Time: O(n^2) — O(n) pieces, each tested against up to n intervals.
- Space: O(n) — the flattened list and the list of endpoints.

### Trade-offs

Obviously correct and easy to trust as an oracle, but quadratic. It never uses the order inside each employee's list.

### Pitfalls and edge cases

- Test `start <= left` and `left < end`: the intervals are half-open, so an interval ending exactly at `left` does not cover the piece that starts there.
- Free spans must not extend to the unbounded time before the first start or after the last end.

### Language notes

- Python: a set comprehension gives the distinct endpoints and `itertools.pairwise` walks neighboring pairs.
- TypeScript: `new Set(...)` removes duplicates, and the numeric comparator in `sort` matters (the default sort is lexicographic).
- Java: a `TreeSet<Integer>` keeps the endpoints distinct and sorted.
- Kotlin: `toSortedSet()` and `zipWithNext()` express the same thing.

## Approach: flatten-and-sort (Sort all intervals by start and sweep the busy end)

### Intuition

This is Merge Intervals, but reporting the gaps instead of the merged spans. Who works when does not matter, so throw all the intervals into one list, sort it by start and keep track of how far the busy block currently reaches.

### Algorithm

1. Flatten the schedules and sort the intervals by start.
2. Set `busyUntil` to the end of the first interval.
3. For each interval `[start, end]`: if `start > busyUntil`, record the free span `[busyUntil, start]`. Then set `busyUntil = max(busyUntil, end)`.
4. Return the recorded spans.

### Correctness

Invariant: after the intervals with the smallest starts have been processed, `busyUntil` is the end of the busy block that contains the last of them, and every free span before it has been recorded. An interval whose start is beyond `busyUntil` starts after every earlier interval has ended, so nobody works in between, and that gap is exactly the next free span. An interval that starts at or before `busyUntil` extends or sits inside the block.

### Complexity

- Time: O(n log n) — sorting dominates; the sweep is linear.
- Space: O(n) — the flattened copy and the output.

### Trade-offs

The simplest optimal answer. It ignores that each employee's list is already sorted, which is what the heap version exploits.

### Pitfalls and edge cases

- Use a strict `start > busyUntil`: a start equal to `busyUntil` touches the busy block and leaves no gap.
- Take the maximum of the ends: a nested interval ends earlier than the block that contains it and must not pull `busyUntil` back.
- A single interval, or intervals that fully overlap, produce an empty answer.

### Language notes

- Python: `sorted` over a generator that flattens the schedules; tuples unpack in the loop.
- TypeScript: `schedule.flat()` builds a new outer array, so the in-place `sort` with a numeric comparator does not touch the input.
- Java: collect the intervals in an `ArrayList<int[]>`, sort with `Comparator.comparingInt`, and return `free.toArray(new int[0][])`.
- Kotlin: `schedule.flatten().sortedBy { it[0] }`, with the result as `toTypedArray()` (an empty answer is `emptyArray<IntArray>()`).

## Approach: heap-merge (Merge the employees' sorted lists with a min-heap)

### Intuition

Every employee's list is already sorted by start, so the whole schedule is `k` sorted lists. Merging them with a min-heap, as in merging k sorted lists, yields the intervals in start order without sorting all `n` of them, and the same sweep then finds the gaps.

### Algorithm

1. Push each employee's first interval into a min-heap keyed by start, together with the employee and the position.
2. Set `busyUntil` to the smallest start.
3. Pop the smallest entry. If its start is greater than `busyUntil`, record `[busyUntil, start]`. Set `busyUntil = max(busyUntil, end)`.
4. Push that employee's next interval, if there is one, and repeat until the heap is empty.

### Correctness

The heap pops the intervals in nondecreasing order of start, which is the standard argument for a k-way merge: each list is sorted, and the heap always holds the next unseen interval of every list. The sweep therefore sees the same sequence as in flatten-and-sort, and its invariant holds.

### Complexity

- Time: O(n log k) — `n` pops and pushes on a heap of at most `k` entries.
- Space: O(k) — one heap entry per employee (the output list is not counted).

### Trade-offs

Better than a full sort when `k` is much smaller than `n`, and it works on lists that arrive as streams. It is more code, and in this problem's generator `k` grows with `n`, so its ladder class is `n log n`.

### Pitfalls and edge cases

- Heap entries need a comparable tie-breaker, the employee index, so the interval list itself is never compared (which most languages cannot do, and Python would do slowly).
- Do not push an employee's next interval before popping the current one; the heap would then hold two entries of the same employee.

### Language notes

- Python: `heapq` with `(start, person, position)` tuples compares them field by field.
- TypeScript: there is no built-in heap, so the reference includes a small binary min-heap of `[start, person, position]` entries (as `min-meeting-rooms` does).
- Java: `PriorityQueue<int[]>` with `Comparator.comparingInt` on the start and then the employee; the answer is built in a `List<int[]>` and returned with `toArray(new int[0][])`.
- Kotlin: `PriorityQueue<IntArray>(compareBy({ it[0] }, { it[1] }))`; destructuring an `IntArray` gives `start`, `person` and `position`.
