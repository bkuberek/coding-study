# Combination Sum: Explanation

## Overview

In the bounds below, n is the number of candidates, t the target and m the smallest candidate, so t/m bounds how many values one combination can hold.

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| include-or-skip | intermediate | O(2^(n + t/m)) | O(n + t/m) | you want the simplest correct recursion, with no sorting |
| sorted-pruning | optimal | O(n^(t/m + 1)) | O(n + t/m) | default answer: sorting lets every loop stop at the first overshoot |

Both are backtracking over the same choices. The duplicates problem ([2, 3] versus [3, 2]) is avoided the same way in both: values are only ever added in one fixed order of the candidates, so each multiset has exactly one construction path.

## Approach: include-or-skip (Use the current candidate again or move past it)

### Intuition

Look at the candidates one at a time. For the current one there are only two moves: put one more copy of it into the combination (and stay on it, because it may repeat), or decide never to use it again and move to the next candidate. A combination is a sequence of these moves that ends with the remaining sum at exactly 0.

### Algorithm

1. `explore(index, remaining)` with a shared list `chosen`:
   1. If `remaining == 0`, record a copy of `chosen` and return.
   2. If `remaining < 0` or `index == n`, return: this path cannot succeed.
   3. Append `candidates[index]`, call `explore(index, remaining - candidates[index])`, then pop it.
   4. Call `explore(index + 1, remaining)`.
2. Start with `explore(0, target)`.

### Correctness

Every combination is a choice of a count `k_i >= 0` for each candidate `i`. The recursion produces each count vector in exactly one way: it takes candidate `i` exactly `k_i` times (step 3 repeated) and then moves past it (step 4), in index order. Paths are recorded only when the sum is exactly `target`, so every recorded list is a valid combination, and two different paths differ in some count, so no combination is recorded twice. Paths are cut only when the sum already exceeds the target or no candidates remain, and neither can lead to a valid combination, since all values are positive.

### Complexity

- Time: O(2^(n + t/m)) — along any path the index advances at most n times and a value is taken at most t/m times before the sum passes the target (one more step overshoots), so the binary recursion tree has depth at most n + t/m + 1. Copies at the leaves are bounded by the at most 150 combinations of at most t/m values.
- Space: O(n + t/m) — the recursion depth is at most n + t/m + 1 and `chosen` holds at most t/m values; the answer itself is at most 150 lists of at most t/m values.

### Trade-offs

Very little to get wrong, which makes it the oracle. It does not use the order of the values, so it only notices an overshoot after taking the value, and it walks past every remaining candidate (each a skip step) even when all of them are too large. Sorting and a loop with an early exit remove both costs.

### Pitfalls and edge cases

- After taking a value, recurse with the same index; recursing with `index + 1` forbids repeats and solves a different problem.
- Check `remaining == 0` before the "out of candidates" test, so a combination that finishes on the last candidate is still recorded.
- Copy `chosen` when recording it.

### Language notes

- Python: a nested function closes over `candidates`, `result` and `chosen`; the recursion depth is at most about 50.
- TypeScript: `[...chosen]` copies on success.
- Java: passing `chosen` and `result` explicitly keeps the helper free of fields; `remove(chosen.size() - 1)` removes by index.
- Kotlin: a local `fun` recursion; `removeAt` removes by index and avoids the `remove(element)` overload.

## Approach: sorted-pruning (Loop over sorted candidates and stop at the first that overshoots)

### Intuition

Build each combination in non-decreasing order of its values. At each step, pick the next value from the candidates at or after the last one used (repeats allowed, earlier ones forbidden). With the candidates sorted, as soon as one candidate is larger than what remains, all later ones are too, so the loop can stop right there instead of trying them.

### Algorithm

1. Sort a copy of `candidates` ascending.
2. `extend(start, remaining)` with a shared list `chosen`:
   1. If `remaining == 0`, record a copy of `chosen` and return.
   2. For `i` from `start` while `ordered[i] <= remaining`: append `ordered[i]`, call `extend(i, remaining - ordered[i])`, then pop it.
3. Start with `extend(0, target)`.

### Correctness

Each combination, written in non-decreasing order, is one sequence of loop choices: its first value at some index `i_1`, its second at `i_2 >= i_1`, and so on, so it is produced exactly once. Every recorded sequence sums to `target`. The loop break skips only candidates larger than the remaining sum; since the list is sorted, every later candidate is at least as large, and adding any of them would overshoot because all values are positive. No valid combination is lost.

### Complexity

- Time: O(n^(t/m + 1)) — the recursion depth is at most t/m, because every level adds at least m to the sum; each node loops over at most n candidates, so the tree has O(n^(t/m)) nodes and does O(n) work per node. Sorting costs O(n log n) once. In practice the break cuts most of the loop.
- Space: O(n + t/m) — the sorted copy holds n values; the recursion depth and `chosen` hold at most t/m; the answer is at most 150 combinations.

### Trade-offs

The standard interview answer: one loop per level and a sorted array make the pruning both cheap and obviously safe. Its worst-case bound is no better in theory than the include-or-skip bound on every input, but on real inputs it explores far fewer dead ends. If only the number of combinations were needed, a dynamic-programming table of ways per sum would answer in O(n * t) without listing anything.

### Pitfalls and edge cases

- Recurse with `i`, not `start` and not `i + 1`: `start` re-allows earlier candidates (duplicate orderings), `i + 1` forbids repeats.
- The break is valid only after sorting; on unsorted input it would skip larger-index candidates that are still small enough.
- A target smaller than every candidate gives an empty answer, not `[[]]`; only `target == 0` would make the empty combination valid, and the constraints exclude it.

### Language notes

- Python: `sorted(candidates)` copies, leaving the input untouched.
- TypeScript: `[...candidates].sort((a, b) => a - b)` sorts numerically; the default `sort()` compares strings and would put 10 before 9.
- Java: `candidates.clone()` then `Arrays.sort` sorts the primitive copy; the loop condition carries the break.
- Kotlin: `candidates.sorted()` returns a sorted `List<Int>`; `break` inside the `for` loop stops it as in Java.
