# Maximal Rectangle: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| widths-walk-up | brute | O(m^2 * n) | O(m * n) | small grids, or as a correctness oracle |
| histogram-stack | optimal | O(m * n) | O(n) | default answer: reuses the histogram problem |
| left-right-dp | optimal | O(m * n) | O(n) | a pure DP formulation without a stack |

Here m and n are the number of rows and columns. Every approach reduces the two-dimensional search to one-dimensional quantities that are carried from row to row: run widths, column heights, or height together with left and right boundaries. Checking every rectangle directly would cost O(m^2 * n^2) candidates, each with its own check; it is not among the references.

The time classes use the side length as n; the generated grids have one side n and the other between 3n/4 and n, so the optimal approaches are quadratic and the walk-up is cubic in n.

## Approach: widths-walk-up (Run widths per row with a walk up from every cell)

### Intuition

Record, for every cell, how many consecutive ones end there in its row: its run width. A rectangle with bottom-right corner `(r, c)` that spans rows `top..r` can be at most as wide as the narrowest of those rows' widths at column `c`. So fix the corner and walk up row by row, keeping the running minimum width.

### Algorithm

1. For each cell `(r, c)` holding a one, set `width[r][c] = width[r][c - 1] + 1` (or 1 in column 0).
2. Walk `top` from `r` upwards, setting `narrowest = min(narrowest, width[top][c])`, and update the best area with `narrowest * (r - top + 1)`; stop when `narrowest` reaches 0.
3. Return the best area.

### Correctness

Any all-ones rectangle has a bottom-right corner `(r, c)` and a top row `top`; its width `w` is at most the run width of every row it spans at column `c`, so `w <= narrowest` for that `top`, and the rectangle of width `narrowest` over the same rows is all ones and at least as large. The walk considers every `(r, c, top)` until a zero makes all taller rectangles impossible, so it finds the maximum.

### Complexity

- Time: O(m^2 * n) — each of the m * n cells may walk up through all rows above it.
- Space: O(m * n) — the table of run widths.

### Trade-offs

Simple and correct, which makes it the oracle; it is also the natural first idea in an interview. On a grid that is nearly all ones every walk is long, about 4 million steps at 200 by 200.

### Pitfalls and edge cases

- Stop walking at the first zero width: nothing taller can include that row.
- The cells are characters; compare with `'1'` and `'0'`.

### Language notes

- Python: a list-of-lists of widths; TypeScript: `Int32Array` rows; Java and Kotlin: `int[][]` and `Array<IntArray>`, with a `while` loop in Kotlin for the walk.

## Approach: histogram-stack (Column heights per row and a monotonic stack)

### Intuition

Fix the bottom row of the rectangle. For every column, count the consecutive ones that end in that row: these heights form a histogram, and the all-ones rectangles resting on the row are exactly the rectangles inside that histogram. So the answer is the best "largest rectangle in a histogram" over all rows. The heights update in O(1) per cell from the previous row, and each histogram is solved in linear time with a monotonic stack.

### Algorithm

1. Set `heights` to zeros.
2. For each row: set `heights[c] = heights[c] + 1` on a one and 0 on a zero; then compute the largest rectangle of the histogram:
   1. For `index` from 0 to `n` (height 0 at `n`): while the stack's top bar is at least as high, pop it and score `height * (index - below - 1)`, where `below` is the new top (or -1).
   2. Push `index`.
3. Return the best score over all rows.

### Correctness

A rectangle of ones with bottom row `r` spanning columns `a..b` and `h` rows fits under the histogram of row `r` (every column in `a..b` has height at least `h`), and conversely every rectangle under the histogram is all ones. The stack procedure returns the largest rectangle in a histogram: for every bar it finds the nearest strictly lower bars on both sides (see Largest Rectangle in Histogram), and the best rectangle uses the full width between those boundaries at the height of its lowest bar. Taking the maximum over all bottom rows covers every rectangle.

### Complexity

- Time: O(m * n) — each row updates n heights and runs a linear stack pass.
- Space: O(n) — the heights and the stack.

### Trade-offs

The standard answer, and a good example of reducing a 2D problem to a known 1D one. It needs the histogram algorithm, which is itself the tricky part; the left-right DP avoids the stack at the cost of three arrays and a less obvious invariant.

### Pitfalls and edge cases

- Reset a column's height to 0 on a zero; the rectangle cannot pass through it.
- Do not forget the sentinel bar of height 0, or bars still on the stack are never scored.

### Language notes

- Python: a list as the stack inside a helper function.
- TypeScript and Java: a reusable primitive array of `n + 1` entries with a size counter, allocated once for all rows.
- Kotlin: `ArrayDeque<Int>` in a private top-level helper.

## Approach: left-right-dp (Height, left and right boundary arrays)

### Intuition

For each column `c` of the current row, look at the vertical run of ones ending here, of height `height[c]`. Push it sideways as far as possible: it can extend left and right as long as every column it enters has at least the same run of ones. Track that stretch as `left[c]` (inclusive) and `right[c]` (exclusive). Moving down one row, the stretch of a continuing column can only shrink: it is limited both by the previous row's stretch and by the zeros in the current row.

### Algorithm

1. Start with `height = 0`, `left = 0` and `right = n` for every column.
2. For each row:
   1. Left to right, with `boundary` the first column after the last zero: on a one, `height[c] += 1` and `left[c] = max(left[c], boundary)`; on a zero, `height[c] = 0`, `left[c] = 0` and `boundary = c + 1`.
   2. Right to left, with `boundary` the last zero seen: on a one, `right[c] = min(right[c], boundary)`; on a zero, `right[c] = n` and `boundary = c`.
   3. Update the best area with `height[c] * (right[c] - left[c])` for every column.
3. Return the best area.

### Correctness

Invariant: after row `r`, for every column `c` with `height[c] > 0`, columns `left[c] .. right[c] - 1` all have at least `height[c]` consecutive ones ending in row `r`, and the stretch cannot be extended. It holds for the first row (the stretch is the run of ones in the row). For the next row, the run of height `height[c] + 1` needs every column in the stretch to have a one in this row and a run of at least `height[c]` above, which is the intersection of the old stretch with the current row's run around `c`: exactly the `max` and `min` updates. Resetting a zero column to the full range is harmless because its height is 0 and the next one restarts the intersection. Every maximal rectangle has a column where its height equals that column's run and its sides equal that column's stretch, so the best `height * width` finds it.

### Complexity

- Time: O(m * n) — three passes over each row.
- Space: O(n) — three arrays of length n.

### Trade-offs

No stack, just three linear passes per row, and it frames the problem as a row-to-row DP. The invariant is harder to explain than the histogram reduction, so in an interview the histogram approach is usually the clearer story.

### Pitfalls and edge cases

- On a zero, reset `left` to 0 and `right` to `n` (the widest range), not to the boundary: otherwise the next row's intersection is wrongly narrow.
- `right` is exclusive; the width is `right - left`, without `+ 1`.

### Language notes

- The four references share the passes; TypeScript uses `Int32Array`s with `fill(columns)`, Java `Arrays.fill`, Kotlin `IntArray(columns) { columns }`.
