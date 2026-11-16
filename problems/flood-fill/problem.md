# Flood Fill

## Statement

A courtyard is paved with square tiles laid out in rows and columns. The paving plan is a grid of whole numbers, and each number is the color of one tile. You repaint a single tile with a new color, and the repaint spreads: every tile that is joined to it through tiles of its original color gets the new color too.

Two tiles are joined when they are neighbors. A tile has up to four neighbors: the tile above it, below it, to its left and to its right. Tiles that only touch at a corner are not neighbors, and a tile on an edge of the grid simply has fewer neighbors, because nothing exists past the edge. The tiles that get repainted are those you can reach from the starting tile by stepping from neighbor to neighbor without ever leaving the original color. We call that set of tiles the region of the starting tile.

Given the grid, the position of the tile to repaint and the new color, return the grid after the repaint. Tiles outside the region keep their color, even when they have the same color as the region but are cut off from it.

If the new color is the same as the starting tile's color, nothing changes and you return the grid as it is.

Reference: this is our own wording of LeetCode problem 733, [Flood Fill](https://leetcode.com/problems/flood-fill/).

## Input

- `grid`: the paving plan, with `m` rows and `n` columns; `grid[r][c]` is the color of the tile in row `r` and column `c`, counting from 0 at the top left.
- `row`, `col`: the position of the tile to repaint.
- `newColor`: the color to paint with.

## Output

The grid after the repaint, with the same dimensions as the input.

## Examples

### Example 1

<!-- case: ex1 -->

The tile at row 1, column 1 has color 1, and the color-1 tiles connected to it are the whole top-left block: three tiles in the top row, two in the middle row and the tile at the bottom left. All of them become 7. The tile with color 1 at the bottom right looks like it belongs, but its neighbors above and to its left are different colors, so the repaint cannot reach it.

### Example 2

<!-- case: ex2 -->

The tile at row 0, column 0 already has color 3, so painting it with 3 changes nothing. This is a case to handle on purpose: a fill that looks for "tiles with the old color" would keep finding the tiles it has just repainted, because their color now equals the old one.

## Constraints

- `1 <= m, n <= 50`
- `0 <= grid[r][c], newColor <= 10^4`
- `0 <= row < m` and `0 <= col < n`

## Follow-ups

- Which tiles does your fill look at twice, and what stops it from looping forever?
- A fill written as a function that calls itself can go as deep as the region is large. What would you use instead if the grid had a million tiles?
- Can you do the fill without writing a separate array that records which tiles were visited?

## Hints

### Hint 1

Think of the grid as a map where each tile is a place, and each pair of side-by-side tiles with the same color is a path between two places. The task is to visit every place you can walk to from the start.

### Hint 2

Whatever you do for the starting tile, you will also do for each of its neighbors that belong to the region, and then for their neighbors. What must a neighbor satisfy to belong to the region? Do not forget the neighbors that do not exist because they would fall outside the grid.

### Hint 3

Remember the original color in a variable before you repaint anything. Repainting a tile is also what marks it as visited, because it no longer has the original color. That only works when the new color differs from the original, so check that case first.

### Hint 4

Two ways to organize "look at the neighbors in turn" both work. A function that repaints a tile and then calls itself on the four neighbors explores one direction as far as it can before coming back (depth-first). A queue of tiles waiting to be processed explores tile by tile in rings around the start (breadth-first).
