# Minimum Cost to Connect Points

## Statement

You get `n` distinct points on a grid, `points[i] = [x, y]`. Laying a cable between two points `[x1, y1]` and `[x2, y2]` costs their Manhattan distance, `|x1 - x2| + |y1 - y2|`. Cables only run directly between two of the given points.

Choose cables so that every point is connected to every other one, directly or through other points, and return the smallest possible total cost.

Reference: this is our own wording of LeetCode problem 1584, [Min Cost to Connect All Points](https://leetcode.com/problems/min-cost-to-connect-all-points/).

## Input

- `points`: the coordinates of the points, all different.

## Output

The minimum total cable cost that connects all points; `0` for a single point.

## Examples

### Example 1

<!-- case: ex1 -->

Four cables are needed for five points. The cheapest choice links `[0, 0]` to `[3, 1]` (cost 4), `[3, 1]` to `[6, 0]` (cost 4), `[0, 0]` to `[1, 4]` (cost 5), and `[1, 4]` to `[5, 5]` (cost 5), for a total of 18. Any other set of cables that connects all five points costs at least as much.

### Example 2

<!-- case: ex2 -->

Two points need one cable, costing `|-2 - 4| + |3 - (-1)| = 10`.

## Constraints

- `1 <= n <= 1000`
- `-10^6 <= x, y <= 10^6`
- All points are distinct.

## Follow-ups

- Sorting all `n·(n - 1)/2` pairs is the main cost of Kruskal's algorithm here. Can you avoid building the list of pairs at all?
- Which cable could you remove to split the points into two groups as cheaply as possible?
- With Euclidean distances and very many points, how could you avoid considering every pair?

## Hints

### Hint 1

Points are nodes, and every pair is an edge whose weight is the Manhattan distance. You need a minimum spanning tree of this complete graph.

### Hint 2

Kruskal's algorithm: sort all pairs by cost and add each cable that joins two groups not yet connected, using a disjoint-set structure to tell.

### Hint 3

Prim's algorithm grows one tree. Keep for every point outside the tree the cheapest cable to any point inside it; each round, add the outside point with the cheapest cable and update the others. With an array, a round costs O(n).
