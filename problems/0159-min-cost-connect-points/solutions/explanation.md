# Minimum Cost to Connect Points: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| kruskal | intermediate | O(n^2·log n) | O(n^2) | the edges are given as a list, or the graph is sparse |
| prim-dense | optimal | O(n^2) | O(n) | complete or dense graphs, like this one: default answer |

The points form a complete graph with Manhattan distances as edge weights, and the cheapest set of cables connecting everything is a minimum spanning tree (a cheapest connected set never contains a cycle, since dropping any cable of a cycle keeps it connected and costs less). Both classic algorithms apply; the graph's density decides which one is faster.

## Approach: kruskal (Kruskal over all sorted pairs with union-find)

### Intuition

Consider cables from cheapest to most expensive. A cable between two points that are already connected would close a cycle, so skip it; any other cable joins two groups and is safe to take. A disjoint-set structure answers "already connected?" in near-constant time. After `n - 1` cables everything is connected.

### Algorithm

1. List all `n·(n - 1)/2` pairs with their Manhattan distances and sort them by distance.
2. Start a disjoint set with every point in its own group.
3. For each pair in sorted order, while fewer than `n - 1` cables are taken: if its points are in different groups, merge the groups and add the cost to the total.
4. Return the total.

### Correctness

The cut property: for any split of the points into two sides, the cheapest cable crossing the split belongs to some minimum spanning tree. When Kruskal takes a pair joining groups `A` and `B`, every cheaper pair lies inside a group (or it would have been taken), so this pair is the cheapest one crossing the split "group `A` versus everything else", and taking it keeps the chosen cables inside some minimum tree. By induction the final `n - 1` cables form a minimum spanning tree.

### Complexity

- Time: O(n^2·log n) — building the pairs is O(n^2), sorting them O(n^2·log n^2) = O(n^2·log n), and the union-find work is nearly linear in the number of pairs.
- Space: O(n^2) — the list of all pairs; for 1000 points that is about half a million entries.

### Trade-offs

Simple and general: it works on any edge list, and on sparse graphs it is the natural choice. Here, though, every pair is an edge, so it materializes and sorts the whole complete graph, which costs both a log factor and quadratic memory. Packing each pair into one integer keeps the sort fast in Java, Kotlin and TypeScript.

### Pitfalls and edge cases

- A single point needs no cable: the answer is 0, and the pair list is empty.
- Stop after `n - 1` cables; the rest of the sorted list cannot change the answer.
- Ties between equal costs may be broken any way; every choice leads to the same total.

### Language notes

- Python: a generator of `(cost, i, j)` tuples fed to `sorted`; tuples compare by cost first.
- TypeScript: pairs are packed as `(cost * 1024 + i) * 1024 + j` into a `Float64Array`, whose `sort()` is numeric (a plain array's `sort()` would compare strings); the packed values stay below 2^53, so they are exact.
- Java: pairs are packed into a `long[]` as `cost << 20 | i << 10 | j` and sorted with `Arrays.sort`, which avoids allocating half a million objects.
- Kotlin: the same packing into a `LongArray` with `shl`, `or` and `and`; `LongArray.sort()` sorts the primitives in place.
- Go: the pairs are packed into an `int` (64 bits wide) as `cost<<20 | i<<10 | j`, like Java and Kotlin, and `slices.Sort` orders the plain integers without allocating a value per pair. The find function is a closure, and `parent[node], node = root, parent[node]` is the same one-step swap as Python's.
- Rust: a `Vec<(i32, usize, usize)>`; tuples compare field by field, cost first, like Python's tuples, so `sort_unstable()` orders the pairs, at 24 bytes per pair. `find` is a function over `&mut [usize]` instead of a closure, because a closure would keep `parent` borrowed while the main loop also writes to it.

## Approach: prim-dense (Prim with an array of cheapest connections)

### Intuition

Grow one tree from any point. At every step, the cheapest cable from a point outside the tree to a point inside it is safe to take (again the cut property, with the tree as one side). Keep, for every outside point, the cost of its cheapest cable into the tree. Each round, add the outside point with the smallest such cost, then update the others with their distance to the new point. On a complete graph, a plain array beats a heap: every round already has to look at every point.

### Algorithm

1. Set `cheapest[0] = 0` and `cheapest[i] = infinity` for the other points.
2. Repeat `n` times: pick the point `p` outside the tree with the smallest `cheapest[p]`, add it to the tree and add `cheapest[p]` to the total; for every point `q` still outside, set `cheapest[q] = min(cheapest[q], dist(p, q))`.
3. Return the total.

### Correctness

Invariant: `cheapest[q]` is the cost of the cheapest cable from `q` to the current tree. It holds after each update, because the only new tree point is `p`. Choosing the outside point with the smallest value takes the cheapest cable crossing the split "tree versus rest", which by the cut property belongs to some minimum spanning tree that contains the cables chosen so far. After `n` rounds the tree spans all points at minimum cost.

### Complexity

- Time: O(n^2) — `n` rounds, each scanning all points once to pick the minimum and once to update.
- Space: O(n) — the `cheapest` array and the tree flags; distances are computed on the fly.

### Trade-offs

Optimal for a complete graph: it never builds the edge list and needs only linear memory. A heap-based Prim would cost O(n^2·log n) here, because every pair is a potential update. On sparse graphs given as edge lists, Kruskal or heap-based Prim is better.

### Pitfalls and edge cases

- Start with cost 0 for the first point; it joins the tree without a cable.
- Update only points outside the tree.
- Integer overflow is not a concern: a distance is at most 4·10^6 and the tree's total stays far below 2^31 for these coordinates.

### Language notes

- Python: `min(..., key=cheapest.__getitem__)` picks the next point; `math.inf` starts the array.
- TypeScript: two plain loops per round; `Infinity` marks points not yet offered a cable.
- Java: `Integer.MAX_VALUE` marks them, and `Math.min` updates the array.
- Kotlin: `(0 until n).filter { !inTree[it] }.minBy { cheapest[it] }` picks the next point; `val (x, y) = points[point]` destructures an `IntArray`.
- Go: `math.MaxInt` marks points not yet offered a cable; it is only compared, never added to, and the scan is an explicit loop. Rust: `i32::MAX` marks them, and `(0..n).filter(...).min_by_key(...)` picks the next point, the first of several equal minima, like Python's `min`.
