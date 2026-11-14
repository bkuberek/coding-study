# Max Area of Island

## Statement

A map is drawn as a grid of `0`s and `1`s, where `1` is land and `0` is water. Land squares that share a side (up, down, left or right) belong to the same island; squares that only meet at a corner do not. The area of an island is the number of land squares it contains.

Return the area of the largest island on the map, or `0` if there is no land.

Reference: this is our own wording of LeetCode problem 695, [Max Area of Island](https://leetcode.com/problems/max-area-of-island/).

## Input

- `grid`: the map, with `m` rows and `n` columns; `grid[r][c]` is `1` for land and `0` for water.

## Output

The largest number of land squares in a single island; `0` when the map is all water.

## Examples

### Example 1

<!-- case: ex1 -->

There are three islands. The one in the top-left corner has 3 squares and the lone square in the bottom row has 1. The island on the right covers a 2 by 2 block plus the square below its lower-right corner, 5 squares, which is the largest.

### Example 2

<!-- case: ex2 -->

There is no land, so the largest area is 0.

## Constraints

- `1 <= m, n <= 300`
- `grid[r][c]` is `0` or `1`.

## Follow-ups

- Return the size of every island, sorted, instead of only the largest.
- If you may turn at most one water square into land, what is the largest island you can make?
- Your flood fill must not recurse once per square on a 300 by 300 map of land. How do you avoid it?

## Hints

### Hint 1

Counting islands needs one flood fill per island. Measuring them needs the same flood fill, plus a counter.

### Hint 2

Count a square when you first mark it as visited, so each square adds exactly 1 to its island's area.

### Hint 3

With a disjoint-set structure, keep the size of each group at its root; merging two groups adds their sizes.
