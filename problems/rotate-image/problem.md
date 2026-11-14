# Rotate Image

## Statement

A square image is stored as an `n x n` matrix of pixel values. Turn the image a quarter turn clockwise, in place: modify `matrix` itself so that, afterwards, it holds the rotated image.

After the rotation, the first row holds the old first column read from bottom to top, the last column holds the old first row, and in general the value at `matrix[r][c]` moves to `matrix[c][n - 1 - r]`.

Reference: this is our own wording of LeetCode problem 48, [Rotate Image](https://leetcode.com/problems/rotate-image/).

## Input

- `matrix`: the `n x n` image to rotate

## Output

Nothing is returned. The test checks the contents of `matrix` after the call.

## Examples

### Example 1

<!-- case: ex1 -->

The old first column holds 5, 2 and 6; read from bottom to top, it becomes the new first row `[6, 2, 5]`. The old first row `[5, 1, 8]` becomes the new last column, read from top to bottom. The centre value 0 stays where it is.

### Example 2

<!-- case: ex2 -->

In a 2 x 2 image, each value moves one corner clockwise: 9 goes from the top-left to the top-right, and the bottom-left -3 comes up to the top-left.

## Constraints

- `n == matrix.length == matrix[i].length`
- `1 <= n <= 500`
- `-1000 <= matrix[r][c] <= 1000`

## Follow-ups

- Rotating into a second matrix is easy. Can you do it with O(1) extra memory?
- Can you express the rotation as two simpler reflections?
- How would you rotate counterclockwise, or by 180 degrees?

## Hints

### Hint 1

Work out where the value at `(r, c)` lands, then where that cell's value lands, and so on. How many cells form one cycle?

### Hint 2

Four cells, one in each quadrant, rotate into each other. Swapping them in a cycle needs only one temporary value.

### Hint 3

Alternatively: a transpose (swap `matrix[r][c]` with `matrix[c][r]`) followed by reversing every row is exactly a clockwise quarter turn.
