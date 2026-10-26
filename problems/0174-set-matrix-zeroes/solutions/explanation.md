# Set Matrix Zeroes: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| zero-sets | brute | O(m * n) | O(m + n) | default when O(m + n) memory is acceptable; simplest correct version |
| in-place-markers | optimal | O(m * n) | O(1) | the follow-up asks for constant extra memory |

Both run in two phases: first decide which rows and columns to clear, then clear them. Doing both at once is the classic bug: a freshly written 0 looks like an original one and keeps spreading until the matrix is all zeros.

## Approach: zero-sets (Record the zero rows and columns in two sets)

### Intuition

A cell ends up 0 exactly when its row or its column contained an original 0. So scan once to collect those rows and columns, and scan again to clear every cell in them.

### Algorithm

1. Scan every cell; for each 0 at `(r, c)`, add `r` to `zero_rows` and `c` to `zero_cols`.
2. Scan every cell again; set it to 0 if its row is in `zero_rows` or its column is in `zero_cols`.

### Correctness

Step 1 reads only original values, because nothing has been written yet, so the two sets hold exactly the rows and columns that contain an original 0. Step 2 then applies the rule from the statement to every cell, and its own writes never influence the sets.

### Complexity

- Time: O(m * n) — two passes, each with O(1) work per cell.
- Space: O(m + n) — at most one entry per row and per column.

### Trade-offs

Clear and hard to get wrong. A full copy of the matrix would also work but uses O(m * n) memory; the sets keep only what matters. The in-place version saves the remaining O(m + n) at the cost of trickier bookkeeping.

### Pitfalls and edge cases

- Never clear rows during the first scan; later cells of a cleared row would then look like original zeros.
- A matrix without zeros must come back unchanged.

### Language notes

- Python and Kotlin: hash sets of indexes. Java: two `boolean[]` arrays, one flag per row and column, which are sets over a small index range and avoid boxing.
- TypeScript: `Set<number>` and `forEach` with indexes.

## Approach: in-place-markers (Use the first row and column as markers)

### Intuition

The flags from the previous approach can live inside the matrix: cell `(r, 0)` can say "clear row r", and cell `(0, c)` "clear column c". Writing a 0 there is harmless, because a cell used as a marker belongs to a row (or column) that is cleared anyway. One cell is claimed twice: `(0, 0)` would have to mark both row 0 and column 0. Let it mark row 0, and keep one extra boolean for column 0.

### Algorithm

1. For every row `r`: if `matrix[r][0]` is 0, set `first_col_has_zero`. For every `c >= 1` with `matrix[r][c] == 0`, set `matrix[r][0] = 0` and `matrix[0][c] = 0`.
2. For every row `r` from the bottom up:
   1. For every `c >= 1`, set `matrix[r][c] = 0` if `matrix[r][0] == 0` or `matrix[0][c] == 0`.
   2. If `first_col_has_zero`, set `matrix[r][0] = 0`.

### Correctness

After step 1, `matrix[r][0]` is 0 exactly when row `r` contained an original 0: an inner zero wrote it, and a zero at `(r, 0)` was already there. Likewise `matrix[0][c]` is 0 for `c >= 1` exactly when column `c` contained an original 0, and `first_col_has_zero` records column 0. Marking only overwrites cells with 0 in rows or columns that must be cleared, so it never invents a new reason to clear. Step 2 applies the rule to every cell. It visits row 0 last, so the column markers in row 0 are still intact while the lower rows read them; within a row, the row's own marker at column 0 is read for the inner cells before step 2.2 may overwrite it.

### Complexity

- Time: O(m * n) — two passes over the matrix.
- Space: O(1) — one boolean.

### Trade-offs

Meets the strictest memory follow-up and is the expected final answer in interviews. The order of the second pass is everything: clearing row 0 or column 0 before the other cells have read their markers spreads zeros too far. In production code the set-based version is usually preferred for readability.

### Pitfalls and edge cases

- Using `matrix[0][0]` for both row 0 and column 0 without the extra boolean clears column 0 whenever row 0 had a zero (or the other way round).
- Running the second pass top-down overwrites the column markers in row 0 before the rows below read them, unless row 0 is handled separately at the end.
- Single-row and single-column matrices work unchanged: the inner loops are empty, and the flag and `matrix[0][0]` carry all the information.

### Language notes

- All four references use the same two passes with plain index loops (`range(rows - 1, -1, -1)`, `downTo` in Kotlin). The bottom-up loop also keeps the Java version free of a separate first-row branch; an earlier variant with one boolean per first line crashed the runner's GraalVM CE 21.0.2 JIT under the bench, while this shape runs cleanly.

