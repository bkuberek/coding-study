# N-Queens

## Statement

A chess queen attacks every square in its row, in its column and along both of its diagonals. You get a positive integer `n`. Place `n` queens on an `n` by `n` board so that no two of them attack each other, and list every way of doing so.

Describe a board as `n` strings, one per row from top to bottom, where `Q` marks a queen and `.` marks an empty square. Mirror images and rotations of a placement count as different placements.

Reference: this is our own wording of LeetCode problem 51, [N-Queens](https://leetcode.com/problems/n-queens/).

## Input

- `n`: the size of the board and the number of queens

## Output

A list of every valid board, each exactly once, as a list of `n` row strings. The boards may be listed in any order; the rows inside a board are always top to bottom.

## Examples

### Example 1

<!-- case: ex1 -->

On a 4 by 4 board there are exactly two placements, mirror images of each other. In the first, the queens sit in columns 1, 3, 0 and 2 of the rows from top to bottom; no two share a column or a diagonal.

### Example 2

<!-- case: ex2 -->

A single queen on a single square attacks nothing.

## Constraints

- `1 <= n <= 10`

## Follow-ups

- Two queens share a diagonal when the difference of their row and column is equal, or when the sum is. How can that turn each conflict test into one lookup?
- Can you track the free columns of the next row as the bits of one integer?
- If you only needed the number of placements, which parts of the work could you drop?

## Hints

### Hint 1

Every row holds exactly one queen, so place them row by row: the question for each row is only which column to use.

### Hint 2

Before placing a queen at `(row, col)`, check it against the queens already placed. Undo the placement after exploring it, then try the next column.

### Hint 3

Keep three sets of attacked lines: used columns, used `row - col` diagonals and used `row + col` anti-diagonals. A square is free exactly when its three lines are all unused.
