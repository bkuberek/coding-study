# Surrounded Regions

## Statement

A board is a grid of the characters `'X'` and `'O'`. Cells holding `'O'` that share a side (up, down, left or right) belong to the same region. A region is captured when none of its cells lies on the edge of the board: it is then completely walled in by `'X'` cells. Capture every such region by changing all of its cells to `'X'`. Regions that touch the edge in at least one cell keep all their `'O'`s.

Change `board` in place; the function returns nothing.

Reference: this is our own wording of LeetCode problem 130, [Surrounded Regions](https://leetcode.com/problems/surrounded-regions/).

## Input

- `board`: the board, with `m` rows and `n` columns; every cell is `'X'` or `'O'`.

## Output

Nothing is returned. The tests read `board` after the call: it must show every captured region turned into `'X'` and every other cell unchanged.

## Examples

### Example 1

<!-- case: ex1 -->

The three `'O'` cells near the top-left corner form a region with no cell on the edge, so they are captured, and so is the lone `'O'` in row 3. The two `'O'` cells in the right column touch the edge and stay.

### Example 2

<!-- case: ex2 -->

The center `'O'` touches the corner cells only diagonally, so it is a region of its own, fully enclosed, and captured. The corner cells lie on the edge and stay.

## Constraints

- `1 <= m, n <= 200`
- `board[r][c]` is `'X'` or `'O'`.

## Follow-ups

- Instead of searching from every enclosed region, can you decide everything with one search that starts at the edge?
- How would you report the number of captured regions and their sizes?
- What changes if regions may also connect diagonally?

## Hints

### Hint 1

Deciding whether a region touches the edge means exploring the whole region. Which cells are easy to classify right away?

### Hint 2

Every `'O'` on the edge is safe, and so is every `'O'` connected to it. A flood fill from the edge finds all safe cells at once.

### Hint 3

Mark the safe cells with a temporary character, turn every remaining `'O'` into `'X'`, then restore the temporary marks to `'O'`.
