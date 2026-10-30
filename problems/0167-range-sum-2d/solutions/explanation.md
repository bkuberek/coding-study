# Range Sum Query 2D: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| scan-region | brute | O(m * n) per sumRegion | O(1) | a few queries on a small grid, or as a correctness oracle |
| prefix-2d | optimal | O(1) per sumRegion, O(m * n) to build | O(m * n) | default answer whenever the grid is fixed |

The grid has `m` rows and `n` columns. The generated sequences make one query per four cells, so the brute force costs O((m * n)^2) per sequence and prefix sums O(m * n).

## Approach: scan-region (Visit every cell of the rectangle)

### Intuition

The rectangle is a set of cells, so add them: one loop over its rows, one over its columns.

### Algorithm

1. The constructor keeps a reference to `matrix`.
2. `sumRegion(row1, col1, row2, col2)`: for every row from `row1` to `row2` and every column from `col1` to `col2`, add `matrix[row][col]` to a running total; return it.

### Correctness

The two nested loops enumerate exactly the pairs `(row, col)` with `row1 <= row <= row2` and `col1 <= col <= col2`, each once, which is the definition of the rectangle's sum.

### Complexity

- Time: O(m * n) per sumRegion — a rectangle can cover the whole grid; with random corners it covers about a ninth of it on average.
- Space: O(1) — one accumulator; the grid is the caller's, not a copy.

### Trade-offs

No preparation and no memory, so it is fine for one or two queries. With many queries it re-adds the same cells over and over; prefix sums make each query a constant number of lookups.

### Pitfalls and edge cases

- Both corners are inclusive: loop up to `row2` and `col2`, not one before.
- Read `matrix[row]` once per row (the reference code keeps it in `cells`) instead of indexing twice in the inner loop; it does not change the complexity, only the constant.

## Approach: prefix-2d (Two-dimensional prefix sums with inclusion-exclusion)

### Intuition

Let `P[r][c]` be the sum of the top-left block made of rows `0..r-1` and columns `0..c-1`. The rectangle you want is the big block `P[row2 + 1][col2 + 1]` minus the block above it, `P[row1][col2 + 1]`, minus the block to its left, `P[row2 + 1][col1]`. The corner block `P[row1][col1]` sits in both of those, so it was subtracted twice and is added back once.

### Algorithm

1. Allocate `P` with `m + 1` rows and `n + 1` columns of zeros; row 0 and column 0 stay 0 (empty blocks).
2. For every cell `(r, c)`: `P[r + 1][c + 1] = matrix[r][c] + P[r][c + 1] + P[r + 1][c] - P[r][c]`.
3. `sumRegion(row1, col1, row2, col2)` returns `P[row2 + 1][col2 + 1] - P[row1][col2 + 1] - P[row2 + 1][col1] + P[row1][col1]`.

### Correctness

Step 2 is inclusion-exclusion on blocks: the block ending at `(r, c)` is its last cell plus the block above plus the block to the left, minus their overlap, which was counted twice. By induction in row-major order every `P` entry is the sum of its block. In step 3, every cell of the grid's top-left block up to `(row2, col2)` is counted with weight `1 - [above] - [left] + [above and left]`: that is 1 inside the rectangle, `1 - 1 = 0` in the strips above or to the left only, and `1 - 1 - 1 + 1 = 0` in the corner block. So exactly the rectangle remains.

### Complexity

- Time: O(1) per sumRegion, O(m * n) to build — one pass over the grid, then four lookups per query.
- Space: O(m * n) — the `(m + 1) * (n + 1)` table.

### Trade-offs

The standard answer and the direct generalization of one-dimensional prefix sums. It needs a table as large as the grid and assumes the grid never changes; with updates, a two-dimensional Fenwick tree answers both queries and updates in O(log m * log n). Another middle ground, one prefix array per row, answers a query in O(m) and is easier to write, but it gives away most of the benefit.

### Pitfalls and edge cases

- The extra zero row and column remove every special case for rectangles touching the top or left edge.
- Forgetting to add back the corner block (or subtracting it again) is the classic bug; check with a single-cell rectangle.
- Overflow: every block sum is at most `4 * 10^8` in absolute value and the intermediate results of the four-term expression stay under `1.6 * 10^9`, so 32-bit `int` is safe here. With larger values or grids, use 64-bit prefixes.

### Language notes

- Python: building row by row with a running row sum (`P[r + 1][c + 1] = P[r][c + 1] + running`) is the same recurrence with one fewer lookup.
- TypeScript: `Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0))` creates independent rows; filling one shared array would alias every row.
- Java: `new int[m + 1][n + 1]` is zero-initialized, so no explicit fill is needed.
- Kotlin: `Array(m + 1) { IntArray(n + 1) }` builds the table as `Array<IntArray>`, which is the JVM's `int[][]`.
- Go: `make([][]int, m+1)` creates the outer slice with nil rows, so each row is allocated separately with its own `make`; `above := prefix[r]` names the finished row to read while the new one is filled. The elements are plain `int`, which holds a rectangle sum of up to 4 * 10^8 on every platform Go targets.
- Rust: `vec![vec![0; cols + 1]]` seeds the zero row, and `prefix.push(row)` appends each finished row. The `above` row is a shared borrow of `prefix` that ends before the `push`, so no clone is needed. The query casts the four `i32` bounds to `usize` once and then indexes; the table holds `i32`, enough for the 4 * 10^8 maximum, and an overflow would panic rather than wrap.
