# Unique Paths

## Statement

A robot stands on the top-left cell of a grid with `m` rows and `n` columns. In one move it steps either one cell to the right or one cell down; it never moves left, up or off the grid. It wants to reach the bottom-right cell.

Count the distinct routes the robot can take. Two routes are different if they differ in at least one move. The count grows very quickly, so return it modulo `10^9 + 7`.

Reference: this is our own wording of LeetCode problem 62, [Unique Paths](https://leetcode.com/problems/unique-paths/). The original guarantees a small answer instead of asking for a remainder.

## Input

- `m`: the number of rows
- `n`: the number of columns

## Output

The number of routes from the top-left cell to the bottom-right cell, modulo `10^9 + 7`.

## Examples

### Example 1

<!-- case: ex1 -->

Every route makes 2 moves down and 3 moves right, in some order. Choosing which 2 of the 5 moves go down gives 10 routes.

### Example 2

<!-- case: ex2 -->

With a single row the robot can only move right, so there is exactly one route.

## Constraints

- `1 <= m, n <= 1000`

## Follow-ups

- Recursion that tries both moves from every cell repeats the same sub-grids exponentially often. Which result can you reuse?
- The table of counts only ever reads the row above. Can you keep a single row?
- Every route is a sequence of `m - 1` downs and `n - 1` rights. Can you count them without any table?

## Hints

### Hint 1

The routes from a cell split by their first move: right or down. So the count for a cell is the count for the cell to its right plus the count for the cell below it.

### Hint 2

Cells in the last row or the last column have exactly one route to the goal. Fill in the other cells from the bottom-right corner backwards, or the mirror image from the top-left.

### Hint 3

The answer is the binomial coefficient `C(m + n - 2, m - 1)`. Modulo a prime, divide by multiplying with a modular inverse (Fermat's little theorem).
