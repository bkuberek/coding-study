# Count Smaller Numbers After Self: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| compare-every-pair | brute | O(n^2) | O(1) | short arrays, or as a correctness oracle |
| fenwick-ranks | optimal | O(n log n) | O(n) | default answer: compact code once ranks are known |
| merge-sort-counts | optimal | O(n log n) | O(n) | no tree wanted; also counts inversions in general |

Space counts memory beyond the output array. Both optimal approaches answer "how many smaller values lie to the right" for all positions together: one by scanning right to left with a frequency tree over value ranks, the other by sorting and counting the smaller values that cross over during each merge.

## Approach: compare-every-pair (Compare each value with everything to its right)

### Intuition

Apply the definition: for each position, look at every later position and count the strictly smaller values.

### Algorithm

1. For each `i`, count the `j > i` with `nums[j] < nums[i]`.
2. Return the counts.

### Correctness

Each count is computed directly from its definition, over exactly the positions to the right.

### Complexity

- Time: O(n^2) — n(n - 1)/2 comparisons.
- Space: O(1) — beyond the output, one counter.

### Trade-offs

Obvious and a good oracle, but quadratic: at `n = 10^5` it would be 5 * 10^9 comparisons.

### Pitfalls and edge cases

- Strictly smaller: equal values to the right do not count (`[5, 5]` gives `[0, 0]`).

## Approach: fenwick-ranks (Fenwick tree over value ranks, scanning from the right)

### Intuition

Scan from right to left. At position `i`, the values already seen are exactly the values to the right of `i`, so the answer is "how many seen values are smaller than `nums[i]`". If values were small integers, a Fenwick tree indexed by value would keep their frequencies and answer that as a prefix sum. They are not small, but only their order matters, so replace each value by its rank among the distinct values (coordinate compression): ranks run from 1 to the number of distinct values.

### Algorithm

1. Sort the distinct values; the rank of a value is its 1-based position in that list.
2. Create a Fenwick tree of frequencies over ranks, all zero.
3. For `i` from `n - 1` down to 0:
   1. Let `r` be the rank of `nums[i]`.
   2. `counts[i] = prefix(r - 1)`, the number of seen values with a smaller rank.
   3. Add 1 at rank `r`.
4. Return `counts`.

### Correctness

Invariant: before processing position `i`, the tree holds the rank frequencies of `nums[i + 1..n - 1]`. A value is strictly smaller than `nums[i]` exactly when its rank is smaller than `r`, because ranks preserve order and equal values share a rank. So `prefix(r - 1)` counts exactly the strictly smaller values to the right. Step 3.3 then adds `nums[i]`, restoring the invariant for `i - 1`.

### Complexity

- Time: O(n log n) — sorting for the ranks, then one prefix query and one update of O(log n) each per position.
- Space: O(n) — the ranks (a map or the sorted distinct values) and the tree.

### Trade-offs

Short once the Fenwick tree is familiar, and it generalizes to "count values in a range to the right" or online variants. It needs the compression step when values are large or negative; with small bounded values (say within 10^4) an offset array index works directly.

### Pitfalls and edge cases

- Query `prefix(r - 1)`, not `prefix(r)`: the latter also counts equal values.
- Compress over the distinct values, so duplicates share one rank.
- Indexing the tree by raw value would need two billion slots here; ranks need at most `n`.

### Language notes

- Python: `{value: rank for rank, value in enumerate(sorted(set(nums)), start=1)}` builds the rank map in one expression.
- TypeScript: sort the distinct values with a numeric comparator (`(a, b) => a - b`); the default sort compares strings, which misorders negative and multi-digit numbers.
- Java: `Arrays.stream(nums).distinct().sorted().toArray()` and `Arrays.binarySearch` find a rank in O(log n) without a hash map.
- Kotlin: `nums.distinct().sorted().toIntArray()` and `IntArray.binarySearch` do the same.

## Approach: merge-sort-counts (Merge sort that counts the smaller values crossing over)

### Intuition

Sort the positions by value with merge sort. While merging a left run with the right run that follows it, every element of the right run is to the right of every element of the left run. When a left element is placed, the right-run elements already placed are exactly the right-run values smaller than it, so add their number to its count. Across all merges, every pair `i < j` with `nums[j] < nums[i]` is counted once, in the merge where `i` and `j` first meet in different runs.

### Algorithm

1. Start with `order = [0, 1, ..., n - 1]` and all counts 0.
2. For run widths 1, 2, 4, ...: merge each pair of adjacent runs `[low, middle)` and `[middle, high)` of `order`, by value:
   1. If the next right element is strictly smaller than the next left element, place it.
   2. Otherwise place the left element and add `right - middle` (the right elements placed so far) to its count.
   3. Copy whatever is left of the right run.
3. Return the counts.

### Correctness

A run at width `w` always holds the positions of one contiguous index block, sorted by value, so the two runs of a merge hold the left block and the right block. When a left element `x` is placed, the right elements placed before it are those with a value strictly smaller than `x` (ties place the left element first), and they are all to its right in the array. Every pair `i < j` lies in different runs at exactly one merge level, the first one where their blocks are merged, so each smaller-to-the-right pair adds 1 to `counts[i]` exactly once.

### Complexity

- Time: O(n log n) — `log2 n` levels of merging, each O(n).
- Space: O(n) — the index array and the merge buffer.

### Trade-offs

Needs no compression and no tree, only a careful merge, and it is the classic inversion-counting algorithm. It moves positions rather than values so the counts can be attributed to the original indexes, which is the step people most often forget. The bottom-up form used here avoids recursion entirely.

### Pitfalls and edge cases

- Ties must place the left element first (strict `<` for taking the right element); otherwise equal values are counted as smaller.
- Sort positions, not values, so that `counts[order[left]]` updates the original index.
- Swap the buffer and the index array after each level instead of copying back.

### Language notes

- Python: list slicing copies the remaining right run in one step; the bottom-up loop avoids Python's recursion overhead.
- TypeScript: `Int32Array` buffers hold positions compactly; destructuring swaps the two arrays.
- Java: plain `int[]` arrays swapped by reference after each level.
- Kotlin: `order = buffer.also { buffer = order }` swaps the two arrays in one expression.
