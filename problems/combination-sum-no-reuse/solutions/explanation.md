# Combination Sum Without Reuse: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| dedupe-with-set | brute | O(n * 2^n) | O(n * 2^n) | tiny inputs, or to cross-check a cleverer search |
| skip-equal-siblings | optimal | O(n * 2^n) | O(n * 2^n) | default answer: prunes by the remaining sum and never builds a duplicate |

The worst cases match (all entries distinct and small enough that almost every subset stays under the target), but on typical inputs the backtracking explores only subsets whose sum stays within the target and produces each combination once. With the target at most 30, that worst case needs n distinct entries totalling at most 30, so it exists only up to n = 7 (1 + 2 + ... + 7 = 28) and nearly so at 8 and 9; the size ladder stops at 9, and on longer arrays the target, not n, bounds the search.

## Approach: dedupe-with-set (Try every subset of entries and keep each distinct sorted match)

### Intuition

"Each entry at most once" means a combination is a subset of positions. There are only 2^n of them, so try all, keep those that sum to the target, and remove repeats by writing each match in sorted order and storing it in a set.

### Algorithm

1. Sort the candidates.
2. For each mask from 0 to 2^n - 1, collect `ordered[i]` for the set bits `i` (in index order, hence sorted) and its sum.
3. If the sum equals the target, add the tuple to a set.
4. Return the set's tuples as lists.

### Correctness

Every way to use each entry at most once is some position subset, so every valid combination is generated at least once. Sorting makes the tuple of a position subset a canonical form of its multiset, so equal combinations map to equal tuples and the set keeps exactly one of each. Only subsets whose sum is the target are added.

### Complexity

- Time: O(n * 2^n) — 2^n masks, each building a tuple and its sum in O(n), plus O(n) hashing for the matches.
- Space: O(n * 2^n) — the set holds at most one tuple per distinct matching subset, at most 2^n of them, each of at most n values.

### Trade-offs

Obviously correct and short, so it is the oracle. It ignores the target while generating: fifteen 1s with target 5 produce 32,768 subsets, 3,003 of which match, to report a single combination. The backtracking cuts both the overshooting branches and the duplicate ones.

### Pitfalls and edge cases

- Sort before building tuples, or `(1, 4)` and `(4, 1)` are stored as different combinations.
- The empty mask sums to 0, which never equals a positive target, so it is never reported.

### Language notes

- Python: tuples are hashable and compare by content, so a `set` of tuples dedupes them.
- TypeScript: a `Map` keyed by `chosen.join(",")` dedupes, since arrays compare by identity.
- Java: `HashSet<List<Integer>>` works because `List` defines content-based `equals` and `hashCode`.
- Kotlin: `filterIndexed` builds each subset; `List<Int>` content equality lets a `LinkedHashSet` dedupe.
- Go: a map key must be comparable and a slice is not, so the reference keys a `map[string][]int` by the combination's text (each value followed by a comma, built with `strconv.AppendInt`), like the TypeScript key. A repeated key just overwrites an identical combination.
- Rust: `Vec<i32>` implements `Hash` and `Eq` by content, so `HashSet<Vec<i32>>` dedupes directly, as Python's set of tuples does; the closure that builds each subset names its return type (`-> Vec<i32>`) so `collect()` knows what to build before the `filter`. The sum fits `i32` easily (at most 15 values of 30).

## Approach: skip-equal-siblings (Backtrack over sorted entries, skipping equal siblings and overshoots)

### Intuition

Sort, then grow a combination by choosing the next entry among the positions after the last one used, which enforces "at most once" by construction. Two cuts make it fast. Once an entry is larger than what remains, so is every later entry, so the loop stops. And at one level, trying a second copy of a value after its first copy would rebuild the same combinations, so it is skipped; the next level may still take it.

### Algorithm

1. Sort the candidates into `ordered`.
2. `extend(start, remaining)` with a shared list `chosen`:
   1. If `remaining == 0`, record a copy of `chosen` and return.
   2. For `i` from `start` while `ordered[i] <= remaining`: skip `i` if `i > start` and `ordered[i] == ordered[i - 1]`; otherwise append `ordered[i]`, call `extend(i + 1, remaining - ordered[i])`, and pop it.
3. Call `extend(0, target)` and return the result.

### Correctness

Each distinct combination, written in sorted order, corresponds to exactly one path: at every level, its next value must be taken from the leftmost remaining copy of that value, because the skip rule rejects every later copy at the same level. Recursing with `i + 1` uses each entry at most once, while a deeper level can still take the next copy of a value, so combinations such as `[1, 1, 3]` remain reachable. The loop break discards only entries larger than the remaining sum; all later entries are at least as large, and adding a positive value can never bring an overshooting sum back to the target.

### Complexity

- Time: O(n * 2^n) — the recursion only visits position subsets in canonical form, at most 2^n nodes, each looping over at most n entries; copies at the leaves cost O(n) each.
- Space: O(n * 2^n) — the answer can hold up to 2^n combinations; the recursion depth, `chosen` and the sorted copy add O(n).

### Trade-offs

Faster in practice by orders of magnitude, and it never needs a set. The two cuts must be applied in the right order and with the right condition (see the pitfalls), so it is easy to write a version that loses or repeats combinations. Compared with Combination Sum, the only changes are `i + 1` instead of `i` in the recursion and the skip rule for repeated values.

### Pitfalls and edge cases

- Compare with `i > start`, not `i > 0`: the latter also forbids taking a second copy at a deeper level and loses combinations like `[6, 6]`.
- Recurse with `i + 1`; recursing with `i` lets one entry be used repeatedly.
- The loop break needs the sorted order.

### Language notes

- Python: `sorted(candidates)` copies before the search; `chosen.copy()` snapshots each match.
- TypeScript: sort with a numeric comparator; the loop condition carries the overshoot break.
- Java: comparing `ordered[i] == ordered[i - 1]` on primitive `int` values avoids boxed `Integer` identity comparison.
- Kotlin: `break` and `continue` work inside a `for` loop over `start until ordered.size`; `toList()` copies `chosen`.
- Go: `slices.Clone` plus `slices.Sort` sorts a copy, and `slices.Clone(chosen)` snapshots each match, because later appends reuse the same backing array. `break` and `continue` work as in Java.
- Rust: the function owns `candidates`, so it sorts that vector in place; the recursion shares one `chosen` buffer through `&mut Vec<i32>`, and `chosen.clone()` snapshots each match. `for i in start..ordered.len()` keeps the index for the `ordered[i - 1]` comparison and the recursive call.
