# Valid Sudoku

## Statement

A Sudoku board is a 9 x 9 grid split into nine 3 x 3 boxes. Some cells hold a digit from `1` to `9`; the others are empty, written `.`. A board follows the rules when no digit appears twice in the same row, twice in the same column, or twice in the same 3 x 3 box.

You get a partially filled board. Decide whether its filled cells follow the rules. Only the digits already on the board matter: you do not need to check whether the empty cells can be completed, so a board can follow the rules even if it has no solution.

Reference: this is our own wording of LeetCode problem 36, [Valid Sudoku](https://leetcode.com/problems/valid-sudoku/).

## Input

- `board`: 9 rows of 9 cells each; every cell is a digit character from `1` to `9` or the character `.` for an empty cell

## Output

`true` if no row, no column and no 3 x 3 box contains the same digit twice, otherwise `false`.

## Examples

### Example 1

<!-- case: ex1 -->

Every row, every column and every box holds each of its digits at most once. For instance the top-left box contains 3, 7 and 1, and the first column contains 3, 2 and 7.

### Example 2

<!-- case: ex2 -->

This is Example 1 with one more digit: a 3 at row 1, column 2 (counting from 0). Row 1 and column 2 contain no other 3, but the top-left box already has a 3 at row 0, column 0, so the box rule is broken.

## Constraints

- `board.length == 9`
- `board[i].length == 9`
- `board[i][j]` is a digit `1` to `9` or `.`.

## Follow-ups

- Can you check all three rules in a single pass over the board?
- How little memory do you need? Can 27 integers replace 27 sets?
- How would the solution change for a 16 x 16 board with 4 x 4 boxes?

## Hints

### Hint 1

Each rule is a duplicate check: does a row, a column or a box contain a repeated digit?

### Hint 2

The cell in row `r` and column `c` belongs to box `(r / 3) * 3 + c / 3`, using integer division.

### Hint 3

Keep one collection of seen digits for every row, every column and every box. Visit each filled cell once and check its three collections before adding the digit to them.
