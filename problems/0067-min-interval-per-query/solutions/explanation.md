# Smallest Interval per Query: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| scan-all | brute | O(n * q) | O(1) | both lists are tiny, or as a correctness oracle |
| sweep-with-heap | optimal | O((n + q) log(n + q)) | O(n + q) | default answer: the standard offline sweep |
| paint-smallest-first | optimal | O(n log n + q log q) | O(n + q) | you prefer reasoning about intervals rather than about a sweep line |

`n` is the number of intervals and `q` the number of queries. Space excludes the input and the output array.

## Approach: scan-all (Scan every interval for every query)

### Intuition

For each query point, look at every interval, keep those that contain the point, and take the smallest size.

### Algorithm

1. For each query `x`:
   1. Set `best` to "none".
   2. For each interval `[left, right]` with `left <= x <= right`, set `best = min(best, right - left + 1)`.
   3. Report `best`, or `-1` if it is still "none".

### Correctness

Each answer is the minimum over exactly the intervals that contain the point, which is the definition; an empty set of such intervals gives `-1`.

### Complexity

- Time: O(n * q) — every query checks every interval. The generator uses as many queries as intervals, so this is quadratic in the input size.
- Space: O(1) — one running minimum per query, beyond the output.

### Trade-offs

It is the definition turned into code, which makes it the oracle. At the constraint limits (10^5 by 10^5) it would need 10^10 checks, so it is only usable for small inputs.

### Pitfalls and edge cases

- Containment is inclusive at both ends: `left <= x <= right`.
- The size counts points, so `[4, 4]` has size 1, not 0.

### Language notes

- Python: `min(..., default=-1)` returns `-1` for an empty generator without a separate check.
- Kotlin: `filter` plus `minOfOrNull` returns `null` when no interval contains the point, and `?: -1` maps it to the sentinel. The filtered list is allocated per query, which is fine for an oracle.

## Approach: sweep-with-heap (Sweep sorted queries with a min-heap of sizes)

### Intuition

Answer the queries in increasing order of value (remembering their original positions). As the sweep moves right, intervals become relevant when the sweep passes their left end, and stop being relevant forever once it passes their right end. Keep the relevant intervals in a min-heap keyed by size; the top is the answer, provided it has not expired. Expired intervals are removed lazily, only when they reach the top.

### Algorithm

1. Sort the intervals by `left`, and sort the query indices by query value.
2. For each query `x` in increasing order:
   1. Push `(size, right)` for every interval not yet pushed whose `left <= x`.
   2. Pop from the heap while its top has `right < x`.
   3. The answer for this query is the top's size, or `-1` if the heap is empty.
3. Return the answers in the original query order.

### Correctness

Invariant: when query `x` is answered, the heap contains every interval with `left <= x` and `right >= x` (plus possibly some with `right < x` buried below the top). Every interval with `left <= x` was pushed in step 2.1, either now or for an earlier, smaller query. An interval is popped only when `right < x' <= x` for the query `x'` being answered then, so it cannot contain `x` or any later query, because queries only increase. After step 2.2, the top has `right >= x` and `left <= x`, so it contains `x`; it has the smallest size of everything in the heap, including every interval containing `x`. If the heap is empty, no interval contains `x`.

### Complexity

- Time: O((n + q) log(n + q)) — two sorts, n pushes and at most n pops, each O(log n).
- Space: O(n + q) — the heap, the sorted copy of the intervals and the sorted query order.

### Trade-offs

This is the standard solution, and its shape (sort events, sweep, heap of active items with lazy deletion) reappears in skyline, meeting-room and scheduling problems. It is offline: all queries must be known in advance. For online queries, a segment tree over the coordinates storing the minimum size per point, or the painting approach followed by a lookup structure, would be needed.

### Pitfalls and edge cases

- Lazy deletion only checks the top. An expired interval deeper in the heap is harmless because it is never read before it reaches the top, where it is popped.
- Repeated query values work: the second copy sees the same heap state.
- Put the answers back by original index; answering in sorted order and returning that order is the most common bug.

### Language notes

- Python: `heapq` compares tuples lexicographically, so `(size, right)` orders by size first; `sorted(range(q), key=queries.__getitem__)` gives the query order without building pairs.
- TypeScript: there is no built-in heap, so the reference carries a small binary heap over `[size, right]` pairs.
- Java: `PriorityQueue<int[]>` with a two-key comparator; the query order is an `Integer[]` because `Arrays.sort` with a comparator does not accept `int[]`.
- Kotlin: `queries.indices.sortedBy { queries[it] }` gives the order; `candidates.peek()?.let { ... }` handles the empty heap, since `peek` returns `null` then.

## Approach: paint-smallest-first (Paint queries from the smallest interval up with union-find)

### Intuition

Process intervals from smallest to largest. The first interval that covers a query point is the smallest one containing it, so it fixes that answer for good; larger intervals should then skip it. "Skip points that already have an answer" is what a union-find structure over the sorted distinct query points does well: each point links to the next point that is still open, and path compression makes repeated skipping cheap.

### Algorithm

1. Sort the distinct query values into `points`; every point starts open with answer `-1`.
2. Let `nextOpen[k] = k` for every point, plus a sentinel at index `len(points)`. `firstOpen(k)` follows the links to the first open point at or after `k`, compressing the path.
3. For each interval in order of increasing size:
   1. Find `k = firstOpen(first point >= left)` with a binary search.
   2. While `k` is a real point with `points[k] <= right`: record the size as its answer, close it (`nextOpen[k] = k + 1`), and move to `firstOpen(k + 1)`.
4. Map every original query to its point's answer.

### Correctness

Intervals are handled by increasing size, and a point is closed the first time an interval containing it is handled, so its recorded size is the smallest size of an interval containing it. Points that no interval contains are never closed and keep `-1`. Within one interval, the walk visits exactly the open points in `[left, right]`: it starts at the first open point at or after `left`, and each step jumps to the next open point, stopping past `right`. Closed points are skipped, which is correct because their answers are already final.

### Complexity

- Time: O(n log n + q log q) — sorting both lists, one binary search per interval (O(n log q)), and union-find work that is nearly linear: each point is closed once, and path compression keeps every `firstOpen` call amortized close to O(1) (O(log q) at worst with compression alone).
- Space: O(n + q) — the sorted copies, the distinct points, their answers and the links.

### Trade-offs

Same asymptotic cost as the sweep, and it closes each query point exactly once, which makes the total work easy to bound. The "process by priority and paint what is still blank" idea also solves interval-coloring and "who covers this point last" problems. It is less familiar to interviewers than the heap sweep and has more moving parts (deduplication, the sentinel, path compression), so present it as the alternative.

### Pitfalls and edge cases

- Deduplicate the queries, or several copies of one value would need separate closing; mapping back through the distinct values answers every copy.
- The sentinel index `len(points)` must exist in `nextOpen`, because closing the last point links it there.
- Recursion-free path compression keeps deep chains (up to 10^5 links) from overflowing the stack.

### Language notes

- Python: `bisect_left` finds the first point at or after `left`; the compression loop uses tuple assignment to relink and advance in one step.
- TypeScript: `new Set(queries)` deduplicates; a `Map` from value to index answers the original queries.
- Java: `Arrays.stream(queries).distinct().sorted().toArray()` builds the points, and `Arrays.binarySearch` maps each query back, since every query value is present.
- Kotlin: a local function `firstOpen` closes over the `nextOpen` array; `binarySearch` returns `-(insertionPoint) - 1` on a miss, which the code converts to the first point at or after `left`.
