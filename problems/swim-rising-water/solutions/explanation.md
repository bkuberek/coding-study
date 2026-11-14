# Swim in Rising Water: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| binary-search-bfs | optimal | O(n^2·log n) | O(n^2) | you want two simple, separately testable pieces |
| min-heap | optimal | O(n^2·log n) | O(n^2) | default answer; one pass, and it generalizes to any "minimize the maximum" path |

The time needed for a route is the highest floor on it, since the route opens exactly when the water covers its highest cell. The answer is the minimum, over all routes, of that maximum: a minimax (bottleneck) path problem on the grid graph. The grid has n^2 cells.

## Approach: binary-search-bfs (Binary search on the time with a reachability search)

### Intuition

For a fixed time `t`, the question "can I get across?" is a flood fill over cells with floor at most `t`. If it works at time `t`, it also works at every later time, because the set of usable cells only grows. That monotone yes/no answer is exactly what binary search needs: find the first `t` that answers yes.

### Algorithm

1. Set `low = max(grid[0][0], grid[n-1][n-1])` and `high = n^2 - 1`.
2. While `low < high`: let `middle = (low + high) / 2`. If the goal is reachable at `middle` (breadth-first search from the start over cells with floor at most `middle`), set `high = middle`, else `low = middle + 1`.
3. Return `low`.

### Correctness

Reachability is monotone in `t`: every route usable at `t` is usable at any larger time. The answer is at least both corner heights (you stand on both) and at most `n^2 - 1` (every cell is covered then, and the grid is connected). The loop keeps the invariant that the answer lies in `[low, high]`: a yes at `middle` means the answer is at most `middle`, a no means it is above `middle`. When the interval has one value, that value is the first time with a yes.

### Complexity

- Time: O(n^2·log n) — about log2(n^2) = 2·log2(n) searches, each visiting each cell at most once.
- Space: O(n^2) — the visited array and queue of one search.

### Trade-offs

Each piece is simple: a textbook flood fill and a textbook binary search, easy to test separately. It repeats the flood fill a logarithmic number of times, so it does more work than the heap version, and it needs the heights to be bounded (they are here) to search over them; with arbitrary heights, binary search over the sorted list of distinct heights instead.

### Pitfalls and edge cases

- Start `low` at the larger corner height, not at 0: a search below the start's own height must fail immediately.
- Use `high = middle` on success and `low = middle + 1` on failure; the other combination loops forever.
- A 1 by 1 pool returns its only height, 0.

### Language notes

- Python: the reachability check is a nested function with its own `deque` and visited grid.
- TypeScript: cells are encoded as `r * n + c`, visited flags live in a `Uint8Array`, and the queue is an array with a moving head.
- Java: `(low + high) >>> 1` is the overflow-safe midpoint idiom, harmless here; `ArrayDeque<int[]>` holds the cells.
- Kotlin: a local function captures `grid` and `n`; `if (reachable(middle)) high = middle else low = middle + 1` keeps the loop compact.
- Go: `reachable` is a closure over `grid` and `n`. The queue is a slice of `[2]int` pairs walked with a `head` index, which avoids re-slicing and costs one append per cell; `max` is the built-in (Go 1.21+). The four moves come from a `[4][2]int` array of deltas.
- Rust: `reachable` is a free function taking `&[Vec<i32>]`, so the search borrows the grid without copying it. Coordinates are `usize` and the deltas `isize`: the neighbor is computed as `isize`, bounds-checked, then converted back, because `r - 1` on a `usize` row 0 would panic. The queue is a `VecDeque`.

## Approach: min-heap (Dijkstra-style search on the highest cell so far)

### Intuition

Grow the region you can reach, always adding the neighboring cell that keeps the route's highest floor as low as possible. A min-heap ordered by "highest floor on the route so far" gives that cell. This is Dijkstra's algorithm with the path cost defined as the maximum of the cell heights instead of their sum; the first time the goal comes off the heap, its cost is the answer.

### Algorithm

1. Mark the start as seen and push `(grid[0][0], start)`.
2. Repeat: pop the entry `(level, cell)` with the smallest level. If `cell` is the goal, return `level`. Otherwise, for each unseen side neighbor, mark it seen and push `(max(level, height(neighbor)), neighbor)`.

### Correctness

Dijkstra's argument needs only that a route's cost never decreases when the route is extended, which holds for the maximum just as for a sum of non-negative weights. Entries leave the heap in non-decreasing order of level, and each cell is pushed once, from the first neighbor that reached it, which comes off the heap no later than any other neighbor; so the level pushed for a cell is the lowest possible highest floor on any route to it. The goal's popped level is therefore the minimax value. Marking cells when they are pushed is safe for the same reason: no later push could offer a lower level.

### Complexity

- Time: O(n^2·log n) — each of the n^2 cells is pushed and popped once, at O(log n^2) = O(log n) per heap operation.
- Space: O(n^2) — the seen array and the heap.

### Trade-offs

One pass, no bound on heights needed, and the idea carries over to every "minimize the maximum edge or cell on a path" problem. A third option, adding cells in increasing height to a disjoint-set structure until the corners join, is equally fast and pairs nicely with Kruskal's algorithm, but needs the cells sorted first.

### Pitfalls and edge cases

- The cost of extending a route is `max(level, height)`, not `level + height`.
- The start cell's own height counts: the first entry carries `grid[0][0]`, not 0.
- Return when the goal is popped. With marking on push, the goal's first push already carries the optimal level, but returning on pop is the habit that stays correct in every Dijkstra variant, including those that mark on pop.

### Language notes

- Python: `heapq` over `(level, row, column)` tuples.
- TypeScript: the reference implements a binary min-heap over `[level, cell]` pairs, since there is no built-in priority queue.
- Java: `PriorityQueue<int[]>` ordered by `entry[0]`; `while (true)` ends by returning at the goal, which is always reachable.
- Kotlin: `PriorityQueue<Pair<Int, Int>>(compareBy { it.first })`, with cells encoded as `r * n + c`.
- Go: `container/heap` needs `Len`, `Less`, `Swap`, `Push` and `Pop`; `entryHeap` holds `entry{level, r, c}` and orders by level. The final `panic` is only there because Go requires a `return` or `panic` at the end of the function.
- Rust: `BinaryHeap` is a max-heap, so `Reverse` over the `(level, row, column)` tuple pops the lowest level first. The loop never falls through for valid input, so `unreachable!` states that and satisfies the return type.
