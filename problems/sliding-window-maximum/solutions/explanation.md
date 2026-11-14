# Sliding Window Maximum: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| brute-force | brute | O(n * k) | O(1) | k is tiny, or as a correctness oracle |
| heap | intermediate | O(n log n) | O(n) | you need a priority queue anyway, or the window rule is irregular |
| monotonic-deque | optimal | O(n) | O(k) | default answer |

Space excludes the returned array of `n - k + 1` maxima.

## Approach: brute-force (Scan every window)

### Intuition

There are `n - k + 1` windows. Compute the maximum of each one directly.

### Algorithm

1. For each `start` from 0 to `n - k`, scan `nums[start .. start+k-1]` and append its maximum.
2. Return the maxima.

### Correctness

Each output entry is the maximum of exactly the window it belongs to, and the windows are enumerated left to right.

### Complexity

- Time: O(n * k) — `n - k + 1` windows of `k` elements. The generator picks `k` between n/8 and n/2, so this is at least `7n^2/64` steps at every seed.
- Space: O(1) — one running maximum per window.

### Trade-offs

Trivially correct, hence the oracle, and fine when `k` is small. For wide windows it rescans the `k - 1` elements that consecutive windows share, about 10^8 steps at n = 3 * 10^4.

### Pitfalls and edge cases

- There are `n - k + 1` windows, not `n - k`; with `k = n` there is exactly one.
- Initialize the running maximum with the window's first element, not 0: all values may be negative.

### Language notes

- Python: `max(nums[start:start + k])` copies and scans the slice in C, about ten times faster than a Python loop but still O(k) per window.
- TypeScript: an explicit inner loop; `Math.max(...nums.slice(...))` spreads up to 10^5 arguments and can exceed the engine's argument limit.
- Java: preallocate `int[n - k + 1]` and fill it.
- Kotlin: `IntArray(size) { start -> ... }` computes each entry with a lambda.
- Go: `nums[start+1 : start+k]` is a window view of the same backing array, so the scan allocates nothing, and the built-in `max` (Go 1.21 and newer) replaces a hand-written comparison.
- Rust: `nums.windows(k)` yields each window as a borrowed slice, and `iter().max()` returns an `Option` because a slice may be empty, so the reference unwraps it: `k` is at least 1.

## Approach: heap (Max-heap with lazy removal)

### Intuition

A max-heap of the window's elements gives the maximum in O(1) and accepts new elements in O(log n). Removing the element that leaves the window is the awkward part, so do not remove it right away: store positions in the heap, and only when the top's position has fallen out of the window, pop it. Stale entries below the top are harmless until they surface.

### Algorithm

1. For each `right`:
   1. Push `right` into a heap ordered by `nums[right]`, largest first.
   2. If `right >= k - 1`: pop while the top's position is at most `right - k`, then append `nums[top]`.
2. Return the maxima.

### Correctness

Every position at or before `right` has been pushed, so the heap contains every element of the current window, plus possibly some stale ones from earlier. After the popping loop, the top is a position inside the window (positions inside the window are never popped, because they satisfy `pos > right - k`). The top is the largest element of everything in the heap, which includes the whole window, so it is the window's maximum.

### Complexity

- Time: O(n log n) — n pushes and at most n pops, each O(log n) on a heap of at most n entries.
- Space: O(n) — stale entries can accumulate; on a rising input the heap holds everything pushed so far.

### Trade-offs

A general technique that works for any "maximum of a changing set" question, including windows with irregular rules. It is slower than the deque and uses more memory, and TypeScript has no built-in heap, so it costs extra code there. In an interview it is a good intermediate step to mention.

### Pitfalls and edge cases

- Compare positions, not values, when deciding whether the top is stale; with duplicates, a value can be both stale and present in the window.
- Pop stale entries only from the top. Removing an arbitrary element from a binary heap is O(n) in most libraries.
- Order by value only; ties can come out in either order without affecting the answer.

### Language notes

- Python: `heapq` is a min-heap, so the reference pushes `(-value, position)` tuples.
- TypeScript: the reference implements a small array-backed binary heap of positions, compared through `nums`.
- Java: `PriorityQueue<Integer>` with the comparator `(a, b) -> Integer.compare(nums[b], nums[a])`. Never compare with `nums[b] - nums[a]` in general: subtraction overflows for large values (it is safe here only because values are within 10^4).
- Kotlin: `PriorityQueue<Int>(compareByDescending { nums[it] })`.
- Go: `container/heap` is a set of functions over a type with five methods (`Len`, `Less`, `Swap`, `Push`, `Pop`), and it builds a min-heap from `Less`, so `Less` reports the larger value as smaller. Call `heap.Push` and `heap.Pop` on the type, never its own `Push` and `Pop` methods, which only append and truncate the slice.
- Rust: `BinaryHeap` is a max-heap already, and `(value, position)` tuples compare by value first, so the reference needs no comparator or negation. `peek` returns an `Option<&T>`, which `while let Some(&(largest, position))` unpacks.

## Approach: monotonic-deque (Deque of decreasing candidates)

### Intuition

If `nums[j] >= nums[i]` with `i < j`, then `i` can never be the maximum of any window that still contains `j`, and every future window that contains `i` also contains `j`. So `i` is useless once `j` arrives. Keeping only useful positions leaves a list whose values strictly decrease from oldest to newest. The front is the window's maximum; the back is where new elements arrive, after evicting smaller values; the front leaves when it slides out of the window.

### Algorithm

1. Start with an empty deque `candidates` of positions.
2. For each `right`:
   1. While the back's value is at most `nums[right]`, pop the back.
   2. Push `right` at the back.
   3. If the front's position is at most `right - k`, pop the front.
   4. If `right >= k - 1`, append `nums[front]`.
3. Return the maxima.

### Correctness

Invariant: `candidates` holds, in increasing position order, exactly the positions `p` in the current window such that no later position in the window has a value at least `nums[p]`. Their values are therefore strictly decreasing. Step 2.1 removes the positions that the new element makes useless, step 2.2 adds the new one (which nothing later dominates yet), and step 2.3 removes the one position that may have left the window (only the front can be that old, and at most one position leaves per step). The window's maximum is never dominated by a later element, so it is a candidate, and as the largest candidate it is at the front.

### Complexity

- Time: O(n) — every position is pushed once and popped at most once, from either end.
- Space: O(k) — all candidates are inside the window; a falling input keeps up to `k` of them.

### Trade-offs

Linear and the expected optimal answer. The same "monotonic queue" idea solves shortest subarray with sum at least `K` (with negative numbers) and jump-game variants with a window. It needs a double-ended queue; in languages without a fast one, an array with head and tail indices works, as in the TypeScript reference.

### Pitfalls and edge cases

- Store positions, not values: the front must be recognized as having left the window.
- Pop the back with `<=`, not `<`: with `<`, equal values stay and the deque is only non-increasing, which is still correct but keeps more entries.
- Remove the expired front before reading the maximum.
- `k = 1`: every element evicts the previous one, and the output equals the input.

### Language notes

- Python: `collections.deque` gives O(1) `pop`, `append` and `popleft`; a list's `pop(0)` would be O(n).
- TypeScript: `Array.prototype.shift` is O(n) in the worst case, so the reference uses an `Int32Array` of capacity n with `head` and `tail` indices.
- Java: `ArrayDeque<Integer>` with `peekLast`, `pollLast`, `peekFirst` and `pollFirst`; the boxed positions are compared after unboxing, so `<=` on them is safe.
- Kotlin: `kotlin.collections.ArrayDeque` with `last()`, `removeLast()`, `first()` and `removeFirst()`.
- Go: there is no deque type. A slice works as one: `candidates[:len(candidates)-1]` pops the back and `candidates[1:]` pops the front, both O(1). When `append` outgrows the shrunken capacity it copies only the live elements, so memory stays O(k).
- Rust: `VecDeque<usize>` is the deque (`push_back`, `pop_back`, `pop_front`, indexing by `candidates[0]`). Positions are `usize`, so the window test is written `candidates[0] + k <= right` instead of `candidates[0] <= right - k`, which would underflow while `right < k`.
