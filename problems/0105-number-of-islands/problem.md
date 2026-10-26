# Number of Islands

## Statement

You get a rectangular map drawn as a grid of characters: `'1'` is a square of land and `'0'` is a square of water. Two land squares belong to the same island when you can walk from one to the other over land, one step at a time, moving up, down, left or right. A diagonal step is not allowed, so squares that only touch at a corner are not connected. Everything outside the map counts as water.

Return how many separate islands the map holds.

Reference: this is our own wording of LeetCode problem 200, [Number of Islands](https://leetcode.com/problems/number-of-islands/).

## Input

- `grid`: the map, with `m` rows and `n` columns; `grid[r][c]` is `'1'` for land or `'0'` for water.

## Output

The number of islands, or `0` when the map has no land at all.

## Examples

### Example 1

<!-- case: ex1 -->

The top-left corner holds an island of three squares and the top-right corner another one of three squares. The squares at rows 2 and 3 in the middle column, plus their neighbor to the right in row 3, form a third island. The single square at the bottom-left corner is a fourth island: its only land neighbor would be diagonal.

### Example 2

<!-- case: ex2 -->

The four land squares touch only at their corners, and corner contact does not connect squares, so each one is an island of its own.

## Constraints

- `1 <= m, n <= 300`
- `grid[r][c]` is `'0'` or `'1'`.

## Follow-ups

- Can you count the islands without changing `grid`? What does that cost in memory?
- A flood fill written with recursion can go 90,000 calls deep on a 300 by 300 map that is all land. How do you avoid that?
- Land is added one square at a time and you must report the island count after every addition. Which data structure answers each update quickly?

## Hints

### Hint 1

Scan the map square by square. An unvisited land square always starts an island you have not counted yet.

### Hint 2

When you find such a square, visit every land square of its island right away and mark them, so the scan never counts that island again.

### Hint 3

Another view: start with every land square as its own island, then merge each land square with its land neighbors to the right and below. Each successful merge removes one island from the count.
