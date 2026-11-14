# Spiral Matrix

## Statement

You get a matrix of `m` rows and `n` columns. Read all of its values along a clockwise spiral and return them in that order.

The spiral starts at the top-left cell and moves right along the first row. Whenever the next cell would be outside the matrix or already read, it turns a quarter turn clockwise (right, then down, then left, then up, then right again) and continues, until every cell has been read exactly once.

Reference: this is our own wording of LeetCode problem 54, [Spiral Matrix](https://leetcode.com/problems/spiral-matrix/).

## Input

- `matrix`: the `m x n` matrix to read

## Output

An array of all `m * n` values in spiral order.

## Examples

### Example 1

<!-- case: ex1 -->

The spiral reads the top row 3, 1, 4, 1 from left to right, goes down the last column (5, 8), back along the bottom row from right to left (6, 2, 9) and up the first column (2). What is left is the middle of the second row, read from left to right: 6, 5.

### Example 2

<!-- case: ex2 -->

A single column is read from top to bottom: the spiral turns down right away, because there is nothing to its right.

## Constraints

- `1 <= m, n <= 300`
- `-1000 <= matrix[r][c] <= 1000`

## Follow-ups

- Can you do it without marking visited cells, with O(1) extra memory?
- How would you fill an `n x n` matrix with `1, 2, ..., n^2` in spiral order?
- What changes for a counterclockwise spiral, or one that starts from the centre?

## Hints

### Hint 1

Simulate the walk: keep a direction, and turn clockwise when the next cell is outside the matrix or already visited.

### Hint 2

The spiral is a sequence of rings. Track the first and last unread row and column; reading one ring moves all four bounds inward.

### Hint 3

When only one row or one column is left, reading it once is enough; check the bounds again before the bottom-row and left-column passes so it is not read twice.
