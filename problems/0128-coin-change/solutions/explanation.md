# Coin Change: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| memoization | intermediate | O(a * k) | O(a) | you derive the recurrence top-down and want only the reachable remainders evaluated |
| tabulation | optimal | O(a * k) | O(a) | default answer |
| bfs | optimal | O(a * k) | O(a) | you think of it as a shortest path, or the answer is usually small |

Here `a` is `amount` and `k` is the number of coin values. Let `fewest(x)` be the fewest coins that pay `x` exactly. The last coin paid has some value `c <= x`, and the coins before it pay `x - c`, so

`fewest(x) = 1 + min over c <= x of fewest(x - c)`, with `fewest(0) = 0`, and `x` unreachable when every `x - c` is unreachable (or no coin fits).

Two shortcuts do not work. Greedy, "always take the largest coin that fits", is optimal for coin systems like 1, 5, 10, 25 but not in general: with coins 1, 3, 4 and amount 6 it pays 4 + 1 + 1 instead of 3 + 3. The naive recursion over the last coin, without memory, is correct but branches `k` ways at every level, about `k` to the power `a / min(coins)` calls in the worst case; it is the first step of the progression and is not a separate reference here.

## Approach: memoization (Top-down fewest coins per remainder)

### Intuition

The naive recursion reaches the same remainder along many paths: paying 1 then 3 and paying 3 then 1 both leave `amount - 4`. There are only `a + 1` possible remainders, so caching `fewest(x)` the first time it is computed makes each one cost `k` steps once.

### Algorithm

1. Define `fewest(x)`: return 0 when `x == 0`.
2. If the memo holds `x`, return it.
3. Otherwise, start from "unreachable" and, for each coin `c <= x`, keep the minimum of `fewest(x - c) + 1`. Store and return it.
4. Return `fewest(amount)`, mapping "unreachable" to -1.

### Correctness

By strong induction on `x`. `fewest(0) = 0` is right. For `x > 0`, any payment of `x` has a last coin `c`; the rest pays `x - c` and uses at least `fewest(x - c)` coins, so the minimum over `c` is a lower bound, and it is achieved by appending `c` to an optimal payment of `x - c`. If no `x - c` is payable, neither is `x`. The memo stores only values the recursion would have returned.

### Complexity

- Time: O(a * k) — each remainder from 1 to `a` is computed once, looping over `k` coins.
- Space: O(a) — the memo, plus a recursion that can be `a` frames deep when a coin of value 1 exists.

### Trade-offs

Direct translation of the recurrence, and it skips remainders that no sequence of coins can reach from `amount`. Its recursion depth grows with `amount`, which is one reason the constraints stop at 2000: for a large amount, prefer the bottom-up table.

### Pitfalls and edge cases

- Represent "unreachable" with a value that survives `+ 1` and `min`: infinity in Python, or `amount + 1` (no payment needs more than `amount` coins). `Integer.MAX_VALUE + 1` overflows in Java and Kotlin.
- Keep "unknown" (not computed) separate from "unreachable" (computed, no answer); conflating them recomputes unreachable remainders every time and brings the exponential cost back.
- Skip coins larger than the remainder instead of recursing on a negative amount.

### Language notes

- Python: `functools.cache` on a nested function; `math.inf` is the unreachable value, so the result is converted back with `int`.
- TypeScript: a closure over a `memo` array filled with -1.
- Java: a private helper takes the memo and the unreachable sentinel explicitly.
- Kotlin: a local `fun` captures `memo`; `IntArray(amount + 1) { unknown }` initializes the sentinel.
- Go: there is no infinity for `int`, so `infinity = 1 << 30` stands in for `math.inf`: it is larger than any real answer (at most 2000 coins) and small enough that `1+infinity` cannot overflow, and the result is compared with `>= infinity` instead of `==`. A coin can be up to 2^31 - 1, which `int` holds on 64-bit platforms.
- Rust: `INFINITY = 1 << 30` plays the role of `math.inf` for the same reason: `1 + INFINITY` stays inside `i32`, where `i32::MAX` would panic under the overflow checks. Coins are compared as `coin as usize <= remaining`, which is exact for positive `i32` values, and `fewest` is a free function because a closure cannot recurse.

## Approach: tabulation (Bottom-up table over amounts)

### Intuition

`fewest(x)` reads only smaller amounts, so computing `x = 1, 2, ..., amount` in order guarantees that every entry it needs is already final.

### Algorithm

1. Create `fewest` of length `amount + 1`, all set to `amount + 1` (unreachable), and set `fewest[0] = 0`.
2. For each `x` from 1 to `amount`, for each coin `c <= x`: if `fewest[x - c] + 1 < fewest[x]`, store it.
3. Return `fewest[amount]`, or -1 if it is still `amount + 1`.

### Correctness

Invariant: when the loop reaches `x`, `fewest[y]` is final for every `y < x`. Step 2 then applies the recurrence to final values, so `fewest[x]` becomes final too. An unreachable `y` keeps `amount + 1`, and `amount + 2` never beats a real count, which is at most `amount`, so unreachable entries never contribute.

### Complexity

- Time: O(a * k) — `a` amounts, `k` coins each.
- Space: O(a) — one table entry per amount.

### Trade-offs

Simple, iterative, no stack depth concerns: the standard interview answer and the oracle. It evaluates every amount up to `a`, including those no coin sequence can reach from `amount`; that is wasted work only when the coins are large and sparse.

### Pitfalls and edge cases

- `amount = 0`: the table has one entry, the loops do not run, and the answer is 0.
- Coins larger than `amount` (up to 2^31 - 1 here) must simply be skipped; `coin <= x` does that, and `x - coin` is never computed for them.
- Looping over coins outside and amounts inside also works for this problem (it is the unbounded knapsack); the order matters only when counting combinations.

### Language notes

- Python: `[0] + [unreachable] * amount` builds the table in one expression.
- TypeScript: `new Array<number>(amount + 1).fill(unreachable)`.
- Java and Kotlin: `Arrays.fill` and the `IntArray(size) { init }` constructor set the sentinel.
- Go: `make` zero-fills the table, so `fewest[0] = 0` is already set and the other cells are overwritten with `unreachable` in a first loop.
- Rust: `vec![unreachable; amount + 1]` followed by `fewest[0] = 0` builds the table in two steps, the counterpart of Python's `[0] + [unreachable] * amount`. `unreachable` stays an `i32` and `amount` is shadowed as a `usize` for indexing.

## Approach: bfs (Breadth-first search over remainders)

### Intuition

Picture each remainder as a node and paying one coin as an edge from `x` to `x - c`. The fewest coins is the length of the shortest path from `amount` to 0. All edges have the same length, so breadth-first search finds it level by level: level `j` holds every remainder payable down from `amount` with exactly `j` coins and no fewer.

### Algorithm

1. Mark `amount` as seen and make it the only node of level 0.
2. While the current level is not empty: if 0 has been seen, return the level number. Otherwise build the next level from every unseen `x - c >= 0`, marking each as seen, and increase the level number.
3. If the levels run out without reaching 0, return -1.

### Correctness

Breadth-first search on an unweighted graph visits nodes in nondecreasing distance from the start, and the first time a node is seen is along a shortest path. Each node is at distance `j` exactly when it can be reached with `j` coins and not fewer, so the level at which 0 first appears is the fewest coins. Every remainder reachable from `amount` is eventually visited, so if 0 is never seen it is unreachable.

### Complexity

- Time: O(a * k) — each of the at most `a + 1` remainders enters a level once and tries `k` coins.
- Space: O(a) — the `seen` array and the current and next levels.

### Trade-offs

The same worst case as the table, but it stops as soon as 0 is reached, which is fast when the answer uses few coins. It needs more bookkeeping (levels or a queue) and is less familiar as a DP answer; mention it as the graph view of the same recurrence.

### Pitfalls and edge cases

- Mark nodes when they are enqueued, not when they are dequeued; otherwise the same remainder enters a level many times and the queue blows up.
- Check for 0 before expanding a level, so `amount = 0` returns 0 without any work.

### Language notes

- Python and TypeScript: a list per level avoids a separate distance array.
- Java: an `ArrayDeque<Integer>` and a loop over the current `queue.size()` process one level at a time; the queue holds boxed integers.
- Kotlin: a `mutableListOf<Int>()` per level, swapped into `level` after each round.
- Go: each level is a fresh slice (`var nextLevel []int`, grown by `append`), and `seen` has one flag per remainder, so a remainder joins at most one level.
- Rust: `remaining.checked_sub(coin as usize)` returns `None` when the coin is larger than the remainder, which replaces Python's `rest >= 0` test and avoids an unsigned underflow. Each level is a `Vec<usize>` replaced by the next one, so no queue type is needed.
