# Split Array Largest Sum: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| prefix-dp | brute | O(k * n^2) | O(n) | the cost function is not a plain sum (for example it changes per piece), or as a correctness oracle |
| search-the-limit | optimal | O(n log s) | O(1) | default answer |

`n` is the length of `nums` and `s` its sum.

## Approach: prefix-dp (Dynamic programming over prefixes and part counts)

### Intuition

Look at the last piece of an optimal cut of the first `i` elements into `j` pieces: it is some run `nums[c..i-1]`, and everything before it, `nums[0..c-1]`, is cut into `j - 1` pieces as well as possible. So the best cost for `(j, i)` is the minimum over all cut points `c` of `max(best cost for (j - 1, c), sum of nums[c..i-1])`. Prefix sums make every piece sum O(1).

### Algorithm

1. Build `prefix` with `prefix[i] = nums[0] + ... + nums[i - 1]`.
2. For one piece, `best[i] = prefix[i]`.
3. For `pieces = 2..k`, build a new row: for each `end` from `pieces` to `n`, `next[end] = min over cut in [pieces - 1, end - 1] of max(best[cut], prefix[end] - prefix[cut])`. Replace `best` with `next`.
4. Return `best[n]`.

### Correctness

By induction on `pieces`, `best[i]` is the smallest cost of cutting the first `i` elements into exactly `pieces` non-empty pieces. For one piece it is the whole prefix sum. For more pieces, every valid cut has a last piece starting at some `cut` with `pieces - 1 <= cut <= end - 1` (each earlier piece needs at least one element, and the last piece too), its cost is the larger of the earlier pieces' cost and the last piece's sum, and the earlier part is best cut optimally because `max` is monotone. Taking the minimum over all `cut` covers every valid cut.

### Complexity

- Time: O(k * n^2) — k - 1 rows, each with up to n entries that scan up to n cut points. The generator keeps k between 5 and 10, so the measured growth is quadratic in n.
- Space: O(n) — the prefix sums and two rows of the table.

### Trade-offs

It is the natural first correct solution and generalizes to cost functions that binary search cannot handle (for instance, minimizing the sum of squared piece sums). For this problem it is far slower than the binary search: at n = 1000 and k = 50 it does about 2.5 * 10^7 steps against about 3 * 10^4.

### Pitfalls and edge cases

- Restrict `cut` to `[pieces - 1, end - 1]`; allowing smaller cuts would create empty pieces, which the problem forbids.
- Zeros are allowed, so several pieces can have sum 0; the recurrence handles them like any other value.
- `prefix[n]` is at most 10^9, which fits in a 32-bit `int`.

### Language notes

- Python: the inner minimum is a generator expression inside a list comprehension, which keeps the hot loop in fewer bytecodes; it is still pure Python and the slowest of the four.
- TypeScript: `Infinity` is a safe initial minimum because every candidate is a finite number.
- Java: `Integer.MAX_VALUE` as the initial minimum is safe because the range of `cut` is never empty for `end >= pieces`.
- Kotlin: `IntArray(n + 1) { end -> ... }` builds each row with an initializer, and `(pieces - 1 until end).minOf { ... }` expresses the minimum over cut points.

## Approach: search-the-limit (Binary search on the largest sum with a greedy check)

### Intuition

Fix a limit `L` and ask whether `nums` can be cut into at most `k` pieces whose sums are all at most `L`. Packing greedily from the left (extend the current piece while it fits, otherwise start a new one) uses the fewest pieces for that limit. A larger limit never needs more pieces, so feasibility is false for small `L` and true from some point on: the answer is that turning point, found by binary search between `max(nums)` and `sum(nums)`.

### Algorithm

1. Set `low = max(nums)` (no piece can be cheaper than its largest element) and `high = sum(nums)` (one piece always works).
2. While `low < high`:
   1. Let `limit = (low + high) / 2`, rounded down.
   2. Count the greedy pieces for `limit`: start with one piece and a running sum of 0; for each value, if adding it would exceed `limit`, start a new piece containing just it, otherwise add it.
   3. If the count is at most `k`, set `high = limit`; otherwise set `low = limit + 1`.
3. Return `low`.

### Correctness

Greedy is optimal for a fixed limit: by an exchange argument, any valid cut can be shifted so that each of its pieces ends no earlier than the corresponding greedy piece, without adding pieces, so greedy never uses more pieces than any valid cut. If greedy needs at most `k` pieces, exactly `k` pieces also work: split pieces further (there are `n >= k` elements), which never increases a piece sum. So "the minimum cost is at most `L`" is equivalent to "greedy needs at most `k` pieces for `L`", a monotone predicate, and the half-open binary search returns its smallest true value, which is the answer. Every value is at most `limit` because `limit >= max(nums)`, so a new piece always fits its first element.

### Complexity

- Time: O(n log s) — about log2(s - max) iterations, each a linear greedy pass; with s at most 10^9 that is at most about 30 passes.
- Space: O(1) — the bounds, a counter and a running sum.

### Trade-offs

This is the expected answer: short, fast, and an instance of the same "binary search on the answer" pattern as `koko-eating-bananas`. It depends on two properties of the problem (piece costs are sums of non-negative values, and the objective is the maximum), so it does not transfer to arbitrary cost functions the way the DP does.

### Pitfalls and edge cases

- Start `low` at `max(nums)`, not 0 or 1: with a smaller limit, a single large element can never fit, and the greedy count is meaningless.
- `running + value > limit` must be strict: a piece whose sum equals the limit is allowed.
- `k == n` gives `max(nums)`; `k == 1` gives `sum(nums)`. Both fall out of the search.
- The sum fits in 32 bits here (at most 10^9); with larger values, Java and Kotlin would need `long` bounds.

### Language notes

- Python: `max` and `sum` compute the bounds in C; the greedy check is a plain loop.
- TypeScript: one loop computes both bounds; `Math.floor((low + high) / 2)` is exact because the sum stays far below 2^53.
- Java: `low + (high - low) / 2` avoids overflow when both bounds are near 10^9.
- Kotlin: `nums.max()` and `nums.sum()` give the bounds; the midpoint uses the same overflow-safe form as Java.
