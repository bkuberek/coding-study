# Subsets With Duplicates: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| dedupe-with-set | brute | O(n * 2^n) | O(n * 2^n) | quick to write; repeats are rare |
| skip-equal-siblings | optimal | O(n * 2^n) | O(n * 2^n) | default answer: never builds a duplicate in the first place |

Both sort first, so that equal values sit next to each other and a subset has one canonical sorted form. With d distinct subsets (d is at most 2^n, and equals 2^n only when all values differ), the brute force always pays for 2^n subsets while the backtracking pays for d.

## Approach: dedupe-with-set (Enumerate every subset of the sorted values and keep each once)

### Intuition

Generate all 2^n position subsets as in the plain Subsets problem and throw away repeats. Two position subsets give the same multiset exactly when, read in sorted order, they spell the same sequence of values, so the sorted tuple is a key that a hash set can deduplicate.

### Algorithm

1. Sort the values.
2. For each mask from 0 to 2^n - 1, build the tuple of `ordered[i]` for the set bits `i`, in index order, and add it to a set.
3. Return the set's tuples as lists.

### Correctness

Every multiset of values that `nums` can supply is produced by at least one mask (pick the first copies of each value it uses). Because `ordered` is sorted and indices are taken in increasing order, every tuple is sorted, so two masks produce equal tuples exactly when they describe the same multiset. The set therefore holds each distinct subset exactly once.

### Complexity

- Time: O(n * 2^n) — sorting is O(n log n); each of the 2^n masks builds a tuple of at most n values and hashes it in O(n).
- Space: O(n * 2^n) — the set holds up to 2^n tuples (exactly 2^n when no value repeats) of at most n values.

### Trade-offs

Easy to get right, which makes it the oracle, but it does the full 2^n work even when repeats make the answer tiny: ten copies of one value have only 11 distinct subsets, yet it builds 1024 and hashes them all. It also needs hashable keys, which is natural in Python and Java but needs a string key in TypeScript.

### Pitfalls and edge cases

- Sort before building the keys; without sorting, `[1, 3]` and `[3, 1]` hash differently.
- The empty subset (mask 0) belongs to the answer.

### Language notes

- Python: a set comprehension of tuples dedupes directly, since tuples hash by content and lists do not.
- TypeScript: arrays compare by identity, so the reference keys a `Map` by `subset.join(",")`; negative numbers keep their sign in the key, so keys stay unambiguous.
- Java: `List.equals` and `List.hashCode` are defined element by element, so a `HashSet<List<Integer>>` dedupes the lists.
- Kotlin: the same content equality for `List<Int>`; a `LinkedHashSet` keeps the insertion order, which makes the output easy to read.

## Approach: skip-equal-siblings (Backtrack over sorted values and skip equal siblings)

### Intuition

After sorting, build each subset by choosing the next value from positions after the last chosen one. Every node of that recursion is a subset. Duplicates appear only when, at the same node, two equal values are both tried as "the next value": both choices lead to identical subtrees. So at each node try each distinct value once, using its first copy, and let deeper levels take further copies.

### Algorithm

1. Sort the values into `ordered`.
2. `extend(start)` with a shared list `chosen`:
   1. Record a copy of `chosen`.
   2. For `i` from `start` to `n - 1`: skip `i` if `i > start` and `ordered[i] == ordered[i - 1]`; otherwise append `ordered[i]`, call `extend(i + 1)`, and pop it.
3. Call `extend(0)` and return the result.

### Correctness

Write a distinct subset in sorted order as `v_1 <= v_2 <= ... <= v_k`, and map it to the positions that take, for each value, its leftmost unused copy: the first copies of `v_1`, then the next copy, and so on. This is the only path the recursion can take to build it, because at each node the loop tries only the leftmost copy of each value among the remaining positions (the skip rule rejects every later copy at the same level). So each distinct subset is recorded exactly once, and the recursion never records anything else, since every node is a multiset of available values.

### Complexity

- Time: O(n * 2^n) — there is one recursion node per distinct subset, at most 2^n; each copies at most n values and loops over at most n positions.
- Space: O(n * 2^n) — the output holds at most 2^n subsets; the recursion depth and `chosen` add O(n).

### Trade-offs

Does work proportional to the answer instead of to 2^n, needs no hashing, and the same "skip equal siblings" rule removes duplicates in Combination Sum Without Reuse and in permutations of repeated values. The rule is easy to get subtly wrong (see the pitfalls), which is the main risk in an interview. An alternative with the same output bound groups equal values and, for a value with `k` copies, branches `k + 1` ways (take 0 to `k` copies).

### Pitfalls and edge cases

- The condition is `i > start`, not `i > 0`: comparing with the previous position across levels would forbid taking a second copy deeper down and lose subsets like `[3, 3]`.
- Sort first; the skip rule only recognizes equal values when they are adjacent.
- Record at every node (including the root, which is the empty subset), not only at leaves.

### Language notes

- Python: `sorted(nums)` leaves the input untouched; a nested function keeps the recursion local.
- TypeScript: sort numerically with `(a, b) => a - b`; the default sort compares strings and orders `-1` after `-10` incorrectly for this purpose.
- Java: comparing `int` values from the primitive array avoids `Integer` identity comparison, which would be wrong for values outside the small-integer cache.
- Kotlin: `nums.sorted()` returns a `List<Int>`; `==` on `Int` compares values.
