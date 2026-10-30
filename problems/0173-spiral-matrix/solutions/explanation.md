# Spiral Matrix: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| visited-walk | brute | O(m * n) | O(m * n) | you want to simulate the rule literally, or as a correctness oracle |
| shrinking-bounds | optimal | O(m * n) | O(1) | default answer |

Both read every cell once, so their time is the same; the difference is the visited grid. Space counts extra memory beyond the `m * n` output, which every approach must produce.

## Approach: visited-walk (Walk and turn right at walls or visited cells)

### Intuition

The statement already describes an algorithm: walk forward, and turn clockwise when the next cell is outside the matrix or already read. Remembering which cells were read makes "already read" a lookup.

### Algorithm

1. Keep a `visited` grid, a position `(r, c) = (0, 0)` and a heading index into the clockwise list right, down, left, up.
2. Repeat `m * n` times:
   1. Append `matrix[r][c]` and mark it visited.
   2. If the next cell in the current heading is outside the matrix or visited, turn: `heading = (heading + 1) % 4`.
   3. Step to the next cell in the (possibly new) heading.

### Correctness

The loop follows the rule from the statement step by step, so it produces the spiral as long as one turn is always enough. It is: the spiral never paints itself into a corner before the last cell, because after a turn it walks along the inside of the cells read in the previous pass, and the cell straight ahead after a turn is always unread until the matrix is exhausted. The loop runs exactly `m * n` times and each iteration reads one unread cell, so every cell is read exactly once.

### Complexity

- Time: O(m * n) — constant work per cell.
- Space: O(m * n) — the visited grid.

### Trade-offs

Faithful to the statement and easy to adapt (other turning rules, other start points), which makes it a good oracle. The visited grid doubles the memory; the bounds approach keeps the same information in four integers.

### Pitfalls and edge cases

- Check the bounds before reading `visited[nr][nc]`; in Python a negative index silently wraps to the other side.
- Run the loop exactly `m * n` times instead of "until stuck"; the last step may compute a next cell that does not exist, which is harmless only if it is never read.

### Language notes

- Go: the headings are a `[4][2]int` array indexed by `heading`, and `for range rows * cols` (Go 1.22) repeats the body once per cell. Go's `int` coordinates can go negative, so the bounds test is a plain comparison before the `visited` lookup.
- Rust: coordinates are `usize`, so a step to row -1 cannot be written as `r + dr`; `checked_add_signed` returns `None` instead of underflowing, and the helper `step` folds the bounds test into that `Option`. `.filter(|&(nr, nc)| !visited[nr][nc])` then drops a visited cell, and `None` means turn right.

## Approach: shrinking-bounds (Peel the outer ring while shrinking four bounds)

### Intuition

The spiral is a sequence of rings. The unread cells always form a rectangle between four bounds: `top`, `bottom`, `left` and `right`. Reading the rectangle's border clockwise and then moving all four bounds inward produces the spiral ring by ring, with no visited marks at all.

### Algorithm

1. Set `top = 0`, `bottom = m - 1`, `left = 0`, `right = n - 1`.
2. While `top <= bottom` and `left <= right`:
   1. Read row `top` from `left` to `right`.
   2. Read column `right` from `top + 1` to `bottom`.
   3. If `top < bottom` and `left < right`: read row `bottom` from `right - 1` down to `left`, then column `left` from `bottom - 1` up to `top + 1`.
   4. Move every bound one step inward.

### Correctness

Invariant: at the start of each iteration, the unread cells are exactly the rectangle `[top, bottom] x [left, right]`, and everything read so far is in spiral order. Steps 2.1 to 2.3 read that rectangle's border clockwise, starting at its top-left corner, which is exactly where the spiral continues; each border cell is read once because the passes start one cell after the previous pass ends. When the rectangle is a single row or a single column, the border is just that row or column, and step 2.3 is skipped so it is not read again backwards. Removing the border leaves `[top + 1, bottom - 1] x [left + 1, right - 1]`, which restores the invariant; the loop stops when the rectangle is empty.

### Complexity

- Time: O(m * n) — each cell is read once.
- Space: O(1) — four bounds besides the output.

### Trade-offs

The standard answer: constant extra memory and no wasted lookups. The cost is careful bound handling for thin rectangles, which is where most bugs come from. The same skeleton generates a spiral (Spiral Matrix II) by writing instead of reading.

### Pitfalls and edge cases

- The guard `top < bottom and left < right` before the bottom and left passes is essential: without it a single remaining row is read twice (forward, then backward), and so is a single column.
- Using `<` instead of `<=` in the loop condition drops the last ring when it is a single row, column or cell (odd sides).
- The left pass stops at `top + 1`, because the corner `(top, left)` was the first cell read in this ring.

### Language notes

- Python: slicing reads the top row in one call (`matrix[top][left : right + 1]`); generator expressions feed the other passes to `extend`.
- TypeScript: four plain loops; `push` grows the output array.
- Java: the output size is known in advance (`m * n`), so the reference fills an `int[]` with a write index instead of boxing into a list.
- Kotlin: `downTo` writes the backward passes directly (`right - 1 downTo left`); the reference collects into an `ArrayList<Int>` and converts with `toIntArray()` (an `IntArray` with a write index, as in Java, would avoid boxing).
- Go: `append(order, matrix[top][left:right+1]...)` copies the top row in one call, and the four bounds are signed `int`s that may go to -1 on the last ring, as in the Python reference.
- Rust: closed bounds would make `bottom` and `right` reach -1, which a `usize` cannot hold, so the reference uses half-open bounds (`bottom` and `right` are one past the last row and column) and the ring tests become `bottom - top > 1` and `right - left > 1`. `extend_from_slice` copies the top row, and the `.iter().rev()` chains walk the backward passes.
