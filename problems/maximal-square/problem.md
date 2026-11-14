# Maximal Square

## Statement

You get a rectangular grid `matrix` whose cells hold the character `'1'` or `'0'`. Find the largest square made only of `'1'` cells, with sides parallel to the grid, and return its area (the number of cells it covers). If the grid has no `'1'`, the answer is 0.

Reference: this is our own wording of LeetCode problem 221, [Maximal Square](https://leetcode.com/problems/maximal-square/).

## Input

- `matrix`: the grid, as a list of rows; each cell is `'0'` or `'1'`

## Output

The area of the largest square that contains only `'1'` cells.

## Examples

### Example 1

<!-- case: ex1 -->

Rows 0 to 2, columns 1 to 3 are all ones, a 3 by 3 square of area 9. No 4 by 4 square fits, because row 0 has only three ones in a row.

### Example 2

<!-- case: ex2 -->

The whole grid is ones, but it is a 2 by 4 rectangle, not a square. The largest square inside it is 2 by 2, area 4.

## Constraints

- `1 <= m, n <= 300`, where `m` is the number of rows and `n` the number of columns
- Every cell is `'0'` or `'1'`.

## Follow-ups

- Checking every possible square is far too slow. If you know the largest squares ending at the three neighbors of a cell, what do you know about the cell itself?
- Can you keep only one row of the table?
- How would you count all the all-ones squares instead of finding the largest?

## Hints

### Hint 1

Let `S(r, c)` be the side of the largest all-ones square whose bottom-right corner is `(r, c)`. It is 0 for a `'0'` cell.

### Hint 2

For a `'1'` cell, `S(r, c) = 1 + min(S(r - 1, c), S(r, c - 1), S(r - 1, c - 1))`: the square can only grow as far as all three neighbors allow.

### Hint 3

The answer is the largest `S` squared. Each row of the table only reads the row above, so one row plus the previous diagonal value is enough.
