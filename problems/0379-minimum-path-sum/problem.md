# Minimum Path Sum

## Statement

A delivery robot crosses a city laid out as a grid of blocks. Standing on a block costs a toll: `grid[r][c]` is the toll of the block in row `r` and column `c`, counting from 0 at the top-left corner.

The robot starts on the top-left block and must reach the bottom-right block. Each move takes it one block to the right or one block down; it never moves left or up, and it never leaves the grid. It pays the toll of every block it stands on, the first and the last included.

Return the smallest total toll the robot can pay on its way from the top-left block to the bottom-right block.

Reference: this is our own wording of LeetCode problem 64, [Minimum Path Sum](https://leetcode.com/problems/minimum-path-sum/).

## Background

This is a first problem on **dynamic programming** (DP): solving a question by answering smaller versions of it first and writing each answer down, so that nothing is worked out twice. When the smaller versions are named by two numbers, the written-down answers form a table with two indexes, a row and a column, and this is called 2D DP.

To see what a table means cell by cell, take a different question that has nothing to do with grids. A club has members numbered 1, 2, 3, ... in a list, and you want to know *in how many ways a team of exactly `j` members can be chosen from the first `i` members of the list*. Let `teams[i][j]` be that number. A table cell is always defined by a sentence like that one, and every cell must keep its sentence true.

- In row 0 there are no members to choose from. The only team that exists is the empty one, so `teams[0][0] = 1`, and `teams[0][j] = 0` for every `j` above 0.
- In column 0 the team has no members, and there is exactly one way to choose nobody. So `teams[i][0] = 1`.
- For any other cell, look at member `i`. Either member `i` is not on the team, and then all `j` members come from the first `i - 1`: that is `teams[i - 1][j]` ways. Or member `i` is on the team, and then the other `j - 1` come from the first `i - 1`: that is `teams[i - 1][j - 1]` ways. The two cases never describe the same team, so the cell is the sum of those two earlier cells.

For 4 members and teams of up to 3, the table fills in row by row:

```
teams:   j=0  j=1  j=2  j=3
i=0       1    0    0    0
i=1       1    1    0    0
i=2       1    2    1    0
i=3       1    3    3    1
i=4       1    4    6    4
```

The cell for 4 members and teams of 2 is 3 + 3 = 6: the cell directly above it (3 members, teams of 2) plus the cell above and to its left (3 members, teams of 1). Each cell is filled once, from cells that are already filled, so the table is built in a single pass, and the cell you were asked about sits at the end.

Your question asks for a cheapest total instead of a count, and the table is the same shape as the grid, one cell per block. Work out what a cell's sentence should say, which earlier cells a block can be reached from, and how their numbers combine with the block's toll into the cell's number.

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
