# Set Matrix Zeroes

## Statement

You get a matrix of `m` rows and `n` columns. Every cell that holds 0 spreads: its whole row and its whole column must become 0. Apply this to the matrix in place.

Only the zeros of the original matrix spread. A cell that becomes 0 because of another zero does not wipe out its own row and column in turn.

Reference: this is our own wording of LeetCode problem 73, [Set Matrix Zeroes](https://leetcode.com/problems/set-matrix-zeroes/).

## Input

- `matrix`: the `m x n` matrix to update

## Output

Nothing is returned. The test checks the contents of `matrix` after the call: every row and every column that contained a 0 is all zeros, and every other cell keeps its value.

## Examples

### Example 1

<!-- case: ex1 -->

The only 0 sits in row 1, column 2, so row 1 and column 2 become all zeros. The other cells keep their values.

### Example 2

<!-- case: ex2 -->

The zeros at the top-left and bottom-right corners clear rows 0 and 2 and columns 0 and 2. Only the centre value 4 survives.

## Constraints

- `1 <= m, n <= 300`
- `-2^31 <= matrix[r][c] <= 2^31 - 1`

## Follow-ups

- Copying the matrix uses O(m * n) extra memory. Can you do it with O(m + n)?
- Can you do it with O(1) extra memory?
- Why does zeroing rows and columns while you are still scanning give a wrong answer?

## Hints

### Hint 1

First find out which rows and which columns must be cleared; only then clear them. Mixing the two phases lets new zeros spread.

### Hint 2

One flag per row and one per column is enough information.

### Hint 3

The first row and the first column can hold those flags themselves. Only cell `(0, 0)` is claimed twice, so remember separately whether the first column contained a zero, and clear the matrix from the bottom row up so the markers in row 0 are read before row 0 is cleared.
