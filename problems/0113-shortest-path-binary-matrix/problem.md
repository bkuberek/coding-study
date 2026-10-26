# Shortest Path in a Binary Grid

## Statement

You get a square grid of `0`s and `1`s with `n` rows and `n` columns. A `0` is an open cell and a `1` is blocked. You start in the top-left cell and want to reach the bottom-right cell. From any open cell you may step to any of its eight neighbors (sideways, up, down or diagonally) as long as that neighbor is open; a diagonal step is allowed even when both cells beside it are blocked.

The length of a path is the number of cells it visits, counting the first and the last. Return the length of the shortest path, or `-1` if no path exists. When the start or the end cell is blocked there is no path.

Reference: this is our own wording of LeetCode problem 1091, [Shortest Path in Binary Matrix](https://leetcode.com/problems/shortest-path-in-binary-matrix/).

## Input

- `grid`: an `n` by `n` grid; `grid[r][c]` is `0` (open) or `1` (blocked).

## Output

The number of cells on a shortest path from `[0, 0]` to `[n - 1, n - 1]`, or `-1` when there is none. A grid of one open cell has a path of length 1.

## Examples

### Example 1

<!-- case: ex1 -->

The straight diagonal is blocked at `[1, 1]`. One shortest route goes down to `[1, 0]`, diagonally to `[2, 1]` and `[3, 2]`, then right to `[3, 3]`: five cells. No route of four cells exists, because only the blocked diagonal covers the distance in three steps.

### Example 2

<!-- case: ex2 -->

The start cell itself is blocked, so no path exists.

## Constraints

- `1 <= n <= 100`
- `grid[r][c]` is `0` or `1`.

## Follow-ups

- Return the path itself, not only its length.
- What if each diagonal step costs more than a straight one? Which algorithm would you switch to?
- Can a search that is guided toward the goal (A* with a suitable estimate) visit fewer cells here?

## Hints

### Hint 1

Every step costs the same, one cell. Which search finds shortest paths in a graph whose edges all have the same weight?

### Hint 2

Run a breadth-first search from the top-left cell over the eight directions. The level at which a cell is first reached is its distance.

### Hint 3

Mark a cell as visited when you add it to the queue, check both corners before starting, and remember that the answer counts cells, so the start alone has length 1.
