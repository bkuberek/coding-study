# Maximal Rectangle

## Statement

You get a rectangular grid `matrix` whose cells hold the character `'1'` or `'0'`. Find the largest rectangle made only of `'1'` cells, with sides parallel to the grid, and return its area (the number of cells it covers). If the grid has no `'1'`, the answer is 0.

Reference: this is our own wording of LeetCode problem 85, [Maximal Rectangle](https://leetcode.com/problems/maximal-rectangle/).

## Input

- `matrix`: the grid, as a list of rows; each cell is `'0'` or `'1'`

## Output

The area of the largest rectangle that contains only `'1'` cells.

## Examples

### Example 1

<!-- case: ex1 -->

Rows 1 to 3, columns 1 to 3 are all ones, a 3 by 3 rectangle of area 9. The full rows 1 and 3 have area 5 each, and the block of columns 2 and 3 over all four rows has area 8.

### Example 2

<!-- case: ex2 -->

The two ones touch only at a corner, so the largest rectangle is a single cell.

## Constraints

- `1 <= m, n <= 200`, where `m` is the number of rows and `n` the number of columns
- Every cell is `'0'` or `'1'`.

## Follow-ups

- Fixing the bottom-right corner and walking up costs O(m) per cell. Can you turn every row into a problem you already know?
- Can you solve it in O(m * n) time with O(n) extra memory?
- How would you count all the all-ones rectangles?

## Hints

### Hint 1

For a fixed bottom row, count for every column how many consecutive ones stand directly above it (including itself). The rectangles resting on that row are exactly the rectangles inside that histogram.

### Hint 2

The heights of one row follow from the previous row: add 1 on a `'1'`, reset to 0 on a `'0'`. Then solve "largest rectangle in a histogram" for each row with a monotonic stack.

### Hint 3

Alternatively, keep for every column the height and the furthest left and right boundaries that the whole column of ones can stretch to; the area for that column is `height * (right - left)`.
