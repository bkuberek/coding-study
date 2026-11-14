# Shortest Path With Obstacle Removals

## Statement

You get a grid of `0`s and `1`s with `m` rows and `n` columns: `0` is an empty cell and `1` is an obstacle. You start in the top-left cell and want to reach the bottom-right cell, moving one cell at a time up, down, left or right, never leaving the grid. Normally obstacles cannot be entered, but you may remove up to `k` of them along the way; a removed obstacle becomes an empty cell you can step on.

Return the smallest number of moves that reaches the bottom-right cell using at most `k` removals, or `-1` if no such route exists. Both corner cells are always empty.

Reference: this is our own wording of LeetCode problem 1293, [Shortest Path in a Grid with Obstacles Elimination](https://leetcode.com/problems/shortest-path-in-a-grid-with-obstacles-elimination/).

## Input

- `grid`: the grid; `grid[r][c]` is `0` (empty) or `1` (obstacle).
- `k`: the most obstacles you may remove.

## Output

The fewest moves from `[0, 0]` to `[m - 1, n - 1]` that enter at most `k` obstacle cells, or `-1`. A one-cell grid needs `0` moves.

## Examples

### Example 1

<!-- case: ex1 -->

With one removal, take out the obstacle at `[0, 1]` and walk along the top row and down the right column: six moves, which is the least any route can take on a 4 by 4 grid.

### Example 2

<!-- case: ex2 -->

The same grid without removals: the empty cells reachable from the start form a dead end in the left part of the grid, so the goal cannot be reached.

## Constraints

- `1 <= m, n <= 40`
- `0 <= k <= m·n`
- `grid[r][c]` is `0` or `1`, and `grid[0][0] == grid[m - 1][n - 1] == 0`.

## Follow-ups

- Return the route itself, and which obstacles it removes.
- Show that `k >= m + n - 3` always allows the straight Manhattan route. Why does that bound let you cap `k`?
- Removals now cost one move each, on top of the step. Which algorithm handles the changed costs?

## Hints

### Hint 1

Your position alone is not enough to describe where you stand: being at a cell with three removals left is better than being there with none. What should a search state contain?

### Hint 2

Use states `(row, column, removals used)`. Moving into an obstacle increases the count; it is allowed only up to `k`. A breadth-first search over these states finds the fewest moves, since every move costs one.

### Hint 3

A state is useless if the same cell was already reached at the same or an earlier level with at least as many removals left. Keeping the best count of removals left per cell prunes most states.
