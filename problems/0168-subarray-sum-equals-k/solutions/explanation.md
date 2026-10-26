# Subarray Sum Equals K: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| every-start | brute | O(n^2) | O(1) | short arrays, or as a correctness oracle |
| prefix-count | optimal | O(n) | O(n) | default answer |

Negative values rule out a sliding window: extending a window can lower its sum, so there is no monotone rule for when to move either end. Prefix sums turn the question into counting pairs of equal-looking prefixes instead.

## Approach: every-start (Extend a running sum from every start)

### Intuition

Every subarray has a start and an end. For a fixed start, extending the end one position at a time updates the sum with one addition, so all subarrays with that start cost O(n) together, without re-adding anything.

### Algorithm

1. For every start `i`:
   1. Set `total = 0`.
   2. For every end `j` from `i` to `n - 1`, add `nums[j]` to `total`; if `total == k`, increment the count.
2. Return the count.

### Correctness

Every pair `(i, j)` with `i <= j` is visited exactly once, and at that moment `total` holds `nums[i] + ... + nums[j]` (invariant of the inner loop). The count therefore increases exactly once per subarray whose sum is `k`.

### Complexity

- Time: O(n^2) — n(n + 1)/2 pairs, one addition and comparison each.
- Space: O(1) — two loop indexes, a running total and the count.

### Trade-offs

Easy to get right and memory-free, which makes it the oracle. Recomputing every subarray sum from scratch would be O(n^3); the running total is what keeps it at O(n^2). It cannot stop early, because a later end may bring the sum back to `k` after negative values.

### Pitfalls and edge cases

- Do not break out of the inner loop when `total` passes `k`: with negative values it can come back down.
- Zeros produce many equal sums; the count can reach n(n + 1)/2 (all zeros with `k = 0`), about 2 * 10^8 here, which still fits in an `int`.

## Approach: prefix-count (Count earlier prefix sums in a hash map)

### Intuition

Write `prefix[t]` for the sum of the first `t` values. A subarray `nums[i..j]` adds up to `k` exactly when `prefix[j + 1] - prefix[i] == k`, that is, when an earlier prefix equals `prefix[j + 1] - k`. So, walking left to right, the number of good subarrays ending at `j` is the number of earlier prefixes with that value, which a hash map of prefix counts answers in O(1).

### Algorithm

1. Start a map `seen` with `{0: 1}` (the empty prefix) and `total = 0`, `count = 0`.
2. For each value:
   1. Add it to `total`.
   2. Add `seen[total - k]` (0 if absent) to `count`.
   3. Increment `seen[total]`.
3. Return `count`.

### Correctness

Invariant: before step 2.2 for position `j`, `seen` holds the counts of `prefix[0], ..., prefix[j]`, and `total` is `prefix[j + 1]`. Each earlier prefix `prefix[i]` with `prefix[i] = total - k` corresponds to exactly one subarray `nums[i..j]` with sum `k`, so step 2.2 adds the number of good subarrays ending at `j`. Step 2.3 then extends the invariant to `j + 1`. Summing over all `j` counts every good subarray exactly once. The lookup happens before the insertion, so the empty subarray (`i = j + 1`) is never counted, even when `k = 0`.

### Complexity

- Time: O(n) — one pass with O(1) average map operations per value.
- Space: O(n) — up to n + 1 distinct prefix sums in the map.

### Trade-offs

Linear and the expected interview answer. It trades O(n) memory for the quadratic time, and its hash map makes it slower per element than the brute force's tight loop, so the brute force wins on very short arrays. The same pattern (count earlier prefixes that complete the target) solves Continuous Subarray Sum with remainders and Count Downward Path Sums on a tree.

### Pitfalls and edge cases

- Seed the map with prefix sum 0 seen once; without it, subarrays that start at position 0 are missed.
- Look up `total - k` before recording `total`, or `k = 0` counts empty subarrays.
- The prefix sums here stay within 2 * 10^7 and `total - k` within 3 * 10^7, so `int` keys are safe; with larger values, use 64-bit sums.

### Language notes

- Python: `collections.Counter` returns 0 for a missing key without inserting it, which keeps lookups from growing the map (a `defaultdict(int)` would insert on every miss).
- TypeScript: `Map<number, number>` with `seen.get(x) ?? 0`; number keys compare by value.
- Java: `HashMap<Integer, Integer>` with `getOrDefault` and `merge(total, 1, Integer::sum)`; keys are boxed, and boxing is the main constant-factor cost.
- Kotlin: `HashMap<Int, Int>` with the index operator; `seen[x] ?: 0` handles the nullable lookup.
