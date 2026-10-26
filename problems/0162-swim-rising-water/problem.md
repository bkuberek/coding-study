# Swim in Rising Water

## Statement

A square pool of `n` by `n` cells has an uneven floor: `grid[r][c]` is the height of the floor in cell `[r, c]`. The heights are the numbers `0` to `n^2 - 1`, each used exactly once. Rain makes the water level rise: at time `t` the water stands at height `t` everywhere.

You start in the top-left cell and want to reach the bottom-right cell. At time `t` you may swim from a cell to a side neighbor (up, down, left or right) when both floors are at height at most `t`. Swimming itself takes no time, so you can cover any distance at once as long as the water is deep enough everywhere on your route. Return the earliest time at which you can reach the bottom-right cell.

Reference: this is our own wording of LeetCode problem 778, [Swim in Rising Water](https://leetcode.com/problems/swim-in-rising-water/).

## Input

- `grid`: the floor heights, an `n` by `n` grid containing every number from `0` to `n^2 - 1` once.

## Output

The smallest `t` such that some route of side-adjacent cells from `[0, 0]` to `[n - 1, n - 1]` has every floor height at most `t`.

## Examples

### Example 1

<!-- case: ex1 -->

The route down and then right passes floors 0, 2 and 1, so it opens at time 2. The other route crosses the floor of height 3 and opens only at time 3.

### Example 2

<!-- case: ex2 -->

Along the top row and down the right column the highest floor is 5. The route down the left column climbs to 7, and every route through the middle crosses the floor of height 8, so the answer is 5, even though the goal cell itself is only at height 2.

## Constraints

- `1 <= n <= 50`
- `grid` holds every number from `0` to `n^2 - 1` exactly once.

## Follow-ups

- Return a route that is usable at the earliest time.
- What changes if the heights may repeat and go up to `10^9`?
- Can you solve it by adding cells in increasing order of height to a disjoint-set structure?

## Hints

### Hint 1

For a fixed time `t`, deciding whether the goal is reachable is a plain flood fill over cells with height at most `t`. Reachability only gets easier as `t` grows.

### Hint 2

Because of that monotonicity, binary search over `t` between the start's height and `n^2 - 1`.

### Hint 3

Or think of the cost of a route as the highest floor on it, and run Dijkstra with that cost: always extend from the reachable cell with the lowest "highest floor so far" using a min-heap.
