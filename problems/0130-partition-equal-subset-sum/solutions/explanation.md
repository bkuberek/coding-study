# Partition Equal Subset Sum: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| memoization | intermediate | O(n * t) | O(n * t) | you derive it top-down from the take-or-skip choice; it stops as soon as one subset is found |
| tabulation | intermediate | O(n * t) | O(n * t) | you want the full table, for example to rebuild the subset |
| one-row | optimal | O(n * t) | O(t) | default answer |

Here `t` is the target, half of the total (at most 100 * 200 / 2 = 10^4). The first observation removes the two-group framing: if the total is odd, no split exists; if it is even, a split exists exactly when some subset sums to `t`, because the other elements then sum to `t` as well. The problem becomes subset sum.

The naive recursion decides for each element whether it joins the subset, 2^n leaves for `n` elements, about 10^60 for 200 elements. It is the first step of the progression and is not a separate reference here. Its subproblems are described by just two numbers, the next element to decide and the sum still missing, and there are only `n * t` such pairs.

## Approach: memoization (Top-down take-or-skip on the remaining target)

### Intuition

Let `reachable(i, r)` mean "some elements of `nums[i..]` add up to exactly `r`". Element `i` is either taken, leaving `reachable(i + 1, r - nums[i])`, or skipped, leaving `reachable(i + 1, r)`. Many different choices over the first elements leave the same `(i, r)`, so caching the answer per pair avoids the exponential repetition.

### Algorithm

1. If the total is odd, return `false`; otherwise let `t` be half of it.
2. Define `reachable(i, r)`: `true` when `r == 0`; `false` when `i == n` or `r < 0`.
3. Otherwise return the cached value, or compute `reachable(i + 1, r - nums[i]) or reachable(i + 1, r)` and cache it.
4. Return `reachable(0, t)`.

### Correctness

By induction on `n - i`. With no elements left, only the empty sum 0 is reachable. Otherwise a subset of `nums[i..]` with sum `r` either contains `nums[i]`, and then the rest is a subset of `nums[i + 1..]` with sum `r - nums[i]`, or it does not, and then it is a subset of `nums[i + 1..]` with sum `r`. The two recursive calls cover both cases exactly. Negative remainders are unreachable because every value is positive.

### Complexity

- Time: O(n * t) — at most `n * (t + 1)` distinct pairs, each computed once with O(1) work besides the two calls.
- Space: O(n * t) — the cache, plus a recursion of depth at most `n`.

### Trade-offs

The short-circuiting `or` stops at the first subset found, so on splittable inputs it often explores only a small part of the table. On unsplittable inputs with an even total it can fill all of it, with the call overhead of recursion and, in Python, the memory of a dictionary keyed by tuples.

### Pitfalls and edge cases

- Check the parity of the total first; it answers half of all random inputs immediately and makes the target an integer.
- Cache `false` results too. Caching only successes leaves the exponential search in place on unsplittable inputs.
- A single element: the total is odd, or the target is `nums[0] / 2`, which no subset of one element reaches.

### Language notes

- Python: `functools.cache` keys on `(index, remaining)`.
- TypeScript: one `Uint8Array` per element holds three states (unknown, yes, no) in a byte each.
- Java: a `byte[][]` memo with the same three states; `Arrays.stream(nums).sum()` computes the total.
- Kotlin: `Array(n) { ByteArray(t + 1) }` and `nums.sum()`; the state constants are file-level `const val`s.

## Approach: tabulation (Table of reachable sums per prefix)

### Intuition

Build the answer for every prefix and every sum. Row `i` lists which sums some subset of the first `i` elements can make. Row `i` follows from row `i - 1`: a sum is reachable with element `i` available if it was already reachable without it, or if the sum minus that element was.

### Algorithm

1. If the total is odd, return `false`; otherwise let `t` be half of it.
2. Create `reach` with `n + 1` rows and `t + 1` columns, all `false`, and set `reach[0][0] = true`.
3. For each row `i` from 1 to `n` with value `v = nums[i - 1]`, and each `s` from 0 to `t`: `reach[i][s] = reach[i - 1][s] or (s >= v and reach[i - 1][s - v])`.
4. Return `reach[n][t]`.

### Correctness

By induction on `i`. Row 0 is right: the empty prefix reaches only 0. A subset of the first `i` elements with sum `s` either avoids element `i - 1`, and is then a subset of the first `i - 1` with sum `s`, or uses it, and the rest is a subset of the first `i - 1` with sum `s - v`. Step 3 is exactly that disjunction over the correct previous row.

### Complexity

- Time: O(n * t) — `n` rows of `t + 1` cells, each O(1).
- Space: O(n * t) — the whole table, up to 201 by 10001 booleans here.

### Trade-offs

Iterative and easy to check, so it is the oracle. Keeping every row lets you rebuild a subset: walk back from `reach[n][t]`, and whenever `reach[i - 1][s]` is `false`, element `i - 1` was used and `s` drops by its value. Without that need, the earlier rows are dead weight.

### Pitfalls and edge cases

- Read only from row `i - 1` in step 3. Reading the current row would let an element be used twice.
- The column range must include `t` itself, so allocate `t + 1` columns.

### Language notes

- Python: a list of lists built with a comprehension; `[[False] * (t + 1)] * (n + 1)` would alias one row `n + 1` times.
- TypeScript: `Array.from` with a factory creates an independent row per element.
- Java and Kotlin: `new boolean[n + 1][t + 1]` and `Array(n + 1) { BooleanArray(t + 1) }` are zero-initialized to `false`.

## Approach: one-row (Single row of reachable sums updated right to left)

### Intuition

Row `i` of the table depends only on row `i - 1`, and cell `s` reads only cells `s` and `s - v` of that row, both at or left of `s`. Updating one row in place from right to left reads each `reachable[s - v]` before this element has had a chance to change it, so the single row behaves like the previous row on the left and the new row on the right.

### Algorithm

1. If the total is odd, return `false`; otherwise let `t` be half of it.
2. Create `reachable` of length `t + 1`, all `false`, with `reachable[0] = true`.
3. For each value `v`, for `s` from `t` down to `v`: if `reachable[s - v]`, set `reachable[s] = true`. Return `true` early once `reachable[t]` is set.
4. Return `reachable[t]`.

### Correctness

Invariant: after processing a prefix of the elements, `reachable[s]` is `true` exactly when some subset of that prefix sums to `s`. Processing `v` from right to left reads `reachable[s - v]` while it still describes the prefix without `v` (indices below `s` are updated later in the same pass), so each new `true` corresponds to a subset that uses `v` once. Cells never turn back to `false`, which matches "already reachable without `v`".

### Complexity

- Time: O(n * t) — `n` passes over at most `t + 1` cells.
- Space: O(t) — one row.

### Trade-offs

The standard final answer: the same time as the table with a fraction of its memory, and it exits as soon as the target is reachable. It cannot rebuild the subset on its own. In Python, a big integer used as a bitset (`bits |= bits << v`) does the same pass in C and is much faster; the explicit loop is kept here because it reads the same in every language.

### Pitfalls and edge cases

- Iterate `s` downward. Iterating upward lets `reachable[s - v]`, set earlier in the same pass, feed `reachable[s]`, which uses `v` several times: that solves the unbounded problem (as in coin change), not this one.
- Stop the inner loop at `v`, not 0, so `s - v` never goes negative.

### Language notes

- Python: `range(t, v - 1, -1)` walks down to `v` inclusive.
- TypeScript and Java: a classic decreasing `for` loop over a boolean array.
- Kotlin: `for (s in target downTo value)` expresses the right-to-left pass directly.
