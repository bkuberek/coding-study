# Cosine Top K: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| sort-all | brute | O(n m + n log n) | O(n) | the collection is small, or you need every score anyway |
| bounded-heap | optimal | O(n m + n log k) | O(k) | default answer |

`n` is the number of documents, `m` the length of a vector and `k` the number of results.

## Approach: sort-all (Score every document and sort them all)

### Intuition

Score every document, sort the scores best first with the tie-break, and keep the first `k`. It is short and obviously right, which makes it a good oracle for the heap.

### Algorithm

1. Compute the query's length. If it is zero, return an empty list.
2. For each document with a nonzero length, compute its cosine with the query and keep the pair (negated score, index).
3. Sort the pairs, which puts the best score first and equal scores by the lower index.
4. Return the indexes of the first `k` pairs.

### Correctness

Every document with a score gets exactly one pair, and documents with no score get none. Sorting by (negated score, index) is the order the statement asks for, so its first `k` entries are the answer, or all of them when fewer than `k` exist.

### Complexity

- Time: O(n m + n log n) — every document is read once to compute its score, and then `n` scores are sorted.
- Space: O(n) — one pair per scored document, held at once.

### Trade-offs

Simple and fast enough for a few thousand documents. It holds every score at once, and on a large collection that memory is the cost: the result needs only `k` of them. `cstudy bench` shows both costs. In TypeScript the sort was about 12 times slower than the heap at `n = 10^5` on one machine, with the gap growing with `n`, and the verdict names a likely extra log factor. In Python the sort runs in C and computing the scores dominates, so the gap was smaller, about 1.7 times, but the space line tells them apart: linear memory here, constant for the heap.

### Pitfalls and edge cases

- **Sorting by score alone.** It passes here only because both languages' sorts are stable and the scores were computed in index order. Once the work is split, merged or parallelized that order is gone, so the tie-break belongs in the key (`ex1`, `h1`).
- **Zero vectors.** Dividing by a zero length gives `NaN` in TypeScript and an exception in Python. Skip such documents, and return nothing for a zero query (`ex2`, `ex3`, `h3`).

## Approach: bounded-heap (Keep the k best in a min-heap whose root is the weakest of them)

### Intuition

To keep the best `k` of a stream, you only ever need to know the weakest one you are keeping: a new document either beats it and takes its place, or is thrown away. A min-heap of size `k` gives you that weakest one at its root, and replacing it costs `O(log k)`.

The subtle part is what "weakest" means with a tie-break. Among equal scores the lower index wins, so the higher index is the weaker one. The heap must be ordered by score and then by **negated** index, so that its root is the lowest score and, among those, the highest index. Documents arrive in index order, so a new document that ties the root never beats it, and the heap keeps the earlier one, as the tie-break requires.

### Algorithm

1. Compute the query's length. If it is zero, return an empty list.
2. For each document, in index order, compute its length; skip it when the length is zero. Otherwise compute its score.
3. While the heap holds fewer than `k` entries, push (score, -index).
4. Once it holds `k`, replace the root only when (score, -index) is greater than the root: a strictly higher score, since a tie with an earlier document loses.
5. Sort the entries best first and return their indexes.

### Correctness

Invariant: after each document, the heap holds the `min(k, s)` best documents among the `s` scored so far, under the total order (score descending, index ascending). It holds after zero documents. When the heap is not full, the new document is among the best and is pushed. When it is full, the root is the worst of the kept documents; if the new one beats the root, the root is no longer among the best `k` and the new one is, and otherwise the new one is not. At the end, the heap holds the best `k` of all scored documents, and the final sort orders them.

### Complexity

- Time: O(n m + n log k) — each document's score costs `O(m)`, and each push or replacement costs `O(log k)`; the final sort of `k` entries is within that.
- Space: O(k) — the heap holds at most `k` entries, and no score is kept for a document once it has been compared.

### Trade-offs

The heap reads the documents once and holds `k` entries, so it works on a stream that does not fit in memory, and on slices scanned by several workers: each keeps its own top `k`, and merging the slices' answers with the same order gives the global one. Quickselect also finds the best `k` in `O(n)` on average, but it needs all `n` scores in memory and has a quadratic worst case.

Be honest about what a benchmark can see: `n log n` and `n log k` share a time band, because a log factor adds too little to the growth curve to separate them by slope. `cstudy bench` judges the sort by its ratio to the heap instead. In TypeScript that ratio grows with `n`. In Python, where the dot products dominate both, the ratio stays a constant factor and the space line tells them apart: constant here, linear for sort-all.

### Pitfalls and edge cases

- **The wrong end of the heap.** A max-heap of everything is a sort in disguise. The root must be the weakest kept document, so that comparing with it decides whether a new one gets in.
- **The tie-break in the heap.** Ordering the heap by (score, index) makes the lower index the weaker of two equal scores, so it is evicted first and the result keeps the wrong documents (`h1`, `h8`, `h11`, `h12`, `h14`). Use (score, -index).
- **Replacing the root on a tie.** A new document with the root's score has a higher index, so it is the weaker one and must not get in (`h8`, `h11`).
- **Returning the heap's array.** Heap order is not sorted order; sort the `k` survivors best first (`h2`, `h13`).
- **The dot product instead of the cosine.** Without dividing by the lengths, a long vector wins by being long (`h6`). Dividing by the squared lengths, with the square root forgotten, punishes long vectors instead (`h7`).
- **Zero vectors.** Skip a zero document before it reaches the heap: a `NaN` compares false with everything and quietly breaks the heap's order (`ex2`, `h3`). A zero query returns nothing (`ex3`).
- **Negative and zero scores.** They are scores, and they are returned when `k` reaches them (`h5`, `h9`, `h14`).
- **Fewer than `k`.** Return what there is (`ex2`, `h4`).

### Language notes

- Python: `heapq` is a min-heap over tuples, so `(score, -index)` is the whole ordering, and `heapreplace` pops the root and pushes in one step. `math.sumprod` (Python 3.12 and later) computes a dot product in C.
- TypeScript: there is no built-in priority queue, so the reference writes a small binary heap with one comparison, `ranksBelow`, used for both sifting and the replacement test. The final `sort` needs an explicit comparator: by score descending, then index ascending.
