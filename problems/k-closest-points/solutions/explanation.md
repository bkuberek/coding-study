# K Closest Points to Origin: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| sorting | brute | O(n log n) | O(n) | simplest code; also gives the points in distance order |
| max-heap | optimal | O(n log k) | O(k) | `k` is small, or the points arrive as a stream |
| quickselect | optimal | O(n) average, O(n^2) worst | O(n) | the follow-up asks for linear time |

`n` is the number of points. All three compare squared distances, `x * x + y * y`, which order points exactly like Euclidean distances and avoid floating point. With coordinates up to `10^4`, a squared distance is at most `2 * 10^8`, which fits a 32-bit integer.

## Approach: sorting (Sort by squared distance and keep the first k)

### Intuition

Sort the points by distance from the origin; the first `k` are the answer.

### Algorithm

1. Sort a copy of the points by `x * x + y * y`.
2. Return the first `k` points.

### Correctness

After sorting, the first `k` points have the `k` smallest distances. The constraints guarantee that the `k`-th smallest distance is strictly smaller than the next one, so no point outside the first `k` ties with one inside, and the first `k` points are exactly the unique answer regardless of how the sort orders equal distances.

### Complexity

- Time: O(n log n) — the sort dominates.
- Space: O(n) — the sorted copy.

### Trade-offs

Short and obviously correct, which makes it the oracle. It orders all n points although only a set of k is required; for a one-off query in production code it is often the right choice anyway, because library sorts are fast.

### Pitfalls and edge cases

- Computing `sqrt` is unnecessary and introduces floating-point noise; squared distances compare exactly.
- A comparator that subtracts distances (`a - b`) is safe here only because distances stay well below `2^31`; with larger coordinates use `Integer.compare`.

### Language notes

- Python: `sorted(..., key=...)` computes each key once (decorate-sort-undecorate).
- TypeScript: the comparator recomputes both distances on every comparison; precomputing them would save time on large inputs.
- Java: `Comparator.comparingInt(point -> ...)` with `Arrays.sort` on `int[][]` sorts the row references; `Arrays.copyOf(sorted, k)` keeps the first k rows.
- Kotlin: `sortedBy { (x, y) -> ... }` destructures an `IntArray` with `component1()` and `component2()`; `toTypedArray()` converts back to `Array<IntArray>`.
- Go: `slices.SortFunc` takes a three-way comparison, so `cmp.Compare` on the two squared distances is the whole comparator. Like the TypeScript version it recomputes both distances on every comparison, and `slices.Clone` copies only the outer slice of row headers, so the input order is kept and no row is copied.
- Rust: `sort_unstable_by_key` computes the key from a borrowed `&Vec<i32>` row, which the helper takes as `&[i32]`; ties may land in any order, which the unique answer allows. The function owns `points`, so it sorts and `truncate`s that vector in place. Squared distances are at most 2 * 10^8, inside `i32`.

## Approach: max-heap (Max-heap of the k closest points seen)

### Intuition

Keep only the `k` closest points seen so far. The one that matters is the farthest of them: a new point either beats it and replaces it, or does not belong in the answer. A max-heap keyed by distance keeps that farthest point at its root.

### Algorithm

1. For each point with squared distance `d`:
   1. If the heap holds fewer than `k` points, push it.
   2. Otherwise, if `d` is smaller than the root's distance, replace the root with this point.
2. Return the points in the heap.

### Correctness

Invariant: after each point, the heap holds `k` points of the prefix (or all of them while fewer than `k` were seen), and no point outside the heap is strictly closer than a point inside. A new point that is not closer than the root cannot displace any heap point under that invariant; a closer one replaces the farthest heap point and restores it. At the end, by the uniqueness guarantee, the heap is exactly the set of the `k` closest points.

### Complexity

- Time: O(n log k) — each point costs at most one O(log k) heap operation. With `k` drawn across all ranks, as in the generated cases, that grows like n log n.
- Space: O(k) — the heap.

### Trade-offs

Best when `k` is small relative to `n`, and the natural choice for a stream: memory stays O(k) however many points arrive. For `k` near `n` it is no better than sorting.

### Pitfalls and edge cases

- Use a max-heap, not a min-heap: a min-heap of all n points works but costs O(n) memory and O(n + k log n) time.
- Replace only on a strictly smaller distance; replacing on equality is still correct here but does useless work.

### Language notes

- Python: `heapq` is a min-heap, so the reference stores `(-distance, index)`: the root is the farthest kept point, and the index breaks ties so the point lists are never compared.
- TypeScript: no built-in priority queue, so the reference implements a max-heap of `{distance, index}` entries.
- Java: `PriorityQueue<int[]>` with `(a, b) -> Integer.compare(b[0], a[0])` keeps `{distance, index}` entries with the farthest at the head; iterating the queue at the end visits its entries in heap order, which is fine for an unordered answer.
- Kotlin: the heap stores point indexes ordered by `compareByDescending(::squared)`, a reference to a local function; `heap.map { points[it] }` collects the answer.
- Go: `container/heap` needs a type that implements `heap.Interface`, so the reference declares `farthestFirst []entry` with `Less` comparing distances with `>`. Replacing the root and calling `heap.Fix(&kept, 0)` is the single sift-down that Python spells `heapreplace`. Entries carry the input position, and the unique answer makes a tie-break on it unnecessary.
- Rust: `BinaryHeap<(i32, usize)>` is a max-heap of `(distance, position)` tuples, which compare element by element, so the farthest point is the root. `peek_mut()` lets the loop overwrite the root, and dropping the guard sifts it down once. The rows are moved out of `points` with `std::mem::take` instead of cloned.

## Approach: quickselect (Quickselect on squared distances)

### Intuition

The answer is a set: the `k` closest points, in any order. Partitioning around a pivot distance splits the points into closer, equal and farther groups; you then only need to keep partitioning the group that contains the boundary between position `k - 1` and `k`. Once position `k - 1` holds its final sorted entry, everything before it is closer or equal, which is the answer.

### Algorithm

1. Compute every squared distance; let `order` be the indexes `0..n-1`.
2. While the range `low..high` has more than one element:
   1. Pick a random pivot distance from the range and partition `order[low..high]` into three blocks: closer, equal, farther.
   2. If `k - 1` lies in the closer block, continue there; if it lies in the farther block, continue there; otherwise stop.
3. Return the points at `order[0..k-1]`.

### Correctness

Invariant: every index left of `low` refers to a point at most as far as every point in `low..high`, and every index right of `high` to a point at least as far. Partitioning keeps that invariant and places the equal block at its final sorted positions. When `k - 1` falls inside the equal block, or the range shrinks to one element, position `k - 1` holds a point with the `k`-th smallest distance and positions `0..k-1` hold `k` points none of which is farther than any point after them. With the uniqueness guarantee, that is exactly the answer.

### Complexity

- Time: O(n) average, O(n^2) worst — a random pivot shrinks the range by a constant factor in expectation; consistently unlucky pivots are quadratic but vanishingly unlikely.
- Space: O(n) — the distance and index arrays; the loop itself uses O(1).

### Trade-offs

Linear on average and the answer to the follow-up. It is the longest of the three and rearranges an index array, and it needs all points up front. The three-way partition matters on inputs like case `g2`, where 10^5 points share at most 19 distinct squared distances.

### Pitfalls and edge cases

- Partitioning the `points` array directly works too, but swapping index integers is cheaper than swapping row references in some languages and keeps the input untouched.
- A two-way partition degrades badly on many equal distances.

### Language notes

- Python: random pivots come from the `random` module; the result does not depend on them, only the running time does.
- TypeScript: destructuring swaps (`[a[i], a[j]] = [a[j], a[i]]`) are concise; a temporary variable is faster in hot loops.
- Java: primitive `int[]` arrays for distances and indexes avoid boxing; `ThreadLocalRandom` draws the pivot.
- Kotlin: `IntArray(size) { ... }` builds both arrays, and a private `IntArray.swap` extension keeps the partition readable.
- Go: `math/rand/v2` is randomly seeded, so `rand.IntN(high-low+1)` draws a pivot position with no setup. The final decision is an `if` chain rather than a `switch`, because a `break` inside a `switch` would only leave the switch and not the loop.
- Rust: the standard library has no random number generator, so the reference carries a few lines of xorshift seeded from `RandomState`. `order.swap(i, j)` swaps two indexes in place, the partition is a `match` on `cmp`, and the answer rows are moved out of `points` with `std::mem::take`.
