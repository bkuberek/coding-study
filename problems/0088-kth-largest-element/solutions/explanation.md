# Kth Largest Element: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| sorting | brute | O(n log n) | O(n) | simplest code; fine for most real inputs |
| min-heap | optimal | O(n log k) | O(k) | `k` is small, or the values arrive as a stream |
| quickselect | optimal | O(n) average, O(n^2) worst | O(n) | the follow-up asks for linear time |

`n` is the length of `nums`. The answer is the element at ascending index `n - k`. Sorting finds every rank; the heap tracks only the top `k`; quickselect narrows down to the one index it needs.

## Approach: sorting (Sort and index from the end)

### Intuition

In ascending order, the largest value is at index `n - 1`, the second largest at `n - 2`, and the `k`-th largest at `n - k`.

### Algorithm

1. Sort a copy of `nums` ascending.
2. Return the element at index `n - k`.

### Correctness

Sorting places the values in ascending order with duplicates kept, so exactly `k - 1` positions lie after index `n - k`. The value there therefore has `k - 1` values at or above it in the descending order, which is the definition of rank `k` with duplicates counted.

### Complexity

- Time: O(n log n) — the sort dominates.
- Space: O(n) — the sorted copy (sorting in place would avoid it, at the cost of mutating the input).

### Trade-offs

One line in every language and very fast in practice, which makes it the oracle. It does more work than needed: it orders all n values to read one. In an interview, state it first and then improve.

### Pitfalls and edge cases

- Index `n - k`, not `k`: that would be the `(k + 1)`-th smallest.
- In TypeScript, `Array.prototype.sort()` without a comparator sorts numbers as strings; the reference sorts an `Int32Array`, which compares numerically.

### Language notes

- Kotlin: `IntArray.sortedArray()` returns a sorted copy of the primitive array.
- Java: `Arrays.sort(int[])` is a dual-pivot quicksort on primitives; `clone()` keeps the input unchanged.
- Go: `slices.Clone` plus `slices.Sort` sorts a copy of the `[]int`, and `sorted[len(sorted)-k]` is the answer, with the same index arithmetic as Python.
- Rust: the function owns `nums`, so it sorts that vector in place. `sort_unstable` is the right call for plain integers, since equal values are indistinguishable and the unstable sort needs no scratch buffer.

## Approach: min-heap (Min-heap of the k largest values seen)

### Intuition

To know the `k`-th largest value you only need the `k` largest ones, and among those only the smallest matters. A min-heap of at most `k` values keeps exactly that smallest one at its root. A new value that beats the root belongs to the top `k` and evicts the root; any other value does not.

### Algorithm

1. Push values until the heap holds `k` of them.
2. For each remaining value, if it is greater than the root, replace the root with it.
3. Return the root.

### Correctness

Invariant: after scanning a prefix with at least `k` values, the heap holds the `k` largest values of that prefix (as a multiset). A new value `v` that is not greater than the root cannot be among the top `k` of the longer prefix, because `k` values at least as large already exist. If `v` is greater, the root is the smallest of the old top `k`, so replacing it with `v` gives the new top `k`. At the end the heap holds the top `k` of the whole array, and its root, their minimum, is rank `k`.

### Complexity

- Time: O(n log k) — each value costs at most one O(log k) heap operation. With `k = n/2`, as in the generated cases of 100 values or more, this grows like n log n.
- Space: O(k) — the heap.

### Trade-offs

Excellent when `k` is small, and the only approach here that works on a stream without storing it. For `k` close to n it is no better than sorting; flipping to a max-heap of the `n - k + 1` smallest values helps in that case.

### Pitfalls and edge cases

- A max-heap of all values popped `k` times also works but costs O(n + k log n) and O(n) space, and it is easy to mix up.
- Use a strict `>` when comparing with the root: replacing on equality is still correct but does useless work on duplicates.

### Language notes

- Python: `heapq` is a min-heap, which is exactly what this needs; `heapify` on the first `k` values is O(k), and `heapreplace` pops and pushes in one sift.
- TypeScript: no built-in priority queue, so the reference implements a binary min-heap with `push` and `replaceRoot`.
- Java: `PriorityQueue<Integer>` defaults to a min-heap; values are boxed, and `peek()` unboxes when compared with an `int`.
- Kotlin: the same `java.util.PriorityQueue<Int>`; `heap.peek()` is a platform type that unboxes on comparison.
- Go: `container/heap` needs a type that implements `heap.Interface`, so the reference declares `minHeap []int` with `Less` as `<`. `heap.Init` heapifies the first `k` values in O(k), and `heap.Fix(&largest, 0)` after overwriting the root is `heapreplace`: one sift-down instead of a pop and a push.
- Rust: `BinaryHeap` is a max-heap, so wrapping the values in `Reverse` turns it into the min-heap this approach needs. `collect()` heapifies in O(k), and `peek_mut()` hands out the root: assigning through it and dropping the guard sifts the new root down once, which is `heapreplace`.

## Approach: quickselect (Quickselect with a random pivot and three-way partition)

### Intuition

Quicksort partitions around a pivot and then sorts both sides. To find one rank you only need the side that contains it. Each partition removes on average a constant fraction of the candidates, so the total work is a geometric series: linear on average.

### Algorithm

1. Copy `nums`; let `target = n - k` (the answer's ascending index), `low = 0`, `high = n - 1`.
2. Repeat:
   1. Pick a random pivot value from `values[low..high]`.
   2. Partition `values[low..high]` into three blocks: less than the pivot (`low..less - 1`), equal (`less..greater`), greater (`greater + 1..high`).
   3. If `target < less`, continue with `high = less - 1`; if `target > greater`, continue with `low = greater + 1`; otherwise return the pivot.

### Correctness

Invariant: the element at ascending index `target` of the whole array is in `values[low..high]`, and every value left of `low` is at most it and every value right of `high` is at least it. After the three-way partition, the block of values equal to the pivot occupies exactly the indexes `less..greater` in sorted order; if `target` falls in it, the answer is the pivot. Otherwise the answer lies in the block of smaller or of larger values, and narrowing to that block keeps the invariant. The equal block is never empty (it contains the pivot), so every iteration shrinks the range and the loop ends.

### Complexity

- Time: O(n) average, O(n^2) worst — with a random pivot, the expected range shrinks by a constant factor per iteration, so the expected work is about `n + 3n/4 + ...`, linear. The worst case (unlucky pivots every time) is quadratic but vanishingly unlikely.
- Space: O(n) — the copy of the input; the loop itself uses O(1). Partitioning the input array in place would remove the copy.

### Trade-offs

Linear on average and the classic answer to the follow-up. It is longer than the alternatives, rearranges its array, and has a quadratic worst case; the median-of-medians pivot rule guarantees O(n) but is rarely worth its constant factor. For many repeated values, the three-way partition is essential.

### Pitfalls and edge cases

- Always choosing the first or last element as the pivot is quadratic on sorted input (case `g3`).
- A two-way partition is quadratic on inputs with few distinct values (case `g2`): every equal value lands on the same side.
- The target index is `n - k`, because partitioning orders ascending.

### Language notes

- Python: the pure-Python partition is slower per element than the C sort used by `sorted`, so for 10^5 values the sorting approach is faster in practice even though quickselect is asymptotically better.
- TypeScript: `Math.floor(Math.random() * (high - low + 1))` draws a uniform index; destructuring swaps are concise but allocate a temporary array.
- Java: `ThreadLocalRandom.current().nextInt(low, high + 1)` draws a pivot index without a shared `Random` instance.
- Kotlin: `kotlin.random.Random.nextInt(from, until)` and a private `IntArray.swap` extension keep the partition readable; `when` with no subject chooses the branch.
- Go: `math/rand/v2` is seeded randomly by default, so `rand.IntN(high-low+1)` needs no setup, and a tagless `switch` picks the partition branch. The function ends in a `for` loop with no condition, which Go accepts as the final statement without a trailing `return`.
- Rust: the standard library has no random number generator, and the project builds with the standard library only. The reference uses a few lines of xorshift seeded from `RandomState`, whose keys are random per process, which is enough to make adversarial inputs unlikely to hit a bad pivot. `values.swap(i, j)` replaces the tuple swap, and the three-way partition is a `match` on `cmp`.
