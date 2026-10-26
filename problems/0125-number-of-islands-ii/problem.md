# Number of Islands II

## Statement

A map is a grid of `m` rows and `n` columns that starts as all water. The operations in `positions` raise land one cell at a time: `[r, c]` turns the cell in row `r` and column `c` into land. An island is a maximal group of land cells connected through their top, bottom, left and right neighbors; diagonal neighbors do not connect.

After each operation, report how many islands the map has. Raising a cell that is already land changes nothing, but it still gets its count in the answer.

Reference: this is our own wording of LeetCode problem 305, [Number of Islands II](https://leetcode.com/problems/number-of-islands-ii/).

## Input

- `m`: the number of rows
- `n`: the number of columns
- `positions`: the cells `[r, c]` raised to land, in order

## Output

An array whose `i`-th entry is the number of islands right after the `i`-th operation.

## Examples

### Example 1

<!-- case: ex1 -->

The first two cells form one island. `[1, 2]` and `[2, 1]` touch neither it nor each other (diagonal contact does not count), so the count rises to 3. The center cell `[1, 1]` touches all three islands and merges them into one.

### Example 2

<!-- case: ex2 -->

Two diagonal cells are two islands. Raising `[0, 0]` again changes nothing. `[0, 1]` touches both and joins them.

## Constraints

- `1 <= m, n <= 10^4` and `m * n <= 10^4`
- `1 <= positions.length <= 10^4`
- `0 <= r < m` and `0 <= c < n`
- The same cell may appear more than once.

## Follow-ups

- Recounting every island after each operation is simple. How much work does it repeat?
- A new land cell creates one island and then merges with each distinct neighboring island. How can you tell whether two neighbors belong to the same island?
- Why can naive union-find still be slow here, and how do union by size and path compression fix it?

## Hints

### Hint 1

Count incrementally: a new land cell adds one island, and every merge with a different neighboring island removes one.

### Hint 2

Keep one union-find element per cell. When a cell becomes land, look at its four neighbors; for each land neighbor whose root differs from the new cell's root, merge them and decrement the count.

### Hint 3

Skip cells that are already land: processing them again would add a phantom island.
