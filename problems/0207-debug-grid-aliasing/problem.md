# Debug: Grid Aliasing

## Statement

A wildfire model stores a terrain map as a grid. Each cell holds `0` (a firebreak, which never burns), `1` (dry brush) or `2` (burning at minute 0). Every minute, each burning cell sets fire to its brush neighbors directly above, below, left and right. A cell that catches fire during minute `t` starts spreading during minute `t + 1`.

The function `burnTimes` you start from should return a grid of the same shape that holds, for every cell, the minute at which it starts burning: `0` for cells burning at the start, and `-1` for cells that never burn (firebreaks, and brush the fire cannot reach). The code simulates the fire minute by minute, building each minute's map from the previous one. It passes some tests and fails others. Find the bugs and fix them.

### Bug report

> **Title:** Burn-time map shows identical rows, and the fire outruns the clock
>
> The evacuation dashboard renders the burn-time grid from `burnTimes`. Two things look wrong. On most maps, every row of the result is identical, as if the whole grid were one row repeated, even when the terrain differs from row to row. The second complaint came in after a quick patch to the result grid was tested locally: on a single-row map with the fire at the left end, `[[2, 1, 1, 1]]`, the dashboard says the whole row is burning by minute 1. Fire that has to cross three cells cannot arrive in one minute. The terrain grid that callers pass in also looks different after the call.

## Input

- `grid`: an `m x n` terrain map of `0` (firebreak), `1` (brush) and `2` (burning at minute 0)

## Output

An `m x n` grid of integers: the minute each cell starts burning, `0` for initially burning cells, and `-1` for cells that never burn.

## Examples

### Example 1

<!-- case: ex1 -->

The fire starts in the top-left corner. It reaches `(0, 1)` and `(1, 0)` in minute 1, `(0, 2)` and `(1, 1)` in minute 2, `(2, 1)` in minute 3 and `(2, 2)` in minute 4. The two firebreaks stay at `-1`. The code as shipped gets this wrong.

### Example 2

<!-- case: ex2 -->

The fire spreads both ways from the middle in minute 1. The firebreak at index 3 stops it, so the brush at index 4 never burns. This case passes as shipped: a single row hides one of the bugs, and the fire never gets two cells to the right in a row, which hides the other.

## Constraints

- `1 <= m, n <= 50`
- `grid[i][j]` is `0`, `1` or `2`
- The function must not modify `grid`.

## Follow-ups

- The minute-by-minute simulation copies the whole grid every minute. Can you compute every burn time in one pass over the cells?
- How would you return only the minute at which the last cell catches fire, or `-1` when some brush never burns?

## Hints

### Hint 1

Start with the first complaint. Write to one cell of the result grid and print the whole grid. How many cells changed?

### Hint 2

Which line creates the result grid? How many distinct row objects does it create: `m`, or one?

### Hint 3

After fixing the rows, reproduce the second complaint with `[[2, 1, 1, 1]]`. Print the current map after every cell you visit during minute 1. When does a cell that only just caught fire get to spread in the same minute?

### Hint 4

A copy of a grid is only independent if each row is copied too. Which copy in the code duplicates the outer list but shares the rows?
