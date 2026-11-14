# Range Sum Query 2D

## Statement

A grid of integers is fixed once and then asked, many times, for the total of the values inside an axis-aligned rectangle. Build a class that answers every such question in constant time.

Implement the class `NumMatrix`:

- `NumMatrix(matrix)` stores the grid. It never changes afterwards.
- `sumRegion(row1, col1, row2, col2)` returns the sum of every `matrix[r][c]` with `row1 <= r <= row2` and `col1 <= c <= col2`: the rectangle whose top-left corner is `(row1, col1)` and whose bottom-right corner is `(row2, col2)`, both corners included.

Reference: this is our own wording of LeetCode problem 304, [Range Sum Query 2D - Immutable](https://leetcode.com/problems/range-sum-query-2d-immutable/).

## Input

- Constructor: `matrix`, a grid of `m` rows and `n` columns.
- `sumRegion(row1, col1, row2, col2)`: the top-left and bottom-right corners of the rectangle, with `0 <= row1 <= row2 < m` and `0 <= col1 <= col2 < n`.

Each test is a sequence of calls: the constructor first, then `sumRegion` calls in order.

## Output

- `sumRegion` returns the sum of the rectangle.

The expected output lists one result per call, with `null` for the constructor.

## Examples

### Example 1

<!-- case: ex1 -->

The grid is

```text
 2  0 -1  4
 1  3  5 -2
-3  1  0  2
```

The rectangle from `(0, 1)` to `(1, 2)` holds 0, -1, 3 and 5, which add up to 7. The rectangle from `(1, 0)` to `(2, 3)` covers the bottom two rows, which add up to 7 as well. A single cell, `(2, 0)`, returns its own value, -3.

### Example 2

<!-- case: ex2 -->

A grid of one row behaves like a one-dimensional array: the rectangle from `(0, 1)` to `(0, 3)` adds 4, 6 and 8 into 18, and the whole row adds up to 30.

## Constraints

- `1 <= m, n <= 200`
- `-10^4 <= matrix[r][c] <= 10^4`
- `0 <= row1 <= row2 < m` and `0 <= col1 <= col2 < n`
- At most `10^5` calls to `sumRegion`.
- Every rectangle sum is at most `200 * 200 * 10^4 = 4 * 10^8` in absolute value, so it fits in a 32-bit `int`.

## Follow-ups

- Visiting every cell of the rectangle costs O(m * n) per query. Can each query cost O(1) after an O(m * n) preparation?
- How would you support updates to single cells? (A two-dimensional Fenwick tree answers both in O(log m * log n).)
- How does the idea extend to a three-dimensional grid?

## Hints

### Hint 1

Start from the one-dimensional version: a range sum is the difference of two prefix sums. What is the two-dimensional analogue of a prefix?

### Hint 2

Let `P[r][c]` be the sum of the sub-grid with corners `(0, 0)` and `(r - 1, c - 1)`. It can be filled row by row from its left, upper and upper-left neighbors.

### Hint 3

The rectangle is `P[row2 + 1][col2 + 1]` minus the strip above it and the strip to its left. The top-left block is subtracted twice, so add it back once (inclusion-exclusion).
