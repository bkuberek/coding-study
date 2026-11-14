# Coin Change Combinations: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| memoization | intermediate | O(k * amount) | O(k * amount) | deriving the recurrence; also the oracle |
| tabulation | optimal | O(k * amount) | O(k * amount) | the two-dimensional table makes the recurrence explicit |
| rolling-array | optimal | O(k * amount) | O(amount) | default answer |

Here k is the number of coin values. The state is (which coin values may still be used, which total remains); fixing an order of the coin values is what makes each combination appear exactly once. Recursion without a memo, choosing at each step "skip this value" or "use one more of it", explores every combination separately, and their number is the answer itself, up to 2^31 here; it is not among the references.

The time classes use the amount as n; the generated inputs have 5 to 25 coin values, so the work is linear in n.

## Approach: memoization (Recursion over coin index and remaining amount with a memo table)

### Intuition

Go through the coin values in a fixed order. For the current value there are two kinds of combinations: those that use none of it (move on to the next value) and those that use at least one (pay one coin and stay on the same value). The two kinds are disjoint, and they never count the same multiset twice, because each combination is decided value by value.

### Algorithm

1. Let `count(i, total)` be the number of combinations of `coins[i:]` that pay `total`.
2. If `total == 0`, return 1 (pay nothing). If `i == k`, return 0 (no values left).
3. Otherwise return `count(i + 1, total) + count(i, total - coins[i])`, the second term only when `coins[i] <= total`.
4. Cache the results; the answer is `count(0, amount)`.

### Correctness

State: `count(i, t)` is the number of multisets of values from `coins[i:]` summing to `t`. Recurrence: such a multiset either contains no copy of `coins[i]`, which makes it a multiset of `coins[i + 1:]` summing to `t`, or contains at least one copy, and removing one copy gives a multiset of `coins[i:]` summing to `t - coins[i]`; both maps are bijections, and the two groups are disjoint. Base cases: the empty multiset pays 0, and with no values left nothing positive can be paid. Each call decreases `total` or increases `i`, so the recursion terminates.

### Complexity

- Time: O(k * amount) — at most k * (amount + 1) states, each computed once from two cached values.
- Space: O(k * amount) — the cache, plus a recursion stack of depth up to k + amount / min(coins), at most 2,300 here.

### Trade-offs

A faithful translation of the "skip or use" argument, and the oracle. It recurses deeply when a small coin is present and stores the whole table; the bottom-up versions avoid both.

### Pitfalls and edge cases

- Recursing "for each value, pay one coin of it" without the index counts orders as different ways (2 + 5 and 5 + 2): that is the number of sequences, not combinations.
- `amount == 0` must return 1, not 0.
- Every count fits in 32 bits by the constraints; without that guarantee, counts would need 64 bits or a modulus.

### Language notes

- Python: a list-of-lists cache and a nested function; the runner allows the deep recursion.
- TypeScript: plain number arrays; every count stays far below 2^53.
- Java: fields for the coins and the cache.
- Kotlin: a local `fun` over `Array(k) { IntArray(amount + 1) { -1 } }`.
- Go: the recursion is a closure declared with `var count func(i, total int) int` before it is assigned. The table is a `[][]int` of -1.
- Rust: closures cannot recurse, so `count` is a private function. The coins are converted to `usize` once, so `total - coins[i]` is a plain index subtraction, and the `coins[i] <= total` guard keeps it from underflowing. `None` marks an unknown cell.

## Approach: tabulation (Table of counts by coin prefix and amount)

### Intuition

Fill the same table bottom-up, using prefixes of the coin list: `ways[i][t]` is the number of combinations of the first `i` values paying `t`. Row 0 has a single 1, for paying 0 with nothing. Each new row adds one coin value: the combinations that do not use it are the row above, and those that use it at least once are found in the same row, `coin` columns to the left.

### Algorithm

1. Create a `(k + 1) * (amount + 1)` table of zeros and set `ways[0][0] = 1`.
2. For each value `coin = coins[i - 1]` and each total `t` from 0 up: `ways[i][t] = ways[i - 1][t] + (ways[i][t - coin] if t >= coin)`.
3. Return `ways[k][amount]`.

### Correctness

The recurrence is the memoized one with prefixes instead of suffixes; the bijection argument is identical. Filling each row in increasing `t` computes `ways[i][t - coin]` before `ways[i][t]`, and the row above is complete before the row starts.

### Complexity

- Time: O(k * amount) — one addition per cell.
- Space: O(k * amount) — the full table.

### Trade-offs

No recursion, and every cell has a clear meaning, which makes it the easiest version to explain. It stores all k rows, although each row only reads itself and the row above.

### Pitfalls and edge cases

- Read `ways[i][t - coin]` (same row), not `ways[i - 1][t - coin]`: the latter allows each value at most once (that is the 0/1 knapsack count).
- Column 0 is 1 in every row: paying 0 is always possible exactly one way.

### Language notes

- Python: rows are independent lists; Kotlin and Java tables are zero-initialized, so only `ways[0][0]` is set.
- TypeScript: `Array.from` with a fill per row.
- Go and Rust: rows from `make([]int, amount+1)` and `vec![vec![0; amount + 1]; k + 1]` start at zero, so only `ways[0][0]` is set. Rust reads each coin as a `usize` because `total - coin` is an index; the `total >= coin` guard prevents the underflow.

## Approach: rolling-array (One array of counts with coins in the outer loop)

### Intuition

In the tabulation, row `i` is row `i - 1` plus contributions from row `i` itself. Updating a single array in place does exactly that: before the update, `ways[t]` still holds the row above, and walking `t` upwards means `ways[t - coin]` already holds the current row. Looping over the coin values outside and the totals inside is what makes the count about combinations.

### Algorithm

1. Set `ways = [1, 0, 0, ..., 0]` (length `amount + 1`).
2. For each `coin`, for `t` from `coin` up to `amount`: `ways[t] += ways[t - coin]`.
3. Return `ways[amount]`.

### Correctness

Invariant: after processing the first `i` values, `ways[t]` equals `ways[i][t]` of the full table for every `t`. During the pass for value `coin`, entries below `t` have been updated to row `i` and entries from `t` on still hold row `i - 1`, so `ways[t] + ways[t - coin]` is exactly the tabulation's recurrence. Each combination is built in coin order (all copies of the first value, then the second, and so on), so it is counted once.

### Complexity

- Time: O(k * amount) — one addition per (value, total) pair.
- Space: O(amount) — one array.

### Trade-offs

The shortest and fastest version, and the expected interview answer. Its loop order carries the whole meaning: swapping the loops (totals outside, coins inside) counts ordered sequences instead, a different problem.

### Pitfalls and edge cases

- Totals must increase inside each coin's pass; decreasing totals would allow each value at most once.
- Coins larger than `amount` leave the array unchanged, so they need no special case.

### Language notes

- Python and TypeScript: plain arrays; Java and Kotlin: `int[]` and `IntArray`, safe by the 32-bit guarantee.
- Go: a `[]int`, which is 64 bits wide. Rust: a `Vec<i32>`; cstudy builds with overflow checks, so a count above 2^31 - 1 would panic, but the constraints rule it out. `for total in coin..=amount` is an empty range when `coin > amount`, as `range(coin, amount + 1)` is in Python.
