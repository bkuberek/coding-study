# Target Sum: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| backtracking | brute | O(2^n) | O(n) | n is at most about 20; also the oracle |
| memoization | intermediate | O(n * s) | O(n * s) | the total s is small and you start from the recursion |
| tabulation | optimal | O(n * s) | O(n * s) | standard DP over running totals |
| subset-sum | optimal | O(n * s) | O(s) | default answer: the reduction to counting subsets |

Here n is the number of values and s their total. With n at most 20, enumerating all 2^n sign assignments is feasible, so the brute force is a real reference here. The DP state is (how many values are signed, running total); the running total lies in `[-s, s]`, so there are at most n * (2s + 1) states, a number that does not grow exponentially. The time classes use n as the size. The generated values are at most 10, so the total s grows in proportion to n and the DP approaches grow as n^2; with a total that stayed fixed, the memo would reach only 2^i running totals after i values and stay exponential over n of 20 or less.

## Approach: backtracking (Try both signs for every number)

### Intuition

Walk through the numbers and branch twice at each one: plus or minus. At the end, count the branch if the total hits the target.

### Algorithm

1. `count(index, total)`: if `index == n`, return 1 when `total == target`, else 0.
2. Otherwise return `count(index + 1, total + nums[index]) + count(index + 1, total - nums[index])`.
3. Return `count(0, 0)`.

### Correctness

The recursion tree has one leaf per sign assignment (each level fixes one sign), and each leaf carries exactly that assignment's total, so the sum of the leaf indicators is the number of assignments that reach the target.

### Complexity

- Time: O(2^n) — the tree has 2^n leaves and 2^(n+1) - 1 calls.
- Space: O(n) — the recursion depth.

### Trade-offs

The simplest correct answer and the oracle; about a million leaves at n = 20 is fine in compiled languages and borderline in Python. It ignores the fact that many prefixes reach the same running total, which is exactly what the DP versions exploit.

### Pitfalls and edge cases

- Zeros: `+0` and `-0` are separate branches, and both count.
- The answer can reach 2^20 (twenty zeros, target 0), which still fits in a 32-bit integer.

### Language notes

- Python: about 2 million calls take a few tenths of a second in CPython.
- TypeScript and Kotlin: a local function; Java: a static helper with the inputs as parameters.
- Go: a closure declared with `var count func(index, total int) int` so it can recurse. Go has no conversion from `bool` to `int`, so an `if` returns 1 or 0.
- Rust: a private function that receives the numbers and the target; `i32::from(total == target)` turns the `bool` into 1 or 0.

## Approach: memoization (Recursion over index and running sum with a memo table)

### Intuition

The number of ways to finish from `(index, total)` does not depend on which signs led there. Cache it, and the exponential tree collapses to at most n * (2s + 1) distinct states.

### Algorithm

1. Same recursion as the backtracking approach.
2. Cache `count(index, total)`, keyed by `index` and `total + s` (so the key is non-negative).
3. Return `count(0, 0)`.

### Correctness

The value of `count(index, total)` is the number of sign assignments of `nums[index:]` that add `target - total`; it is a function of the pair alone, so caching does not change any result. The recursion is the backtracking recursion, which is correct.

### Complexity

- Time: O(n * s) — at most n * (2s + 1) states, each combining two cached values.
- Space: O(n * s) — the cache, plus O(n) recursion depth.

### Trade-offs

A small change to the brute force that makes it polynomial in s. It allocates a full table even though only reachable totals are visited, and it keeps the recursion.

### Pitfalls and edge cases

- Running totals are negative too: offset them by `s` before indexing an array.
- A target outside `[-s, s]` is never reached; the recursion handles it, but the table approaches check it first.

### Language notes

- Python: `functools.cache` on a nested function; the state count is small enough for a dictionary.
- TypeScript, Java and Kotlin: a table of `2s + 1` columns per index with -1 as "unknown"; `Arrays.stream(nums).sum()` and `nums.sum()` compute s.
- Go: the same table of `2s + 1` columns per index, filled with -1; a short loop computes `s`.
- Rust: `Option<i32>` cells in a `Vec<Vec<Option<i32>>>`, and `nums.iter().sum()` computes `s`. The column `(running + total) as usize` is never negative, because `|running|` never exceeds `s`.

## Approach: tabulation (Table of counts by prefix and running sum)

### Intuition

Push counts forward: `ways[i][t]` is the number of sign assignments of the first `i` values whose total is `t`. Each count spreads to two cells of the next row, `t + v` and `t - v`.

### Algorithm

1. If `|target| > s`, return 0.
2. Create an `(n + 1) * (2s + 1)` table; `ways[0][0 + s] = 1`.
3. For each value `v` and each total `t` with a non-zero count in row `i`, add the count to `ways[i + 1][t + v + s]` and `ways[i + 1][t - v + s]`.
4. Return `ways[n][target + s]`.

### Correctness

By induction on `i`: every assignment of the first `i + 1` values extends exactly one assignment of the first `i` values with one sign, so row `i + 1` receives each assignment's count exactly once at its new total. Totals of prefixes never leave `[-s, s]`, so the indexes stay in range.

### Complexity

- Time: O(n * s) — each row has 2s + 1 cells, each pushed in O(1).
- Space: O(n * s) — the full table.

### Trade-offs

Iterative and easy to check; keeping only two rows would bring the space down to O(s), and the subset-sum reduction does better still by halving the range.

### Pitfalls and edge cases

- Skip empty cells, or the pushes from out-of-range totals could be attempted; with the offset they stay in range anyway.
- A zero pushes its count twice into the same cell, which doubles it, as it should.

### Language notes

- Python enumerates each row; TypeScript, Java and Kotlin loop over offsets, and Kotlin destructures `withIndex()`.
- Go ranges over `ways[i]` as `offset, count`. Rust loops over the offsets by index, because it reads `ways[i]` while it writes `ways[i + 1]` and the borrow checker would not allow a live iterator over one row of the table next to a write to another. Only offsets with a positive count reach `offset - value`, and a reachable offset always stays inside the table, so the `usize` subtraction cannot underflow.

## Approach: subset-sum (Count subsets with the positive sum in one rolling array)

### Intuition

Split the numbers into the plus group (sum `P`) and the minus group (sum `s - P`). The signed total is `P - (s - P) = 2P - s`, so it equals the target exactly when `P = (s + target) / 2`. Counting sign assignments is therefore counting subsets with sum `P`, which a one-dimensional knapsack does with one array, iterating the sums downwards so that each value is used at most once.

### Algorithm

1. If `|target| > s` or `s + target` is odd, return 0.
2. Let `P = (s + target) / 2`; set `ways = [1, 0, ..., 0]` of length `P + 1`.
3. For each value `v`, for `p` from `P` down to `v`: `ways[p] += ways[p - v]`.
4. Return `ways[P]`.

### Correctness

Sign assignments and subsets (the plus positions) are in one-to-one correspondence, and the assignment reaches the target exactly when its subset sums to `P`; if `s + target` is odd or `|target| > s`, no subset qualifies. Invariant for the loop: after processing a prefix of the values, `ways[p]` counts the subsets of that prefix with sum `p`. Iterating `p` downwards, `ways[p - v]` still holds the count without `v`, so the update adds exactly the subsets that contain `v` once.

### Complexity

- Time: O(n * s) — each value updates at most `P + 1 <= s + 1` entries.
- Space: O(s) — one array of `P + 1` counts.

### Trade-offs

The fastest and leanest version, and the insight interviewers look for. It is a reduction, not a direct model of the signs, so it is easier to get wrong under pressure (parity and range checks).

### Pitfalls and edge cases

- Check parity and range before computing `P`; otherwise `P` is fractional or negative.
- Iterate `p` downwards; upwards would let a value be reused, which counts multisets instead of subsets.
- Zeros are handled for free: `ways[p] += ways[p]` doubles every count, one for each sign of the zero.

### Language notes

- The four references are the same loop; TypeScript divides with `/` after the parity check, so the result is an integer; Kotlin uses `downTo`.
- Go: `%` keeps the sign of a negative operand, so the range check on `target` comes before the parity test; the loop is `for p := plus; p >= value; p--`.
- Rust: `%` keeps the sign too, so the `target.abs() > total` test runs first. `(value..=plus).rev()` counts down and is an empty range when `value > plus`, so no `usize` goes below zero.
