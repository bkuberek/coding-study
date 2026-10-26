# Burst Balloons: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| memoization | intermediate | O(n^3) | O(n^2) | deriving the "last balloon" recurrence; also the oracle |
| tabulation | optimal | O(n^3) | O(n^2) | default answer |

This is an interval DP. The state is a pair of balloons `(left, right)` that are still standing, and its value is the most coins from bursting everything between them. Trying all n! orders is hopeless beyond about 10 balloons, and splitting on the first balloon burst does not work: after it bursts, its two neighbors become adjacent, so the left and right parts interact. Choosing the balloon burst last in an interval is the key that makes the parts independent. Unlike the other two-dimensional DPs in this set, there is no rolling-array version: an interval needs answers for intervals of every shorter length, not just the previous "row".

## Approach: memoization (Recursion on the balloon burst last in each interval with a memo table)

### Intuition

Pad the row with a balloon of value 1 at each end. Consider the open interval between two standing balloons `left` and `right`. Whichever balloon `k` in it is burst last, at that moment its neighbors are exactly `left` and `right`, so it earns `v[left] * v[k] * v[right]`. Before that, `k` stands between the balloons on its left and those on its right, so the two groups are burst independently, each inside its own smaller interval.

### Algorithm

1. Let `values = [1] + nums + [1]` and `solve(left, right)` the best total for the open interval.
2. If `right - left < 2`, the interval is empty: return 0.
3. Otherwise return the maximum over `left < k < right` of `solve(left, k) + values[left] * values[k] * values[right] + solve(k, right)`, cached.
4. The answer is `solve(0, n + 1)`.

### Correctness

Every bursting order of the balloons in `(left, right)` has a last balloon `k`. While `k` stands, a balloon on its left never has a neighbor to the right of `k` and vice versa, so the order restricted to each side is a valid order for that side's interval with `left`, `k` (or `k`, `right`) as the fixed ends, and the coins add up. Conversely, any orders for the two sides followed by `k` form a valid order of the whole interval with that total. So the best total is the maximum over `k` of the best of each side plus the last burst, which is the recurrence.

### Complexity

- Time: O(n^3) — about n^2 / 2 intervals, each trying up to n choices of the last balloon.
- Space: O(n^2) — the memo table, plus a recursion depth of at most n.

### Trade-offs

The clearest way to explain the solution, and the oracle. It only visits the intervals it needs (all of them here), and pays for recursion; the tabulation is the same work in tight loops.

### Pitfalls and edge cases

- Use open intervals with fixed ends. Recursing on "which balloon to burst first" leads to subproblems that depend on the whole history.
- The padding balloons are never burst; they only provide the factor 1 at the ends.
- Zeros are allowed: a balloon worth 0 contributes nothing itself and makes its neighbors' products 0 while it stands, which is why the best order often bursts it early.
- The largest total is 300 * 100^3 = 3 * 10^8, which fits in 32 bits.

### Language notes

- Python: a list-of-lists memo and a generator expression inside `max`.
- TypeScript: `Int32Array` rows and an explicit loop for the maximum.
- Java: `System.arraycopy` builds the padded array; the memo is a field.
- Kotlin: `intArrayOf(1, *nums, 1)` pads with the spread operator, and `(left + 1 until right).maxOf { ... }` takes the maximum.

## Approach: tabulation (Fill the interval table by increasing length)

### Intuition

Every interval depends only on strictly shorter intervals inside it. Filling the table in order of increasing gap `right - left` therefore computes every dependency first, with no recursion.

### Algorithm

1. Build `values` as above and a `(n + 2) * (n + 2)` table of zeros (gaps 0 and 1 are empty intervals).
2. For `gap` from 2 to `n + 1`, for every `left` with `right = left + gap`: set `best[left][right]` to the maximum over `left < k < right` of `best[left][k] + values[left] * values[k] * values[right] + best[k][right]`.
3. Return `best[0][n + 1]`.

### Correctness

The recurrence is the memoized one. Both `(left, k)` and `(k, right)` have a smaller gap than `(left, right)`, so they are final when the loop reaches it.

### Complexity

- Time: O(n^3) — the sum over gaps of (number of intervals) * (gap - 1) is about n^3 / 6.
- Space: O(n^2) — the table.

### Trade-offs

The standard answer. Iterating by gap (or by `left` descending and `right` ascending, which also works) is the part people get wrong; filling row by row in plain order would read unfinished cells.

### Pitfalls and edge cases

- Hoisting `values[left] * values[right]` out of the inner loop saves a multiplication per step; it does not change the result.
- An input of one balloon gives a single interval of gap 2 with `k` the only choice.

### Language notes

- Python: the inner maximum is a generator over `last`, reading `best[left]` once as `row`; at n = 300 this is about 4.5 million steps, a second or so in CPython.
- TypeScript, Java and Kotlin: three nested loops over primitive arrays.
