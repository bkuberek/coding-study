# City With Fewest Reachable Neighbors

## Statement

There are `n` cities, numbered `0` to `n - 1`, joined by two-way roads: `edges[i] = [a, b, w]` is a road between cities `a` and `b` of length `w`. The distance between two cities is the length of the shortest route between them over any number of roads.

For each city, count the other cities whose distance from it is at most `distanceThreshold`. Return the city with the smallest count. If several cities share the smallest count, return the one with the largest number.

Reference: this is our own wording of LeetCode problem 1334, [Find the City With the Smallest Number of Neighbors at a Threshold Distance](https://leetcode.com/problems/find-the-city-with-the-smallest-number-of-neighbors-at-a-threshold-distance/).

## Input

- `n`: the number of cities.
- `edges`: the roads, each `[a, b, w]`, usable in both directions.
- `distanceThreshold`: the largest distance that still counts as reachable.

## Output

The number of the city with the fewest other cities within `distanceThreshold`; on a tie, the largest such city number.

## Examples

### Example 1

<!-- case: ex1 -->

From city 0 only city 1 is within distance 4 (city 2 is 5 away and city 3 is 6 away). City 1 reaches all three others (distances 2, 3 and 4); cities 2 and 3 reach two each. City 0 has the smallest count.

### Example 2

<!-- case: ex2 -->

The only road is longer than the threshold, so no city reaches any other: all three counts are 0, and the tie goes to the largest number, city 2.

## Constraints

- `2 <= n <= 100`
- `1 <= edges.length <= n·(n - 1)/2`
- `0 <= a < b < n`, and no pair of cities has two roads.
- `1 <= w, distanceThreshold <= 10^4`

## Follow-ups

- Return the counts for all cities, not only the best one.
- Which algorithm would you choose for 10^5 cities and 3·10^5 roads, and why?
- What changes if roads are one-way?

## Hints

### Hint 1

You need shortest distances between all pairs of cities, then one count per city.

### Hint 2

Floyd-Warshall computes all pairs in O(n^3): for every middle city `m`, check whether going through `m` shortens the route between every pair `i`, `j`.

### Hint 3

Alternatively, run Dijkstra from every city; you can stop each run as soon as the next distance exceeds the threshold. Scan cities in increasing order and use `<=` when comparing counts, so a later city wins ties.
