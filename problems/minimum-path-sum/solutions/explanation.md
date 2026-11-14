# Minimum Path Sum: Explanation

## Overview

Let m be the number of rows and n the number of columns. Both approaches use the same fact: the robot enters every block, except the start, from the block above or the block on the left, so the cheapest way to a block is its own toll plus the cheaper of the cheapest ways to those two neighbours.

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| memoization | intermediate | O(m * n) | O(m * n) | you think top-down: "what is the cheapest way to the goal?" |
| tabulation | optimal | O(m * n) | O(m * n) | default answer: fill the table row by row, with no recursion |

Without the memo table, the recursion would recompute the same blocks again and again and take time proportional to the number of routes, which grows exponentially with the size of the grid. Both approaches here remove that repetition.

## Approach: memoization (Recursion from the goal cell with a memo table)

### Intuition

Ask the question for the goal block: what is the cheapest total toll to arrive here? The robot came from the block above or the block on the left, so the answer is this block's toll plus the smaller of the answers for those two blocks. Each of those is the same question about a smaller grid, so ask it recursively, and write every answer in a table the first time it is found. A block asked about again reads its answer from the table instead of recursing.

### Algorithm

1. Create a table `cheapest` with the shape of the grid, filled with a marker for "not computed yet".
2. Define `cheapestTo(r, c)`:
   1. If `cheapest[r][c]` is computed, return it.
   2. The top-left block has no way in, so its arrival cost is 0. A block in the top row can only come from the left, and a block in the left column only from above. Any other block takes the smaller of `cheapestTo(r - 1, c)` and `cheapestTo(r, c - 1)`.
   3. Store the arrival cost plus `grid[r][c]` in `cheapest[r][c]` and return it.
3. Return `cheapestTo(m - 1, n - 1)`.

### Correctness

By induction on `r + c`. The top-left block's cheapest total is its own toll. For any other block, every route to it ends with a move from the block above or the block on the left, and the part of the route before that move is itself a route to that neighbour. So the cheapest route to the block is its toll plus the cheaper of the two neighbours' cheapest routes, and the recursion computes exactly that. The table only stores values that the recursion would return again, so it changes the speed and not the result.

### Complexity

- Time: O(m * n) — each block's answer is computed once, with a constant amount of work besides the recursive calls, and every later request reads the table.
- Space: O(m * n) — the table has one entry per block, and the recursion goes at most m + n - 1 calls deep.

### Trade-offs

The code mirrors the definition, which makes it the easiest to trust and the oracle here. It pays for a call stack up to m + n deep, which is harmless at 200 by 200 but is a limit on much larger grids. It also computes only the blocks the goal depends on, which here is all of them. The tabulation reads the same recurrence without recursion.

### Pitfalls and edge cases

- The top row and left column have only one neighbour; reading `row - 1` or `column - 1` there would run off the grid.
- The start block's toll counts, and so does the goal block's toll.
- A toll of 0 is a valid value, so use a marker such as -1 for "not computed", never 0.
- A one-cell grid answers with that cell's toll.

### Language notes

- Python: a nested function reads `grid` and `cheapest` from the enclosing scope. The recursion is at most m + n - 1 calls deep, which is 399 for the largest grid and well within the interpreter's default recursion limit (1000 in CPython 3.13).
- TypeScript: `Array.from` builds the table row by row so the rows are separate arrays; `fill` on an outer array would share one row.
- Java: `Arrays.fill` sets each row of the table to the marker, and a private helper method carries the grid and the table.
- Kotlin: `Array(rows) { IntArray(columns) { unknown } }` builds the table with the marker already in it; `minOf` picks the smaller value.
- Go: the table is a slice of slices, each row allocated separately. The built-in `min`, added in Go 1.21, picks the smaller value.
- Rust: the helper takes the table as `&mut [Vec<i32>]`, so the two recursive calls are made one after the other and stored in `above` and `left` before `min` is applied. Indexes are `usize`, which is why the top row and left column are tested before subtracting 1.

## Approach: tabulation (Fill the table of cheapest costs row by row)

### Intuition

The memoized recursion asks about a block only after the two blocks above and to the left of it. So there is no need to recurse: visit the blocks in an order where those two are already known, which row by row from the top-left gives. The table cell `cheapest[r][c]` holds the cheapest total toll of any route from the top-left block to that block, its own toll included.

### Algorithm

1. Create a table `cheapest` with the shape of the grid.
2. For each row `r` from top to bottom, and each column `c` from left to right:
   1. If `(r, c)` is the top-left block, the arrival cost is 0.
   2. If `r == 0`, the arrival cost is `cheapest[r][c - 1]`; if `c == 0`, it is `cheapest[r - 1][c]`.
   3. Otherwise, it is the smaller of `cheapest[r - 1][c]` and `cheapest[r][c - 1]`.
   4. Set `cheapest[r][c]` to the arrival cost plus `grid[r][c]`.
3. Return `cheapest[m - 1][n - 1]`.

### Correctness

Invariant: when the loop reaches `(r, c)`, every cell above it and to its left is already filled with the cheapest total toll of a route to that block. The cell above is in an earlier row, and the cell on the left is earlier in the same row. The same argument as in the memoization then shows that the new cell is correct: every route to `(r, c)` ends with a move from one of those two neighbours. The last cell, which the loop fills last, is the answer.

### Complexity

- Time: O(m * n) — the two loops visit each block once and do constant work for each.
- Space: O(m * n) — the table of cheapest totals.

### Trade-offs

The same time as the memoization with no recursion, so no stack limit and a smaller constant. Because each row reads only the previous row and the cell to its left, one row of n numbers would be enough and bring the space down to O(n); the full table is kept here because it shows every cell's meaning, and because the full table lets you walk back from the goal to recover the route.

### Pitfalls and edge cases

- Visit the blocks in an order where the neighbours are ready. Filling column by column works too, but filling in any order that reaches a block before its neighbours does not.
- Treat the first row and the first column as special cases rather than reading a block outside the grid.
- Add the block's own toll for every cell, not only for the neighbours' sum; forgetting the start block's toll is the usual off-by-one.
- The largest answer is 399 blocks of toll 100, which is 39,900, so it fits easily in a 32-bit integer.

### Language notes

- Python: `[[0] * columns for _ in range(rows)]` builds separate rows; `[[0] * columns] * rows` would repeat one row.
- TypeScript: `Array.from({ length: rows }, () => new Array<number>(columns).fill(0))` builds separate rows, and `Math.min` picks the smaller value.
- Java and Kotlin: `new int[rows][columns]` and `Array(rows) { IntArray(columns) }` start at 0, so the table needs no filling.
- Go: each row is allocated with `make([]int, columns)`; the built-in `min`, added in Go 1.21, picks the smaller value, and `switch` with no tag reads as the chain of conditions.
- Rust: `vec![vec![0; columns]; rows]` clones the inner vector, so each row is separate. The `min` method on `i32` picks the smaller value.
