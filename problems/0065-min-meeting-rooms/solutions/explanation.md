# Minimum Meeting Rooms: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| count-at-starts | brute | O(n^2) | O(1) | n is tiny, or as a correctness oracle |
| end-time-heap | optimal | O(n log n) | O(n) | you also need to assign rooms, or meetings arrive in start order as a stream |
| sorted-sweep | optimal | O(n log n) | O(n) | default answer when only the count is needed |

## Approach: count-at-starts (Count the meetings running at every start)

### Intuition

The number of rooms needed is the largest number of meetings in progress at one moment. That count only goes up when a meeting starts, so its maximum is reached at some meeting's start time. Check every start and count the meetings running then.

### Algorithm

1. For each meeting's start `t`, count the meetings with `start <= t < end`.
2. Return the largest count.

### Correctness

Fewer rooms than the peak overlap cannot work, since the meetings running at that moment each need their own room. The peak number of rooms also suffices: assigning meetings in start order to any free room never needs more rooms than are running at that start (the heap approach below makes this concrete). The running count is piecewise constant and increases only at start times, so the maximum over start times is the maximum over all moments. A meeting ending at `t` is not counted at `t`, which matches the half-open schedule.

### Complexity

- Time: O(n^2) — n start times, each compared with all n meetings.
- Space: O(1) — two counters (the Python version uses generators, not lists).

### Trade-offs

Very little code and no sorting, so it is a trustworthy oracle. It does n^2 comparisons, 2.5 * 10^7 at n = 5000, and cannot handle the full constraint of 10^5 meetings in time.

### Pitfalls and edge cases

- The running test is `start <= t < end`; using `t <= end` would count a meeting that ends exactly when another starts, and back-to-back meetings would wrongly need two rooms.
- Every meeting counts itself at its own start, so the answer is at least 1.

### Language notes

- Python: nested generator expressions inside `max` and `sum` avoid building lists.
- Kotlin: `moment in start until end` is exactly the half-open test; destructuring lambdas `{ (start, end) -> ... }` work on `IntArray` through `component1` and `component2`.
- Rust: an iterator chain (`map` over the moments, `filter` and `count` over the meetings, `max`) mirrors the nested generator expressions and builds no list.

## Approach: end-time-heap (Min-heap of end times)

### Intuition

Hand out rooms in order of meeting start. When a meeting starts, the only room that might be free is the one whose current meeting ends earliest. Keep the end times of the meetings that hold rooms in a min-heap: if the smallest end time is at most the new start, reuse that room (replace its end time); otherwise open a new room. The heap size at the end is the number of rooms opened.

### Algorithm

1. Sort the meetings by start.
2. For each meeting `[start, end]`:
   1. If the heap is non-empty and its minimum is at most `start`, remove the minimum.
   2. Push `end`.
3. Return the heap size.

### Correctness

The heap holds one entry per opened room: the end time of the last meeting placed in it. The heap never shrinks, since every pop is followed by a push. A new room is opened only when the earliest-ending room is still busy at `start`; then every room is busy at `start`, so the meetings in them plus the new one run at the same moment, and the peak overlap is at least the new number of rooms. Hence the number of rooms opened never exceeds the peak overlap, and it cannot be lower.

### Complexity

- Time: O(n log n) — sorting, plus one push and at most one pop per meeting, each O(log n).
- Space: O(n) — the heap holds up to n end times, plus the sorted copy.

### Trade-offs

The heap version simulates the actual allocation, so storing a room id next to each end time turns it into a room assignment, the natural follow-up. If meetings already arrive sorted by start (a stream), it works online. For a bare count, the sorted sweep is shorter and avoids the heap.

### Pitfalls and edge cases

- Pop at most one entry per meeting. Popping every ended meeting is also correct but then the answer is the maximum heap size seen, not the final size; mixing the two styles gives wrong counts.
- Compare with `<=`: a room freed at time `t` can be reused at `t`.

### Language notes

- Python: `heapq` is a min-heap over a list; `heapreplace` pops the minimum and pushes in one sift.
- TypeScript: there is no built-in priority queue, so the reference includes a small binary min-heap; sorting a fresh array of end times on every meeting would be O(n^2 log n).
- Java: `PriorityQueue<Integer>` boxes each end time. `ends.peek() <= meeting[0]` unboxes the `Integer`, so the comparison is numeric (`==` between two `Integer`s would not be).
- Kotlin: `java.util.PriorityQueue<Int>` is the same class; `peek()` returns a platform type, compared numerically after unboxing.
- Go: `container/heap` needs a small `intHeap` type (`Len`, `Less`, `Swap`, `Push`, `Pop`). Overwriting `(*ends)[0]` and calling `heap.Fix(ends, 0)` is Python's `heapreplace`.
- Rust: `BinaryHeap` is a max-heap, so end times are wrapped in `Reverse`. The reference replaces the earliest end with a `pop` and a `push`; `peek_mut` would replace it in place with one sift.

## Approach: sorted-sweep (Sweep sorted starts against sorted ends)

### Intuition

To know how many meetings run at each moment, only the multiset of start times and the multiset of end times matter, not which end belongs to which start. Sort both lists. Walk the starts in order; for each one, if the earliest end time not yet used is at most this start, some meeting has finished and its room can be reused; otherwise a new room is needed.

### Algorithm

1. Sort all start times into `starts` and all end times into `ends`.
2. Set `rooms = 0` and `ended = 0`.
3. For each `start` in `starts`: if `ends[ended] <= start`, increment `ended`; otherwise increment `rooms`.
4. Return `rooms`.

### Correctness

Write `s_k` for the `k`-th smallest start. Just after `s_k`, the number of running meetings is `k - E(s_k)`, where `E(t)` counts the end times at or before `t`; the peak overlap is the largest of these values. After step `k`, `rooms + ended = k`, and `ended <= E(s_k)`, because only ends at or before the current start are consumed and starts never decrease. So `rooms >= k - E(s_k)` after every step, which makes the final `rooms` at least the peak. Conversely, `rooms` grows at step `k` only when no unconsumed end is at or before `s_k`, that is, when `ended == E(s_k)`; then the new `rooms` equals `k - E(s_k)`, an overlap that really occurs, so `rooms` never exceeds the peak. The final `rooms` is therefore exactly the peak overlap.

### Complexity

- Time: O(n log n) — two sorts and a linear sweep.
- Space: O(n) — the two sorted arrays.

### Trade-offs

The shortest optimal solution, with primitive arrays and no heap, so it is also the fastest in practice. It loses the pairing between starts and ends, so it cannot produce a room assignment.

### Pitfalls and edge cases

- `ends[ended] <= start` must use `<=` for the half-open schedule.
- `ends[ended]` never reads past the end: an end at or before `s_k` belongs to a meeting that started strictly earlier, so at most `k - 1` ends can have been consumed when step `k` reads one.
- Duplicate start or end times need no special handling.

### Language notes

- Python: two `sorted` calls over generator expressions build the lists.
- TypeScript: always pass a numeric comparator to `sort`; the default compares strings, so `1000` would sort before `999`.
- Java: primitive `int[]` arrays sorted with `Arrays.sort` avoid all boxing.
- Kotlin: `IntArray(n) { ... }.apply { sort() }` builds and sorts each primitive array in one expression.
- Go and Rust: `slices.Sort` and `sort_unstable` order primitive integers in place with no comparator, so there is no string-comparison trap like TypeScript's default `sort`.
