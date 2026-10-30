# Maximal Square: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| memoization | intermediate | O(m * n) | O(m * n) | deriving the recurrence; also the oracle |
| tabulation | optimal | O(m * n) | O(m * n) | standard answer |
| rolling-array | optimal | O(m * n) | O(n) | default answer with minimal memory |

Here m and n are the number of rows and columns. The state is a cell, and its value is the side of the largest all-ones square anchored at that cell (top-left corner for the memoized version, bottom-right for the tables). The brute force that grows a square from every cell and checks it cell by cell costs up to O((m * n) * min(m, n)^2) on a grid of ones, and plain recursion on the recurrence without a memo recomputes the same corners exponentially often along the three directions; neither is among the references.

The time classes use the number of cells as n; the generated grids are roughly square, so one row has about sqrt(n) cells.

## Approach: memoization (Recursion on the square starting at each cell with a memo table)

### Intuition

A square of ones with top-left corner `(r, c)` and side `k + 1` exists exactly when the cell is a one and squares of side `k` start at the three neighbors to the right, below and diagonally below-right. So the largest side at `(r, c)` is one more than the smallest of the three neighbors' largest sides.

### Algorithm

1. Let `largest(r, c)` be 0 outside the grid or on a `'0'` cell.
2. Otherwise `largest(r, c) = 1 + min(largest(r + 1, c), largest(r, c + 1), largest(r + 1, c + 1))`, cached.
3. Return the square of the maximum of `largest` over all cells.

### Correctness

If the three neighbors start squares of side at least `k`, together with the corner cell they cover the `(k + 1) * (k + 1)` square at `(r, c)`: the right neighbor's square covers the top `k` rows of the last `k` columns, the lower neighbor's the bottom `k` rows of the first `k` columns, and the diagonal one the bottom-right `k` by `k` block. Conversely, a square of side `k + 1` at `(r, c)` contains squares of side `k` at all three neighbors. So the recurrence gives the exact largest side. Every square has a top-left corner, so the maximum over all cells is the answer.

### Complexity

- Time: O(m * n) — each cell is computed once from three cached values.
- Space: O(m * n) — the cache, plus a recursion stack of depth up to m + n.

### Trade-offs

The recurrence in its most direct form and the oracle here. The tables avoid the recursion and are just as easy once the recurrence is known.

### Pitfalls and edge cases

- The cells are characters: compare with `'1'`, not the number 1.
- Return the area (side squared), not the side.
- A grid of zeros has answer 0, a single one answer 1.

### Language notes

- Python: a nested function over a list-of-lists cache; `max` over a generator visits every cell.
- TypeScript: cells are one-character strings (`"1"`), and `Int16Array` rows hold sides up to 300.
- Java and Kotlin: `char[][]` and `Array<CharArray>`, compared with `'0'`; Java keeps the grid and cache in fields.
- Go: the grid is a `[][]rune`, compared with the rune literal `'0'`; the built-in `min` takes three arguments, and the recursion is a closure declared with `var` first.
- Rust: the grid is a `Vec<Vec<char>>`. `Ord::min` takes two arguments, so the three neighbors chain as `down.min(right).min(diagonal)`; the recursion is a private function that receives the grid and the `Option<i32>` cache.

## Approach: tabulation (Table of the largest square ending at each cell)

### Intuition

The mirror image: let `side[r][c]` be the largest all-ones square whose bottom-right corner is `(r, c)`. It depends on the cells above, to the left and diagonally above-left, which a row-by-row scan has already filled. A border row and column of zeros removes the edge cases.

### Algorithm

1. Create an `(m + 1) * (n + 1)` table of zeros.
2. For every `'1'` cell `(r, c)`: `side[r + 1][c + 1] = 1 + min(side[r][c + 1], side[r + 1][c], side[r][c])`; track the maximum.
3. Return the maximum squared.

### Correctness

The same covering argument as above, with the three neighbors above, to the left and above-left. Row-major order fills all three before the cell; `'0'` cells keep 0.

### Complexity

- Time: O(m * n) — constant work per cell.
- Space: O(m * n) — the table.

### Trade-offs

Simple loops and no recursion; the table could also answer "how many squares end here" (summing it counts all all-ones squares, a common follow-up).

### Pitfalls and edge cases

- The padded table is shifted by one: cell `(r, c)` lives at `side[r + 1][c + 1]`.
- Without padding, the first row and column need special cases (their value is just 1 for a `'1'`).

### Language notes

- Python and TypeScript: nested arrays; Java and Kotlin: zero-initialized `int[][]` and `IntArray` rows; Kotlin destructures `withIndex()` for the row and column.
- Go and Rust: zero-initialized rows (`make` per row, and `vec![vec![0; columns + 1]; rows + 1]`). The border row and column at index 0 mean the cell at `(r, c)` reads `side[r][c]`, `side[r][c + 1]` and `side[r + 1][c]` without a bounds test, and without a `usize` subtraction at the edge in Rust.

## Approach: rolling-array (One row of square sides plus the diagonal value)

### Intuition

The table's row `r` reads only row `r - 1`. One array is enough if the upper-left neighbor is saved before it is overwritten: when cell `c` is processed, `side[c]` still holds the value from the row above, `side[c - 1]` already holds the current row, and the old `side[c - 1]` (the diagonal) was saved one step earlier.

### Algorithm

1. Set `side` to `n + 1` zeros and `best = 0`.
2. For each row, set `diagonal = 0`; for each column `c` from 1: save `above = side[c]`; set `side[c]` to `1 + min(above, side[c - 1], diagonal)` for a `'1'`, else 0; update `best`; set `diagonal = above`.
3. Return `best` squared.

### Correctness

Invariant: after processing cell `(r, c)`, `side[c + 1]` holds the table value for `(r, c)`, entries to its right hold row `r - 1`, and `diagonal` holds the row-`(r - 1)` value of column `c`. So each update reads exactly the three neighbors the recurrence needs. Writing 0 for `'0'` cells matters, because the array still holds the row above there.

### Complexity

- Time: O(m * n) — the same work as the table.
- Space: O(n) — one row (about sqrt of the number of cells for square-ish grids).

### Trade-offs

The memory-optimal version and a frequent interview follow-up. The saved diagonal is the only subtle part; using two rows instead is equally fast and harder to get wrong.

### Pitfalls and edge cases

- Reset `diagonal` to 0 at the start of every row (it stands for the border column).
- Save `above` before writing `side[c]`; using `side[c - 1]` as the diagonal is wrong because it was already overwritten.

### Language notes

- The four references share the loop; TypeScript uses `Int16Array`, Java `int[]`, Kotlin `IntArray`, Python a list.
- Go and Rust share it too, over a `[]int` or `Vec<i32>`. The side for column `c` lives at `side[c + 1]`, so the left neighbor `side[c]` needs no subtraction; Rust's `for (c, &cell) in row.iter().enumerate()` gives the column and the cell together.
