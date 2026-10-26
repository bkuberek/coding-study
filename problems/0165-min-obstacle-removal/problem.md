# Minimum Obstacle Removal

## Statement

You get a grid of `0`s and `1`s with `m` rows and `n` columns: `0` is an empty cell and `1` is an obstacle that can be removed. You start in the top-left cell and want to reach the bottom-right cell, moving up, down, left or right, one cell at a time, without leaving the grid. You may only step on empty cells, but you may remove as many obstacles as you like before you set out.

Return the smallest number of obstacles you have to remove so that a route from the top-left to the bottom-right cell exists. The number of moves does not matter, only the number of removals. Both corner cells are always empty.

Reference: this is our own wording of LeetCode problem 2290, [Minimum Obstacle Removal to Reach Corner](https://leetcode.com/problems/minimum-obstacle-removal-to-reach-corner/).

## Input

- `grid`: the grid; `grid[r][c]` is `0` (empty) or `1` (obstacle).

## Output

The minimum number of obstacles to remove so that `[m - 1, n - 1]` can be reached from `[0, 0]`.

## Examples

### Example 1

<!-- case: ex1 -->

The obstacles in the middle row block every way down except through the right column, and the top row is blocked at `[0, 1]`. Removing that one obstacle opens the route along the top row and down the right column.

### Example 2

<!-- case: ex2 -->

The route `[0, 0]`, `[0, 1]`, `[1, 1]`, `[1, 2]` uses only empty cells, so nothing has to be removed.

## Constraints

- `1 <= m, n` and `2 <= m·n <= 10^5`
- `grid[r][c]` is `0` or `1`, and `grid[0][0] == grid[m - 1][n - 1] == 0`.

## Follow-ups

- Return the obstacles to remove, not only how many.
- Removing an obstacle now costs its own amount, between 1 and 9. What changes?
- How does this differ from limiting the removals to `k` and minimizing the number of moves?

## Hints

### Hint 1

Moving onto an empty cell costs nothing; moving onto an obstacle costs one removal. You want a cheapest path, where every step costs 0 or 1.

### Hint 2

Dijkstra's algorithm solves it directly, with the removals as the path cost.

### Hint 3

With costs of only 0 and 1, a double-ended queue replaces the heap: push zero-cost steps to the front and one-cost steps to the back, and the deque stays sorted by cost.
