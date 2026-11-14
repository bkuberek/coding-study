# Merge K Sorted Lists: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| one-by-one | brute | O(k N) | O(1) | `k` is tiny |
| min-heap | optimal | O(N log k) | O(k) | default answer; also works when lists arrive as streams |
| pairwise | optimal | O(N log k) | O(k) | no heap available, or to reuse the two-list merge |

`N` is the total number of nodes and `k` the number of lists. Both optimal approaches make every node pass through about `log k` comparisons; they differ in whether a heap or a merge tree does the selecting.

## Approach: one-by-one (Merge the lists into the result one at a time)

### Intuition

You already know how to merge two sorted lists. Start with an empty result and merge each input list into it, one after another.

### Algorithm

1. Set `merged = null`.
2. For each list in `lists`, set `merged` to the two-list merge of `merged` and that list.
3. Return `merged`.

### Correctness

Invariant: after processing `i` lists, `merged` is a sorted list of exactly their nodes. Merging two sorted lists yields a sorted list of their union, so merging the next list keeps the invariant. After all `k` lists, `merged` holds every node in sorted order.

### Complexity

- Time: O(k N) — the `i`-th merge walks the whole result built so far, so the early nodes are walked up to `k` times. With `k` lists of `N / k` nodes, the total is about `k N / 2`; in the generated cases `k = N / 10`, which makes it quadratic in `N`.
- Space: O(1) — merging relinks nodes; only a dummy node per merge is allocated.

### Trade-offs

The shortest correct answer and a fine oracle, and for two or three lists it is as good as anything. With many short lists the result is re-walked over and over: 1000 lists of 10 nodes cost about 5 * 10^6 steps instead of about 10^5.

### Pitfalls and edge cases

- An empty `lists` array returns null without merging anything.
- Starting with the first list as `merged` instead of null works too, but then the empty array needs its own check.

### Language notes

- Kotlin: `lists.fold(null as ListNode?) { ... }` threads the result through the merges; the cast gives the accumulator its nullable type.
- Rust: `lists.into_iter().fold(None, merge)` threads the merged list through the merges and consumes the input. `merge` moves one node at a time (`tail = tail.next.insert(node)`) and appends what is left of either list with `left.or(right)`.

## Approach: min-heap (Min-heap of the k front nodes)

### Intuition

The next node of the result is the smallest of the current fronts. A min-heap holding one front per non-empty list returns that smallest front in O(1) and replaces it with its successor in O(log k).

### Algorithm

1. Push the head of every non-empty list into a min-heap ordered by value.
2. While the heap is not empty:
   1. Pop the smallest node and append it to the result.
   2. If it has a successor, push the successor.
3. Return the result's head.

### Correctness

Invariant: the heap holds exactly the front node of every list that still has unmerged nodes. Each list is sorted, so its front is its smallest remaining value, and the heap's minimum is therefore the smallest remaining value overall; appending it keeps the result sorted. Pushing the popped node's successor restores the invariant for that list. The loop ends when every list is used up, so every node is appended exactly once.

### Complexity

- Time: O(N log k) — each of the N nodes is pushed and popped once, and the heap never holds more than `k` nodes.
- Space: O(k) — the heap; the result reuses the input nodes.

### Trade-offs

The standard answer, and the one that generalizes: it works on `k` streams that are read lazily (external sorting, merging sorted log files). It needs a priority queue, which TypeScript lacks, and every operation carries the heap's overhead. The pairwise approach reaches the same bound with only the two-list merge.

### Pitfalls and edge cases

- Skip null heads when filling the heap; pushing null breaks the ordering in most languages.
- Ties: when two fronts are equal, any order is fine for the result, but some heaps cannot compare the payloads (see the Python note).

### Language notes

- Python: `heapq` is a min-heap over tuples. A tuple `(value, node)` would compare the nodes when two values are equal and raise `TypeError`, so the reference stores `(value, list index, node)`; indexes are distinct and break every tie. `heapreplace` pops and pushes in one sift.
- TypeScript: there is no built-in priority queue, so the reference includes a small binary heap with `push` (sift up) and `pop` (move the last element to the root and sift down).
- Java: `PriorityQueue<ListNode>` with `Comparator.comparingInt(node -> node.val)`; `poll` returns the smallest. Comparing with a subtraction lambda (`a.val - b.val`) is a classic overflow bug for large values.
- Kotlin: the same `java.util.PriorityQueue` with ``compareBy { it.`val` }``; `filterNotNullTo(heap)` fills it with the non-null heads, and `node.next?.let(heap::offer)` pushes a successor only when there is one.
- Go: `container/heap` works on any type that implements `Len`, `Less`, `Swap`, `Push` and `Pop`, so the reference declares a `nodeHeap` slice type. `Less` compares plain integers, so unlike Python's tuples it needs no tie-breaking index. Overwriting the root and calling `heap.Fix(&heads, 0)` is Python's `heapreplace`.
- Rust: `BinaryHeap` is a max-heap, so entries are wrapped in `Reverse`. A `Box<ListNode>` has no ordering, so the heap holds `(value, list index)` pairs, the index breaks ties as in Python, and the nodes stay in `lists`. `peek_mut` plus an assignment replaces the root and sifts it down when the guard drops (`heapreplace`); `PeekMut::pop` removes an exhausted list.

## Approach: pairwise (Merge neighbouring lists in rounds)

### Intuition

Merging one list at a time builds a lopsided merge tree: early nodes take part in up to `k` merges. Merge in a balanced tree instead: pair the lists up and merge each pair, then pair up the results, and so on. Every node takes part in only one merge per round, and there are about `log2 k` rounds.

### Algorithm

1. If `lists` is empty, return null.
2. While more than one list remains, replace the lists by the merges of neighbouring pairs (the last list passes through alone when the count is odd).
3. Return the remaining list.

### Correctness

Each round replaces sorted lists by sorted merges of disjoint pairs, so after every round the lists still hold every node exactly once and each list is sorted. The number of lists halves (rounding up) each round, so the loop ends with one sorted list of all nodes.

### Complexity

- Time: O(N log k) — a round walks every node once across all its merges, and there are `ceil(log2 k)` rounds.
- Space: O(k) — the array of heads for the next round; merges relink nodes in place.

### Trade-offs

Same bound as the heap, built from the simplest list routine, and often faster in practice because a merge does one comparison per node with no heap bookkeeping. It needs all lists up front, so it does not suit streams. Reusing the input array instead of allocating a new one per round brings the extra memory down to O(1).

### Pitfalls and edge cases

- With an odd number of lists, the last one must be carried into the next round, not dropped.
- The empty input array needs an explicit check before reading the first head.

### Language notes

- Python: a list comprehension builds the next round; `heads[index + 1] if ... else None` handles the odd one out.
- Kotlin: `chunked(2) { pair -> ... }` groups neighbours and transforms each group in one call; `pair.getOrNull(1)` is null for a lone last list.
- Java: the next round's array has `(length + 1) / 2` slots, the integer form of `ceil(length / 2)`.
- Rust: `heads.into_iter()` is consumed two items at a time with `pending.next()` and `pending.next().flatten()`, which turns a missing partner into an empty list, and `Vec::with_capacity(heads.len().div_ceil(2))` sizes the next round.
