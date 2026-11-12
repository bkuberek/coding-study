# Minimum Path Sum

## Statement

A delivery robot crosses a city laid out as a grid of blocks. Standing on a block costs a toll: `grid[r][c]` is the toll of the block in row `r` and column `c`, counting from 0 at the top-left corner.

The robot starts on the top-left block and must reach the bottom-right block. Each move takes it one block to the right or one block down; it never moves left or up, and it never leaves the grid. It pays the toll of every block it stands on, the first and the last included.

Return the smallest total toll the robot can pay on its way from the top-left block to the bottom-right block.

Reference: this is our own wording of LeetCode problem 64, [Minimum Path Sum](https://leetcode.com/problems/minimum-path-sum/).

## Background

This is a first problem on **dynamic programming** (DP): solving a question by answering smaller versions of it first and writing each answer down, so that nothing is worked out twice. When the smaller versions are named by two numbers, such as a row and a column, the written-down answers form a table with the same shape as the grid, and this is called 2D DP.

To see what a table means cell by cell, take a different question on a small grid: *in how many ways can the robot get from the top-left block to each block?* Let `ways[r][c]` be that number for the block in row `r` and column `c`. A table cell is always defined by a sentence like that one, and every cell must keep its sentence true.

- The top-left block has exactly one way to be reached: the robot is already there. So `ways[0][0] = 1`.
- A block in the top row can only be entered from its left neighbour, because there is no block above it. The robot has no other choice, so it has the same number of ways as that neighbour.
- A block in the left column is the mirror image: it can only be entered from above.
- Any other block can be entered from the block above it or from the block to its left, and those two ways are different. So its number of ways is the sum of its two neighbours' numbers.

For a grid with 2 rows and 3 columns, the table fills in from the top-left:

```
ways:   1  1  1
        1  2  3
```

The block in row 1, column 2 has 2 + 1 = 3 ways, because the robot can arrive from the block on its left (2 ways) or from the block above it (1 way). The answer to the whole question sits in the last cell. Each cell is filled once from cells already filled, so the table is built in a single pass over the grid.

Your question asks for a cheapest total instead of a count, and every block has a toll. The idea is the same, but you must decide what a cell's sentence says and how two neighbours' numbers combine into a cell's number.

## Input

- `grid`: the tolls, `grid[r][c]` being the toll of the block in row `r` and column `c`; every row has the same length

## Output

The smallest possible sum of the tolls of the blocks on a route from the top-left block to the bottom-right block, moving only right or down.

## Examples

### Example 1

<!-- case: ex1 -->

Going right along the top row and then straight down looks cheap but is not the best. The best route pays 6 + 1 + 2 + 2 + 4 + 7 = 22: right, right, down, down, right. Written as a table of "cheapest total toll to arrive at each block", the grid fills in as 6, 7, 9, 10 in the top row, then 9, 16, 11, 16 in the middle row, then 10, 12, 15, 22 in the bottom row; the answer is its last cell.

### Example 2

<!-- case: ex2 -->

With a single row the robot has no choice: it walks right and pays 5 + 2 + 9.

## Constraints

- `1 <= grid.length, grid[r].length <= 200`
- `0 <= grid[r][c] <= 100`

## Follow-ups

- Recursion that tries both moves from every block repeats the same sub-grids over and over. Which results can you reuse?
- The table only ever reads the row above and the cell to the left. Can you keep a single row of numbers?
- How would you recover the route itself, not just its total toll?

## Hints

### Hint 1

Pick a block in the middle of the grid. The robot only moves right or down, so which blocks could it have been standing on one move earlier?

### Hint 2

Suppose someone told you the cheapest total toll for reaching each of those earlier blocks. How would you work out the cheapest total toll for reaching this block?

### Hint 3

Make a table with the same shape as the grid, where cell `(r, c)` holds the cheapest total toll of any route from the top-left block to that block, its own toll included. The top-left cell is just its own toll, and the first row and first column each have only one block to come from. Fill the table row by row, so that the cells you need are always ready.

### Hint 4

For any cell with both neighbours, `table[r][c] = grid[r][c] + min(table[r - 1][c], table[r][c - 1])`. In the first row only the left neighbour exists, and in the first column only the one above. The answer is the bottom-right cell of the table.
