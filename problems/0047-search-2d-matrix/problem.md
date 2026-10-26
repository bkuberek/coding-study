# Search a Sorted Matrix

## Statement

You are given a rectangular grid of integers `matrix` with `m` rows and `n` columns. The grid is ordered like the lines of a book: inside every row the values never decrease from left to right, and the first value of each row is strictly greater than the last value of the row above it. Reading the cells row by row therefore produces one non-decreasing sequence.

Decide whether `target` occurs anywhere in the grid. A solution should take a number of steps proportional to the logarithm of the number of cells.

Reference: this is our own wording of LeetCode problem 74, [Search a 2D Matrix](https://leetcode.com/problems/search-a-2d-matrix/).

## Input

- `matrix`: the grid, as a list of rows of equal length
- `target`: the value to look for

## Output

`true` if at least one cell holds `target`, `false` otherwise.

## Examples

### Example 1

<!-- case: ex1 -->

The middle row runs from 10 to 15, and 13 is its second value, so the answer is `true`.

### Example 2

<!-- case: ex2 -->

Every value of the first row is below 12 and the second row jumps from 11 to 14, so 12 is nowhere in the grid. Repeated values inside a row, like the two 11s, are allowed.

## Constraints

- `1 <= m, n`
- `m * n <= 10^5`
- `-10^9 <= matrix[i][j] <= 10^9`
- `-10^9 <= target <= 10^9`
- `matrix[i][j] <= matrix[i][j + 1]` within every row.
- `matrix[i][n - 1] < matrix[i + 1][0]` for every pair of consecutive rows.

## Follow-ups

- Can you treat the whole grid as a single sorted array without copying it?
- Suppose only each row and each column were sorted, without the row-to-row guarantee. Which of your approaches still works, and how fast is it?

## Hints

### Hint 1

Because of the row-to-row rule, the cells in row-major order form one sorted list of length `m * n`.

### Hint 2

Binary search over positions `0` to `m * n - 1`. How do you turn a position into a row and a column?

### Hint 3

Position `p` is row `p / n` and column `p % n`, using integer division.
