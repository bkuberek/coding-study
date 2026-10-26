# Top K Frequent Elements: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| sorting | intermediate | O(n log n) | O(n) | quickest to write; few distinct values |
| heap | optimal | O(n log k) | O(n) | k is much smaller than the number of distinct values, or values stream in |
| bucket | optimal | O(n) | O(n) | default answer for a fixed array |

All three start the same way: one pass with a hash map from value to count, O(n). They differ in how they pick the k largest counts among the d distinct values: a full sort, a bounded heap, or buckets indexed by count.

## Approach: sorting (Count, then sort the distinct values by count)

### Intuition

Once every value has a count, the answer is the first k values in order of decreasing count. Sorting the distinct values by count produces that order directly.

### Algorithm

1. Count each value with a hash map.
2. Sort the distinct values by count, highest first.
3. Return the first k of them.

### Correctness

After sorting, the first k values have the k highest counts. The constraints guarantee that the k-th highest count is strictly greater than the (k + 1)-th, so the set of the first k values does not depend on how the sort orders values with equal counts: every value with a count tied inside the answer is inside it, and every value left out has a strictly smaller count.

### Complexity

- Time: O(n log n) — counting is O(n); sorting d distinct values costs O(d log d), and d can be close to n.
- Space: O(n) — the count map and the sorted list of distinct values.

### Trade-offs

Short and obviously correct, which makes it the oracle. It orders all d values although only k are needed, which costs a log factor; with few distinct values (for example, small value ranges) that cost is negligible and this is the simplest choice.

### Pitfalls and edge cases

- Sort the distinct values, not `nums`: sorting the raw array by count repeats every value.
- Without the uniqueness guarantee, ties at the boundary would make several answers valid; the comparator would then need a checker.

### Language notes

- Python: `collections.Counter` counts in C; `sorted(counts, key=counts.__getitem__, reverse=True)` sorts the keys by count. `counts.most_common(k)` would use a heap internally instead.
- TypeScript: `[...counts.entries()].sort((a, b) => b[1] - a[1])` sorts `[value, count]` pairs numerically.
- Java: `Comparator.comparingInt(...).reversed()` sorts the boxed keys by count; the explicit `(Integer value)` parameter type is needed so that `reversed()` can infer the comparator's type.
- Kotlin: `nums.asIterable().groupingBy { it }.eachCount()` builds the count map in one call; `sortedByDescending`, `take` and `map` finish the job.

## Approach: heap (Count, then keep the k most frequent in a min-heap)

### Intuition

To keep the k largest counts seen so far, you only need to know the smallest of them: a new value either beats it and replaces it, or is not in the answer. A min-heap of at most k entries gives that smallest entry in O(1) and replaces it in O(log k).

### Algorithm

1. Count each value with a hash map.
2. For each distinct value `v` with count `c`:
   1. If the heap holds fewer than k entries, push `(c, v)`.
   2. Otherwise, if `c` is greater than the count at the heap's root, replace the root with `(c, v)`.
3. Return the values in the heap.

### Correctness

Invariant: after processing a prefix of the distinct values, the heap holds k values of that prefix (or all of them, while fewer than k were seen) and no value outside the heap has a strictly greater count than a value inside it. A new value whose count is not greater than the root's cannot belong among the k largest by strict count, and when its count is greater, replacing the root (the smallest count inside) restores the invariant. At the end, the heap holds k values none of which is beaten by an outside value; by the uniqueness guarantee those are exactly the answer.

### Complexity

- Time: O(n log k) — counting is O(n); each of the d ≤ n distinct values costs at most one O(log k) heap operation. With k at most 10 in the generated inputs, it grows linearly in n.
- Space: O(n) — the count map dominates; the heap holds at most k entries.

### Trade-offs

Better than sorting when k is much smaller than d, and the natural choice when values arrive as a stream: the heap never grows beyond k. For a fixed array, bucketing is linear and simpler. Interviewers often ask for this one because it shows heap fluency.

### Pitfalls and edge cases

- Use a min-heap, not a max-heap: a max-heap of all d entries works but costs O(d log d), the same as sorting.
- Push until the heap holds k entries before comparing with the root; comparing against an empty heap fails.
- Equal counts at the root are not replaced, which is correct here because the answer's boundary is strict.

### Language notes

- Python: `heapq` is a min-heap over plain lists. Tuples `(count, value)` order by count first; `heapq.heapreplace` pops the root and pushes the new entry in one O(log k) step.
- TypeScript: there is no built-in priority queue, so the reference implements a small binary heap with `push` (sift up) and `replaceRoot` (sift down). Sorting an array of k entries after every insertion would also be correct, at O(k log k) per update.
- Java: `PriorityQueue` is a min-heap; the comparator `Comparator.comparingInt(counts::get)` orders values by their counts. `heap.stream().mapToInt(Integer::intValue).toArray()` unboxes the result.
- Kotlin: the same `java.util.PriorityQueue`, built with `compareBy { counts.getValue(it) }`; `getValue` throws instead of returning null for a missing key, which keeps the comparator non-nullable.

## Approach: bucket (Count, then bucket the values by count)

### Intuition

A count is an integer between 1 and n. Instead of comparing counts, use them as array indexes: bucket `c` lists the values that occur exactly `c` times. Reading the buckets from `n` down to 1 visits values in order of decreasing count, with no sorting at all.

### Algorithm

1. Count each value with a hash map.
2. Create `n + 1` empty buckets.
3. Append each distinct value `v` to bucket `count(v)`.
4. Walk the buckets from `n` down to 1, appending their values to the answer, and stop once it holds k values.

### Correctness

Step 4 emits values in non-increasing order of count, because it reads buckets in decreasing order of index and bucket `c` holds exactly the values of count `c`. The first k values emitted are therefore k values with the highest counts, and by the uniqueness guarantee they are exactly the answer.

### Complexity

- Time: O(n) — counting is O(n), filling the buckets O(d), and the final walk visits n + 1 buckets plus at most d values.
- Space: O(n) — the count map and n + 1 buckets.

### Trade-offs

Linear and simple, the best answer for a fixed array. It allocates n + 1 buckets even when there are only a few distinct values, and it cannot handle a stream as gracefully as the heap. Quickselect on the distinct values is another O(n) average alternative, but it is harder to write correctly and degrades to O(d^2) in the worst case.

### Pitfalls and edge cases

- The buckets need indexes up to `n`, not `n - 1`: an array of one repeated value has count `n`.
- Stop exactly at k values; reading whole buckets can return too many values if a bucket straddles the boundary (impossible here, but common in variants without the guarantee).

### Language notes

- Python: `[[] for _ in range(n + 1)]` creates independent lists; `[[]] * (n + 1)` would share one list across all buckets.
- TypeScript: `Array.from({ length: n + 1 }, () => [])` creates independent arrays for the same reason.
- Java: a `List<List<Integer>>` of buckets; arrays of generic lists (`List<Integer>[]`) need an unchecked cast, so a list of lists is cleaner.
- Kotlin: `Array(n + 1) { mutableListOf<Int>() }` calls the initializer once per bucket; destructuring `for ((value, count) in counts)` iterates map entries.
