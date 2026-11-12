# Flood Fill

## Statement

A courtyard is paved with square tiles laid out in rows and columns. The paving plan is a grid of whole numbers, and each number is the colour of one tile. You repaint a single tile with a new colour, and the repaint spreads: every tile that is joined to it through tiles of its original colour gets the new colour too.

Two tiles are joined when they are neighbours. A tile has up to four neighbours: the tile above it, below it, to its left and to its right. Tiles that only touch at a corner are not neighbours, and a tile on an edge of the grid simply has fewer neighbours, because nothing exists past the edge. The tiles that get repainted are those you can reach from the starting tile by stepping from neighbour to neighbour without ever leaving the original colour. We call that set of tiles the region of the starting tile.

Given the grid, the position of the tile to repaint and the new colour, return the grid after the repaint. Tiles outside the region keep their colour, even when they have the same colour as the region but are cut off from it.

If the new colour is the same as the starting tile's colour, nothing changes and you return the grid as it is.

## Input

- `grid`: the paving plan, with `m` rows and `n` columns; `grid[r][c]` is the colour of the tile in row `r` and column `c`, counting from 0 at the top left.
- `row`, `col`: the position of the tile to repaint.
- `newColor`: the colour to paint with.

## Output

The grid after the repaint, with the same dimensions as the input.

## Examples

### Example 1

<!-- case: ex1 -->

The tile at row 1, column 1 has colour 1, and the colour-1 tiles connected to it are the whole top-left block: three tiles in the top row, two in the middle row and the tile at the bottom left. All of them become 7. The tile with colour 1 at the bottom right looks like it belongs, but its neighbours above and to its left are different colours, so the repaint cannot reach it.

### Example 2

<!-- case: ex2 -->

The tile at row 0, column 0 already has colour 3, so painting it with 3 changes nothing. This is a case to handle on purpose: a fill that looks for "tiles with the old colour" would keep finding the tiles it has just repainted, because their colour now equals the old one.

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

Think of the grid as a map where each tile is a place, and each pair of side-by-side tiles with the same colour is a path between two places. The task is to visit every place you can walk to from the start.

### Hint 2

Whatever you do for the starting tile, you will also do for each of its neighbours that belong to the region, and then for their neighbours. What must a neighbour satisfy to belong to the region? Do not forget the neighbours that do not exist because they would fall outside the grid.

### Hint 3

Remember the original colour in a variable before you repaint anything. Repainting a tile is also what marks it as visited, because it no longer has the original colour. That only works when the new colour differs from the original, so check that case first.

### Hint 4

Two ways to organise "look at the neighbours in turn" both work. A function that repaints a tile and then calls itself on the four neighbours explores one direction as far as it can before coming back (depth-first). A queue of tiles waiting to be processed explores tile by tile in rings around the start (breadth-first).
