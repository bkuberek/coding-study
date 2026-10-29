# Sorted Insertion Cost: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| sorted-list | brute | O(n^2) | O(n) | n is up to about 10^5 and block moves are fast, or as a correctness oracle |
| fenwick-tree | optimal | O(n log m) | O(m) | default answer |

Here `m` is the largest value. The generator keeps it at most 4n, so the measured classes on the ladder are `n^2` and `n log n`.

## Approach: sorted-list (Sorted list with binary-search counts and insertion)

### Intuition

Keep the container literally sorted. Then two binary searches give both counts at once: the lower bound of `x` is the number of values smaller than `x`, and everything after the upper bound is larger.

### Algorithm

1. Keep a sorted list, empty at first.
2. For each value `x`: compute `less = lowerBound(x)` and `greater = size - upperBound(x)`.
3. Add `min(less, greater)` to the cost.
4. Insert `x` at position `upperBound(x)` (any position among equal values would do).
5. Return the total modulo `10^9 + 7`.

### Correctness

In a sorted list, the lower bound of `x` counts the values `< x` and the upper bound counts the values `<= x`, so `size - upperBound` counts the values `> x`. Inserting at the upper bound keeps the list sorted. The cost of each insertion is therefore exactly the one in the statement.

### Complexity

- Time: O(n^2) — each search is O(log n), but inserting into the middle of a list shifts O(n) elements.
- Space: O(n) — the sorted list.

### Trade-offs

Simple, and fast in practice because the shift is one block move of memory, but quadratic in the worst case: the standard library offers no sorted container with O(log n) positional insertion. It is a good oracle because it follows the statement literally.

### Pitfalls and edge cases

- The two searches use different comparisons: `<` for the lower bound and `<=` for the upper bound. Mixing them up counts equal values on the wrong side.
- Equal values cost nothing on their own side: they are neither smaller nor larger.

### Language notes

- Python: `bisect_left` and `bisect_right` are the two searches, and `list.insert` does the shift.
- TypeScript: hand-written lower and upper bound, and `splice(index, 0, x)` to insert; never sort the whole array again for every insertion.
- Java: an `ArrayList<Integer>` with a hand-written search and `add(index, x)`. Keep the total in a `long`, since a total near n^2 / 8 passes `Integer.MAX_VALUE` for large `n`.
- Kotlin: `ArrayList<Int>` and a `Long` total.

## Approach: fenwick-tree (Fenwick tree of counts by value)

### Intuition

Index a counting array by value: `count[v]` is how many times `v` has been inserted. The number of earlier values smaller than `x` is a prefix sum of that array, and so is the number of values at most `x`. A Fenwick tree keeps prefix sums under point updates in logarithmic time.

### Algorithm

1. Let `largest` be the maximum value and allocate a tree of size `largest + 1`.
2. For the `i`-th value `x` (counting from 0): `less = prefix(x - 1)` and `greater = i - prefix(x)`.
3. Add `min(less, greater)` to the cost, modulo `10^9 + 7`.
4. Add 1 at position `x` in the tree.
5. Return the cost.

### Correctness

`prefix(v)` counts the inserted values that are at most `v`. Of the `i` values already inserted, `prefix(x - 1)` are smaller than `x`, `prefix(x) - prefix(x - 1)` are equal to it, and the remaining `i - prefix(x)` are larger. So the two counts are exactly those of the statement.

### Complexity

- Time: O(n log m) — two prefix queries and one update per value, each O(log m).
- Space: O(m) — the tree, sized by the largest value.

### Trade-offs

It needs bounded values, or coordinate compression when they are large. A segment tree works the same way with more code. Unlike the sorted list, it never moves elements.

### Pitfalls and edge cases

- The tree is one-based, and the value itself is the index, so value 1 is index 1. Size it by the largest value present, not by `n`.
- Reduce modulo `10^9 + 7` while accumulating (or use a 64-bit total): the sum can pass the range of a 32-bit integer.

### Language notes

- Python: a list for the tree and a nested function for the prefix query; Python integers do not overflow.
- TypeScript: an `Int32Array` for the tree and a plain `number` for the cost, reduced at every step.
- Java: an `int[]` tree and a `long` cost reduced at every step; the final value is below the modulus, so the cast to `int` is safe.
- Kotlin: an `IntArray` tree, a `Long` cost, and a local function for the prefix query.
