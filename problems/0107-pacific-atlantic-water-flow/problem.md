# Pacific Atlantic Water Flow

## Statement

An island is mapped as a grid of land heights. The Pacific Ocean runs along the whole top edge and the whole left edge of the map; the Atlantic Ocean runs along the whole bottom edge and the whole right edge.

Rain that lands on a cell can run into any of its four side neighbors (up, down, left, right) whose height is at most the height of the cell it is on, and from there it keeps running by the same rule. Water on a cell of the top row or the left column can drain into the Pacific; water on a cell of the bottom row or the right column can drain into the Atlantic. A corner cell may touch both.

Find every cell from which rain can reach both oceans, possibly by different routes.

Reference: this is our own wording of LeetCode problem 417, [Pacific Atlantic Water Flow](https://leetcode.com/problems/pacific-atlantic-water-flow/).

## Input

- `heights`: the map, with `m` rows and `n` columns; `heights[r][c]` is the height of the cell in row `r` and column `c`.

## Output

The list of all cells `[r, c]` from which water can reach both the Pacific and the Atlantic, each cell once, in any order.

## Examples

### Example 1

<!-- case: ex1 -->

The cell `[0, 0]` touches the Pacific and its water runs down through `[1, 0]` to the bottom row, so it reaches the Atlantic too. The two cells of height 1 in the middle form a basin: every neighbor is higher, so their water reaches neither ocean. The cell `[0, 2]` touches the Pacific, but every route from it toward the Atlantic ends in that basin or climbs.

### Example 2

<!-- case: ex2 -->

The cells `[0, 1]` and `[1, 0]` each touch both oceans. The low corner `[0, 0]` touches only the Pacific and both of its neighbors are higher, so its water stays on the Pacific side; `[1, 1]` is the same for the Atlantic.

## Constraints

- `1 <= m, n <= 200`
- `0 <= heights[r][c] <= 10^5`

## Follow-ups

- Searching from every cell separately repeats the same work many times. Can you solve it with two searches in total?
- How would you answer the question for a map with three or four oceans, one per edge?
- Which cells can reach at least one ocean? Which can reach neither?

## Hints

### Hint 1

Water flowing from a cell downhill to the ocean is the same route as climbing from the ocean uphill to that cell, read backwards.

### Hint 2

Start one search from all the Pacific cells at once and move only to neighbors that are at least as high. Every cell it reaches can drain into the Pacific.

### Hint 3

Do the same from the Atlantic cells. The answer is the set of cells reached by both searches.
