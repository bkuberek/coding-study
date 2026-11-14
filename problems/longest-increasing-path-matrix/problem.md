# Longest Increasing Path in a Matrix

## Statement

You get a rectangular grid of integers, `matrix`. A path moves from a cell to one of its four neighbors (up, down, left or right; never diagonally and never off the grid), and it is increasing if every step goes to a strictly larger value. A single cell is an increasing path of length 1.

Return the number of cells on the longest increasing path in the grid. The path may start anywhere.

Reference: this is our own wording of LeetCode problem 329, [Longest Increasing Path in a Matrix](https://leetcode.com/problems/longest-increasing-path-in-a-matrix/).

## Input

- `matrix`: the grid, as a list of rows

## Output

The length, in cells, of the longest strictly increasing path.

## Examples

### Example 1

<!-- case: ex1 -->

The values spiral outwards from the 1 in the center: 1, 2, 3, 4, 5, 6, 7, 8, 9, each next to the previous one. The path visits all nine cells.

### Example 2

<!-- case: ex2 -->

All values are equal, so no step is strictly increasing and every path has a single cell.

## Constraints

- `1 <= m, n <= 200`, where `m` is the number of rows and `n` the number of columns
- `0 <= matrix[i][j] <= 2^31 - 1`
- The longest increasing path has at most 2000 cells, so a recursive search stays within the default stack depth of every language.

## Follow-ups

- A depth-first search from every cell revisits the same cells over and over. What can you remember about a cell once you have explored it?
- Why can an increasing path never visit a cell twice, and what does that say about the graph of allowed steps?
- Can you compute the answer without recursion?

## Hints

### Hint 1

The longest increasing path starting at a cell is 1 plus the longest one starting at a larger neighbor. That value does not depend on how you reached the cell.

### Hint 2

Steps always go to strictly larger values, so the "step" graph has no cycles: it is a directed acyclic graph, and a memoized depth-first search computes each cell once.

### Hint 3

Without recursion: repeatedly remove all cells that have no larger neighbor left (Kahn's algorithm from the sinks). The number of rounds is the answer.
