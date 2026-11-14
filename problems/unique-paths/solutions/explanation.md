# Unique Paths: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| memoization | intermediate | O(m * n) | O(m * n) | the recurrence is clearest top-down; also the oracle |
| tabulation | intermediate | O(m * n) | O(m * n) | the standard bottom-up DP |
| rolling-array | intermediate | O(m * n) | O(min(m, n)) | DP answer with minimal memory |
| binomial | optimal | O(min(m, n) + log p) | O(1) | default answer once the formula is known |

The DP state is a cell; its value is the number of routes between it and one end of the grid, and it is the sum of the values of the two neighbors on the robot's way. Plain recursion on that recurrence, without a memo, is correct but recomputes the same cells exponentially often: with the goal as the only base case, every route ends in its own base-case call, so the number of calls is at least the answer itself, C(m + n - 2, m - 1), about 4 * 10^7 already for a 15 by 15 grid. It is therefore not among the references. The binomial approach skips the table entirely by counting move sequences.

The time classes use the number of cells, n = m * n, as the size; the generated grids are roughly square, so min(m, n) grows like sqrt(n).

## Approach: memoization (Recursion from each cell with a memo table)

### Intuition

From any cell, a route to the goal starts with a move right or a move down, so the number of routes from the cell is the number from the cell to its right plus the number from the cell below. Recursion expresses that directly; a table of already computed cells makes each cell cost O(1) after its first visit.

### Algorithm

1. Let `count(row, column)` be the number of routes from that cell to `(m - 1, n - 1)`.
2. If `row == m - 1` or `column == n - 1`, return 1: only a straight line remains.
3. Otherwise, if the memo has no value yet, store `(count(row + 1, column) + count(row, column + 1)) mod p`.
4. Return the memo value; the answer is `count(0, 0)`.

### Correctness

State: `count(r, c)` is the number of monotone routes from `(r, c)` to the goal. Recurrence: routes from `(r, c)` split by their first move into two disjoint groups, the routes through `(r + 1, c)` and those through `(r, c + 1)`, so the counts add. Base cases: from the last row or column only one route exists. Every call moves strictly closer to the goal, so the recursion terminates, and the memo only stores values the recurrence would recompute identically. Reducing modulo p after every addition preserves the result modulo p.

### Complexity

- Time: O(m * n) — each of the m * n cells is computed once, from two O(1) lookups.
- Space: O(m * n) — the memo table, plus a recursion stack of depth up to m + n - 2.

### Trade-offs

The most direct translation of the recurrence, which makes it the oracle. It pays for function calls and keeps the full table; the recursion depth reaches about 2,000 at the largest grids, which is fine here but would overflow a default stack on much larger grids.

### Pitfalls and edge cases

- A 1 by 1 grid has one route (the empty one); the base case handles it.
- Use a sentinel (-1) for "not computed": 0 is never a valid count here, but in variants with obstacles it is.
- Reduce after each addition; the true counts have hundreds of digits.

### Language notes

- Python: a list-of-lists memo uses far less memory than `functools.cache` with a million `(row, column)` keys; the runner raises the recursion limit, but a plain script would need `sys.setrecursionlimit`.
- TypeScript: one `Int32Array` per row (all residues fit in 31 bits) and a closure for the recursion.
- Java: the memo is a field, because Java has no nested functions; two residues below p add to less than 2^31, so `int` arithmetic is safe before the reduction.
- Kotlin: a local `fun` closes over the memo, and `Array(m) { IntArray(n) { -1 } }` builds it.
- Go: the closure is declared with `var count func(row, column int) int` before it is assigned, so it can call itself. `int` is 64 bits, so the sum of two residues cannot overflow.
- Rust: a closure cannot call itself, so `count` is a private function over `&mut [Vec<Option<i32>>]`, where `None` marks an unknown cell. Like the Java version, two residues below `MOD` add up to less than 2^31, so `i32` holds the sum before the reduction.

## Approach: tabulation (Fill the table of path counts row by row)

### Intuition

Turn the recursion around: count the routes from the start to each cell instead. A cell is entered from the left or from above, so its count is the sum of those two cells, which are already filled when the table is filled row by row, left to right.

### Algorithm

1. Create an m by n table filled with 1: the first row and first column are reached in a straight line.
2. For each row from 1 and each column from 1, set `routes[row][column] = (routes[row - 1][column] + routes[row][column - 1]) mod p`.
3. Return `routes[m - 1][n - 1]`.

### Correctness

State: `routes[r][c]` is the number of routes from `(0, 0)` to `(r, c)`. The last move into `(r, c)` comes from above or from the left, which splits the routes into two disjoint groups, so the recurrence adds them. The fill order computes both neighbors before the cell. The number of routes from the start to the goal equals the number from the goal backwards, so this agrees with the memoized version.

### Complexity

- Time: O(m * n) — one addition per cell.
- Space: O(m * n) — the full table.

### Trade-offs

No recursion, so no stack depth limit and less overhead per cell; it still stores every row although only the previous one is read.

### Pitfalls and edge cases

- Initialize the first row and column to 1, not 0; with a table of zeros the sums stay 0.
- Loops start at 1; with `m == 1` or `n == 1` they do not run and the answer is 1.

### Language notes

- Python: `[[1] * n for _ in range(m)]` builds independent rows; `[[1] * n] * m` would alias one row m times.
- TypeScript: `Int32Array` rows filled with 1.
- Java: `Arrays.fill` per row; Kotlin builds the rows with `IntArray(n) { 1 }`.
- Go: each row is its own `make([]int, n)`, filled with 1 in a loop because `make` zeroes the memory.
- Rust: `vec![vec![1; columns]; rows]` clones the inner vector, so the rows are independent.

## Approach: rolling-array (One row of path counts updated in place)

### Intuition

Row `r` of the table only reads row `r - 1` and the cell to its left in row `r`. Keep one array: before updating `routes[column]` it still holds the value from the row above, and `routes[column - 1]` already holds the current row's value. The update `routes[column] += routes[column - 1]` is the whole recurrence. Since the count is symmetric in m and n, let the array run along the shorter side.

### Algorithm

1. Let `width = min(m, n)` and `height = max(m, n)`; fill `routes` of length `width` with 1.
2. Repeat `height - 1` times: for each column from 1, set `routes[column] = (routes[column] + routes[column - 1]) mod p`.
3. Return `routes[width - 1]`.

### Correctness

Invariant: after processing row `r`, `routes[c]` equals `table[r][c]` of the tabulation. Updating left to right, the old `routes[c]` is `table[r - 1][c]` and the new `routes[c - 1]` is `table[r][c - 1]`, so the in-place update computes exactly `table[r][c]`. Transposing the grid maps routes to routes one to one, so using the shorter side changes nothing.

### Complexity

- Time: O(m * n) — the same additions as the full table.
- Space: O(min(m, n)) — one row along the shorter side.

### Trade-offs

The best DP answer: same time, a fraction of the memory, and less cache pressure. It loses the table, so it cannot reconstruct an actual route (not needed here).

### Pitfalls and edge cases

- Update left to right; right to left would mix in values from the row above twice.
- Choosing the shorter side is what makes the space O(min(m, n)) instead of O(n).

### Language notes

- Python: a list; TypeScript: an `Int32Array`; Java: `int[]` with `Arrays.fill`; Kotlin: `IntArray(width) { 1 }` and `repeat(height - 1)`.
- Go: the built-in `min` and `max` pick the shorter and longer side. Rust: `m.min(n)` and `m.max(n)`, with `for _ in 1..height` because the row number is not used.

## Approach: binomial (Choose which moves go down with a modular inverse)

### Intuition

Every route is a sequence of exactly `m - 1` moves down and `n - 1` moves right, and every such sequence is a route. So the number of routes is the number of ways to choose which of the `m + n - 2` moves go down: `C(m + n - 2, m - 1)`. Modulo the prime p, division by `k!` becomes multiplication by its modular inverse, `(k!)^(p - 2) mod p` by Fermat's little theorem.

### Algorithm

1. Let `moves = m + n - 2` and `k = min(m, n) - 1` (by symmetry, `C(moves, k)` is the same count).
2. Multiply `numerator = (moves - k + 1) * ... * moves` and `denominator = k!`, both modulo p.
3. Return `numerator * denominator^(p - 2) mod p`, using fast exponentiation.

### Correctness

The map from routes to move sequences is a bijection onto sequences with exactly `m - 1` downs, so the count is the binomial coefficient, and `C(moves, k) = C(moves, moves - k)`. `C(moves, k) = numerator / k!` exactly, and since p is a prime larger than every factor (at most 1998), `k!` is not divisible by p and has an inverse modulo p, equal to `(k!)^(p - 2)` by Fermat's little theorem. Hence the product is `C(moves, k) mod p`.

### Complexity

- Time: O(min(m, n) + log p) — k multiplications for each product and about 30 squarings for the inverse.
- Space: O(1) — a few running products.

### Trade-offs

Asymptotically the best and the usual follow-up in interviews. It only works because the grid has no obstacles and moves are restricted to right and down; the DP versions adapt to obstacles, weights or other move sets, which is why they are the pattern to learn.

### Pitfalls and edge cases

- Products of two residues reach about 10^18: they fit in a 64-bit integer but not exactly in a double.
- Without the modulus, a formula with integer division must divide as it goes (`result = result * (moves - k + i) / i`) to stay exact.
- `k = 0` (a single row or column) leaves both products at 1, which gives 1.

### Language notes

- Python: `pow(denominator, MOD - 2, MOD)` is built-in modular exponentiation. `math.comb(m + n - 2, m - 1) % MOD` is also correct, but it builds a number with hundreds of digits first.
- TypeScript: `number` cannot hold 10^18 exactly, so the reference uses `BigInt` (`1_000_000_007n`) and converts back with `Number` at the end.
- Java and Kotlin: `long` arithmetic with a hand-written square-and-multiply, since there is no built-in modular power for primitive types (`BigInteger.modPow` exists, but boxes every step).
- Go: `int` is 64 bits, so a product of two residues (below 2^60) fits without `math/big`; `modPow` is the same hand-written square-and-multiply (`big.Int.Exp` would allocate at every step).
- Rust: the signature uses `i32`, so the reference widens to `i64` for the products (`i64::from`) and narrows the final residue with `as i32`, which is safe because it is below 2^31. `mod_pow` is hand-written, since the standard integer `pow` takes no modulus.
