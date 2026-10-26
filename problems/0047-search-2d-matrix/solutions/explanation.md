# Search a Sorted Matrix: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| full-scan | brute | O(m * n) | O(1) | the grid is tiny, or as a correctness oracle |
| staircase | intermediate | O(m + n) | O(1) | only rows and columns are sorted (the weaker follow-up property) |
| flattened | optimal | O(log(m * n)) | O(1) | default answer for this problem's ordering |

`m` is the number of rows and `n` the number of columns. On the size ladder, `n` is the number of cells, so the three approaches grow like n, sqrt(n) and log(n).

## Approach: full-scan (Check every cell)

### Intuition

Look at every cell and stop at the first one that equals `target`. The ordering is ignored entirely.

### Algorithm

1. For each row, for each value in the row, return `true` if it equals `target`.
2. Return `false`.

### Correctness

Every cell is compared before `false` is returned, so a present value is always found, and `true` is returned only on an equal cell.

### Complexity

- Time: O(m * n) — up to one comparison per cell. From 100 cells on, the generator places the target, present or absent, three quarters of the way through the cells, so at least three quarters of them are read at every seed.
- Space: O(1) — loop variables only.

### Trade-offs

It works on any grid, which makes it the oracle, but it treats sorted data as unsorted: 10^5 comparisons where 17 suffice.

### Pitfalls and edge cases

- None specific; it handles one-row and one-column grids naturally.

### Language notes

- Kotlin: `matrix.any { row -> row.any { it == target } }` short-circuits like the nested loops; `IntArray.any` does not box.
- Python: `any(target in row for row in matrix)` is the idiomatic one-liner, with `in` scanning each row in C.

## Approach: staircase (Walk from the top-right corner)

### Intuition

Stand on the top-right cell. Everything to its left in the same row is no larger, and everything below it in the same column is no smaller. If the cell is larger than `target`, its whole column below it is too, so the column can be dropped; if it is smaller, its whole row to the left is too, so the row can be dropped. Each step drops a row or a column.

### Algorithm

1. Start at `row = 0`, `column = n - 1`.
2. While `row < m` and `column >= 0`:
   1. If `matrix[row][column] == target`, return `true`.
   2. If it is larger than `target`, move left (`column -= 1`); otherwise move down (`row += 1`).
3. Return `false`.

### Correctness

Invariant: if `target` is present, it lies in the sub-grid of rows `row..m-1` and columns `0..column`. Moving left is safe because the current cell is the smallest cell of its column within that sub-grid, and it already exceeds `target`. Moving down is safe because the current cell is the largest cell of its row within the sub-grid, and it is below `target`. When the walk leaves the grid, the sub-grid is empty, so `target` is absent.

### Complexity

- Time: O(m + n) — every step either moves down one row or left one column, so there are at most m + n - 1 steps. With about sqrt(cells) rows and columns, that is O(sqrt(cells)).
- Space: O(1) — two indices.

### Trade-offs

Slower than the flattened binary search here, but it needs only "rows sorted and columns sorted", so it also solves the harder variant (LeetCode 240) where the row-to-row guarantee is missing and flattening is impossible. Knowing both, and when each applies, is a good interview signal.

### Pitfalls and edge cases

- Start at the top-right or bottom-left corner. From the top-left both moves increase the value, so a comparison does not tell you which way to go.
- Check `column >= 0` and `row < m` before reading a cell; the walk leaves the grid when the target is absent.
- Repeated values do not break it: an equal cell returns immediately, and strictly larger or smaller cells still justify the move.

### Language notes

- Kotlin: `matrix[0].lastIndex` is the last column; `when` with conditions keeps the three branches together.
- All languages: the walk only reads cells, so Java and Kotlin `int[][]` / `Array<IntArray>` rows are accessed without copying.

## Approach: flattened (Binary search over the row-major order)

### Intuition

The ordering rules say that reading the grid row by row gives one sorted sequence of length `m * n`. Position `p` of that sequence is the cell in row `p / n`, column `p % n`, so a binary search over positions works directly on the grid, without building the sequence.

### Algorithm

1. Set `low = 0`, `high = m * n - 1`.
2. While `low <= high`:
   1. Let `middle` be the midpoint and read `value = matrix[middle / n][middle % n]`.
   2. If `value == target`, return `true`.
   3. If `value < target`, set `low = middle + 1`; otherwise set `high = middle - 1`.
3. Return `false`.

### Correctness

The map from position to `(row, column)` is the row-major order, which is non-decreasing by the two ordering rules. Binary search on a non-decreasing sequence keeps the invariant "if `target` is present, some position holding it lies in `[low, high]`": when `value < target`, every position up to `middle` holds a value at most `value`, so no occurrence is there; the other branch is symmetric. The range shrinks each step, and an empty range means absent.

### Complexity

- Time: O(log(m * n)) — a binary search over m * n positions takes at most floor(log2(m * n)) + 1 probes, each O(1).
- Space: O(1) — indices only; nothing is copied.

### Trade-offs

The fastest option and the expected answer. An equivalent alternative is two binary searches, one over the first column to find the row and one inside that row; it has the same O(log m + log n) = O(log(m * n)) cost and is sometimes easier to explain, but it has two loops to get right instead of one.

### Pitfalls and edge cases

- Divide by the number of columns `n`, not by the number of rows: `middle / m` maps positions to the wrong cells whenever the grid is not square.
- `m * n` is at most 10^5 here; in general, a product of two `int` dimensions can overflow 32 bits, so a production version would compute it in 64 bits.
- One-row and one-column grids are just short sequences; no special case is needed.

### Language notes

- Python: `divmod(middle, columns)` returns row and column in one call.
- TypeScript: `/` is floating-point division, so the row needs `Math.floor(middle / columns)`; `%` on non-negative integers is exact.
- Java and Kotlin: integer `/` and `%` give row and column directly; `>>> 1` / `ushr 1` floors the midpoint.
