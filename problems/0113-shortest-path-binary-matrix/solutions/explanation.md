# Shortest Path in a Binary Grid: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| relaxation-sweeps | brute | O(n^4) | O(n^2) | as a stepping stone toward Bellman-Ford; never the interview answer here |
| bfs | optimal | O(n^2) | O(n^2) | default answer |

The open cells form a graph in which every cell is linked to up to eight open neighbors, and every edge has the same cost: one more cell on the path. The grid has n^2 cells. With equal edge weights, the length of a shortest path is the breadth-first level of the target. The brute force reaches the same distances by repeated local improvement, which is how Bellman-Ford works on weighted graphs.

## Approach: relaxation-sweeps (Relax every cell until no distance improves)

### Intuition

Give every cell a tentative distance: 1 for the start, "unreached" for the rest. A cell's true distance is one more than the best distance among its open neighbors, so sweep the grid and let every open cell lower its tentative distance to `neighbor + 1` whenever a neighbor offers a better value. When a full sweep changes nothing, every tentative distance is final.

### Algorithm

1. If either corner is blocked, return -1.
2. Set `dist[0][0] = 1` and every other `dist` to "unreached".
3. Repeat until a sweep changes nothing: visit every open cell (alternating between forward and backward reading order), and for each of its eight neighbors set `dist[cell] = min(dist[cell], dist[neighbor] + 1)`.
4. Return `dist` of the bottom-right cell, or -1 if it is still unreached.

### Correctness

Every tentative value is the length of some real path, because it only ever becomes a neighbor's value plus one step. Conversely, after a sweep in which a cell's predecessor on a shortest path already held its true distance, the cell holds its true distance too; a shortest path has at most n^2 cells, so after at most n^2 sweeps all distances are exact, and the loop stops only when no value can improve, which is exactly when all values are final. The end cell's value is then its shortest path length, or unreached when no path exists.

### Complexity

- Time: O(n^4) — each sweep checks eight neighbors of all n^2 cells, and a path that zigzags against the scan direction can need up to about n^2 sweeps.
- Space: O(n^2) — the distance grid.

### Trade-offs

It needs no queue and generalizes to any edge weights (it is Bellman-Ford with the grid as the edge list), but it redoes work on cells whose distance is already final. Alternating the scan direction makes it fast on most grids; long winding corridors still force many sweeps, and a corridor that steps diagonally down and up in turn needs one sweep per step, about n^2 / 3 sweeps of n^2 cells. Breadth-first search finalizes each cell exactly once.

### Pitfalls and edge cases

- Blocked cells never get a distance and never offer one.
- Stop only after a whole sweep without changes; stopping when the end cell first gets a value can return a path that is too long.
- A one-cell grid that is open has answer 1.

### Language notes

- Python: the cell order is a list that is reversed after each sweep.
- TypeScript: one loop index runs forward or backward over the flattened cells; `STEPS` is built once at module level with `flatMap`.
- Java: the eight directions are a constant `int[][]`; `Arrays.fill` sets the unreached value row by row.
- Kotlin: `STEPS` is a private top-level list of pairs, destructured in the loop as `(dr, dc)`.

## Approach: bfs (Breadth-first search over eight directions)

### Intuition

All steps cost the same, so explore the grid in rings around the start: first every cell one step away, then every cell two steps away, and so on. The first time the search reaches a cell, it has found that cell's shortest path. Stop as soon as the bottom-right cell comes off the queue.

### Algorithm

1. If either corner is blocked, return -1.
2. Set `dist[0][0] = 1` and put the start in a queue.
3. While the queue is not empty, take a cell; if it is the bottom-right cell, return its `dist`. Otherwise, for each of its eight neighbors that is open and unreached, set `dist[neighbor] = dist[cell] + 1` and enqueue it.
4. Return -1.

### Correctness

Breadth-first search takes cells off the queue in non-decreasing order of `dist`, and a cell is assigned its `dist` when it is first discovered, from a neighbor that was itself reached by a shortest path. So each `dist` equals the length of a shortest path to that cell (counted in cells). If the end cell is never reached, no sequence of open neighboring cells links the corners, and the answer is -1.

### Complexity

- Time: O(n^2) — every open cell is enqueued at most once, and each dequeue checks eight neighbors.
- Space: O(n^2) — the distance grid and the queue.

### Trade-offs

The standard answer: linear in the number of cells and short to write. A* with the Chebyshev distance to the corner as its estimate often visits fewer cells, but it needs a priority queue and only pays off on large, open grids. If diagonal steps cost more than straight ones, the edges are no longer equal and Dijkstra's algorithm is needed instead.

### Pitfalls and edge cases

- Check both corners before the search; a blocked start must return -1, not 1.
- Mark cells when they are enqueued, or the same cell enters the queue up to eight times.
- The length counts cells, not steps: the start already has length 1.
- Corner-cutting diagonals are allowed: a diagonal step between two blocked cells is legal.

### Language notes

- Python: `collections.deque`; a `dist` of 0 doubles as "not reached".
- TypeScript: the distances live in one flat `Int32Array`, cells are encoded as `r * n + c`, and the queue is an array with a moving head.
- Java: `ArrayDeque<int[]>` and an `int[][]` of distances, zero-initialized by the language.
- Kotlin: `ArrayDeque<Int>` with encoded cells; `nr in 0 until n` keeps the bounds checks short.
