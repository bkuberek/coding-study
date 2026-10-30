# City With Fewest Reachable Neighbors: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| floyd-warshall | intermediate | O(n^3) | O(n^2) | small or dense graphs; shortest code |
| dijkstra-from-each | optimal | O(n·(n + E)·log n) | O(n + E) | sparse graphs, and whenever the threshold cuts searches short |

Each city needs the number of other cities within the threshold, which is a question about shortest distances from every city. Floyd-Warshall computes all pairs at once; running Dijkstra from each city computes one row at a time and can stop each run at the threshold. With n at most 100 both are fast; their growth differs on larger or sparser graphs.

## Approach: floyd-warshall (All-pairs distances with Floyd-Warshall)

### Intuition

Start with the direct road lengths. Then allow city 0 as a stopover: for every pair, a route through city 0 may be shorter. Then allow city 1 as well, and so on. After every city has been allowed as a stopover, the table holds the true shortest distances. Counting the entries within the threshold in each row gives every city's count.

### Algorithm

1. Fill `dist` with infinity, 0 on the diagonal, and the road lengths in both directions.
2. For each `middle` from 0 to `n - 1`, for every pair `i`, `j`: `dist[i][j] = min(dist[i][j], dist[i][middle] + dist[middle][j])`.
3. For each city in increasing order, count the other cities with `dist <= distanceThreshold`; keep the city whenever its count is at most the best so far.
4. Return the kept city.

### Correctness

Invariant: after processing `middle = m`, `dist[i][j]` is the length of a shortest route from `i` to `j` whose stopovers are all among cities `0..m`. A shortest such route either avoids `m` (already counted) or passes through it exactly once, splitting into two routes whose stopovers are among `0..m - 1`, which are exact by the invariant. After the last step every stopover is allowed, so the table is exact. Scanning cities in increasing order and replacing on `<=` returns the largest city among those with the smallest count.

### Complexity

- Time: O(n^3) — three nested loops over the cities; counting adds O(n^2).
- Space: O(n^2) — the distance table.

### Trade-offs

Very short and independent of the number of roads, which makes it the natural pick for at most 100 cities or dense graphs. It always does n^3 work, even when the threshold is tiny or roads are few; Dijkstra from each city does better on sparse graphs.

### Pitfalls and edge cases

- The order of the loops matters: `middle` must be the outer loop.
- Initialize the diagonal to 0, and count only other cities, not the city itself.
- With fixed-size integers, use a large "far" value whose double still fits, so `dist[i][m] + dist[m][j]` cannot overflow.
- Ties go to the largest city number: compare with `<=` while scanning upward.

### Language notes

- Python: `math.inf` marks missing roads; skipping rows where `dist[i][middle]` is infinite saves work on sparse graphs.
- TypeScript: rows are plain arrays filled with `Infinity`, which adds safely.
- Java: `Integer.MAX_VALUE / 2` serves as infinity so that adding two of them stays positive.
- Kotlin: the same constant; the final choice is `(0 until n).last { counts[it] == fewest }`, which states the tie rule directly.
- Go: `inf = math.MaxInt / 2` (a 64-bit `int`) makes the sum of two "no road" entries safe from overflow, and `dist[i][j]` is indexed directly, so the `[][]int` needs no copy. The `for` loops with explicit indexes mirror the textbook triple loop.
- Rust: `i32::MAX / 2` plays the same role, and it is required, not a nicety: overflow checks are on, so `i32::MAX + i32::MAX` would panic. Cloning the `middle` row before the loop lets `dist.iter_mut()` borrow every row mutably without aliasing the row being read.

## Approach: dijkstra-from-each (Dijkstra with a heap from every city)

### Intuition

All road lengths are positive, so Dijkstra's algorithm from a city settles the other cities in order of distance. For this problem only cities within the threshold matter: never push a tentative distance above the threshold, and every settled city is one of the cities to count. Repeat from every city.

### Algorithm

1. Build adjacency lists with every road in both directions.
2. For each city `s`: run Dijkstra from `s` with a min-heap of `(distance, city)`, pushing a neighbor only if its tentative distance is at most the threshold; count the settled cities other than `s`.
3. Scanning cities in increasing order, keep the city whenever its count is at most the best so far, and return it.

### Correctness

Dijkstra settles cities in non-decreasing order of their true distance from `s`. A city within the threshold has a shortest route whose every prefix is also within the threshold (lengths are positive), so all tentative distances along it are pushed, and the city is settled. A city beyond the threshold has no route of length within it, so it is never pushed. The count is therefore exact, and the scan applies the tie rule as before.

### Complexity

- Time: O(n·(n + E)·log n) — one Dijkstra per city, each O((n + E)·log n) with a binary heap; the threshold often makes each run much smaller.
- Space: O(n + E) — the adjacency lists, plus one heap and one settled array reused per run.

### Trade-offs

Faster than Floyd-Warshall on sparse graphs and on small thresholds, and it scales to many more cities. It needs a priority queue and more code; for the given limits either approach is fine, and Floyd-Warshall is easier to get right under pressure.

### Pitfalls and edge cases

- Do not count the source city itself; the reference starts its counter at -1.
- Skip heap entries for cities already settled (stale entries from earlier pushes).
- Isolated cities reach nobody and have count 0.

### Language notes

- Python: `heapq` over `(distance, city)` tuples, with a `set` of settled cities per run.
- TypeScript: the reference implements a binary min-heap, since there is no built-in priority queue; a `Uint8Array` marks settled cities.
- Java: `PriorityQueue<int[]>` ordered by the distance field.
- Kotlin: `PriorityQueue<Pair<Int, Int>>(compareBy { it.first })` inside a local function that captures the graph.
- Go: `container/heap` needs a type with `Len`, `Less`, `Swap`, `Push` and `Pop`; the reference defines `visitHeap` over `visit{distance, city}` structs. A `[]bool` of size `n` records the settled cities, and the closure `reachable` captures `graph`, `n` and the threshold.
- Rust: `BinaryHeap<Reverse<(i32, usize)>>` is the min-heap; the tuple compares by distance first. The closure `reachable` borrows `graph` immutably and allocates its own `settled` vector per source.
