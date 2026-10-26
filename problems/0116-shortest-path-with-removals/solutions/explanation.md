# Shortest Path With Obstacle Removals: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| state-bfs | optimal | O(m·n·K) | O(m·n·K) | default answer; the cleanest model of the problem |
| best-remaining-bfs | optimal | O(m·n·K) | O(m·n·K) | the same search with dominated states pruned; usually much faster |

Here K = min(k, m + n - 3): a straight Manhattan route from corner to corner has m + n - 1 cells, both corners are empty, so it never needs more than m + n - 3 removals, and any larger `k` behaves like that bound. Position alone is not a complete state: what matters is the cell together with how many removals are still available. Both approaches run breadth-first search over those states, since every move costs one.

## Approach: state-bfs (Breadth-first search over (cell, removals used) states)

### Intuition

Make the removals part of the position. A state is `(row, column, used)`. Stepping onto an empty cell keeps `used`; stepping onto an obstacle increases it by one, which is allowed only while `used <= K`. Every move costs one step, so breadth-first search over these states reaches the goal cell first along a route with the fewest moves, whatever its `used` count.

### Algorithm

1. Set `K = min(k, m + n - 3)` (and at least 0).
2. Mark the state `(0, 0, 0)` seen and start the first level with it, at `moves = 0`.
3. For each level: if any state is at the bottom-right cell, return `moves`. Otherwise, for each state and each of its four neighbors inside the grid, compute `after = used + grid[neighbor]`; if `after <= K` and `(neighbor, after)` is not seen, mark it and add it to the next level. Add 1 to `moves`.
4. If the levels run out, return -1.

### Correctness

Legal routes of the problem correspond one-to-one with walks in the state graph from `(0, 0, 0)`: each step updates the removal count exactly as the route does, and the count never exceeds `K`. Capping `k` at `K` loses nothing, because if any route reaches the goal, the straight Manhattan route uses at most m + n - 3 removals, so with `k >= m + n - 3` the shortest answer is reachable within the cap, and with smaller `k` the cap is `k` itself. Breadth-first search finds the fewest moves to any state at the goal cell, which is the answer, or exhausts the reachable states, in which case no route exists.

### Complexity

- Time: O(m·n·K) — there are m·n·(K + 1) states, each expanded at most once with four neighbor checks.
- Space: O(m·n·K) — one seen flag per state, and the levels can hold a large share of them.

### Trade-offs

The textbook answer and easy to argue about: the state is explicit and nothing clever happens. It spends memory on every `(cell, used)` combination even when most are useless, for example reaching a cell later with more removals spent than an earlier visit.

### Pitfalls and edge cases

- Track removals per state, not per cell: a plain visited grid wrongly blocks a cell that a later route reaches with removals to spare.
- Cap `k`; without the cap, `k = m·n` makes the state space grow to (m·n)^2.
- A 1 by 1 grid returns 0 moves.
- Return as soon as the goal cell appears, at any removal count.

### Language notes

- Python: a three-level nested list of booleans, indexed `[r][c][used]`, and a deque of tuples processed one level at a time.
- TypeScript: each state is packed into one number, `(r * cols + c) * layers + used`, and the seen flags live in a flat `Uint8Array`.
- Java: a `boolean[rows][cols][K + 1]` array and `int[]` triples in an `ArrayDeque`.
- Kotlin: `Triple<Int, Int, Int>` states destructure as `val (r, c, used)`; `repeat(queue.size)` handles one level.

## Approach: best-remaining-bfs (Breadth-first search that keeps the most removals left per cell)

### Intuition

Two visits to the same cell can be compared: one that arrives no later and with at least as many removals left is at least as good in every way. Breadth-first search reaches cells in non-decreasing order of moves, so a new visit is useful only if it has strictly more removals left than every earlier visit of that cell. Keeping, per cell, the best number of removals left seen so far prunes all dominated states. If `k` already covers the straight route, return `m + n - 2` immediately.

### Algorithm

1. If `k >= m + n - 3`, return `m + n - 2`.
2. Set `best[cell] = -1` everywhere, `best[0][0] = k`, and start the first level with `(0, 0, k)`.
3. For each level: if a state is at the bottom-right cell, return `moves`. Otherwise, for each neighbor inside the grid, compute `remaining = left - grid[neighbor]`; if `remaining > best[neighbor]`, set `best[neighbor] = remaining` and add the state to the next level. Add 1 to `moves`.
4. Return -1 when the levels run out.

### Correctness

The search is the state search of `state-bfs` with some states skipped. A skipped state `(cell, remaining)` is reached at some level after a state `(cell, best)` with `best >= remaining` was already reached at the same or an earlier level. Every route that continues from the skipped state can continue the same way from the kept one, arriving at the goal no later and with removals to spare, so skipping cannot lose the optimum. The shortcut in step 1 is the Manhattan bound from the overview: with that many removals the straight route is legal, and no route is shorter than `m + n - 2` moves.

### Complexity

- Time: O(m·n·K) — a cell can be accepted again only when its best count strictly rises, at most K + 1 times, so at most m·n·(K + 1) states are expanded; usually far fewer.
- Space: O(m·n·K) — the per-cell array is O(m·n), but in the worst case a level can still hold several states per cell; in practice the queue stays small.

### Trade-offs

Same worst case, less memory for the bookkeeping and typically far fewer states, because most `(cell, used)` combinations are dominated. The domination argument is the part an interviewer will probe, so be ready to state it. A* with the Manhattan distance as estimate can cut the work further, at the price of a priority queue.

### Pitfalls and edge cases

- Compare with `>`, not `>=`: re-adding a visit with the same count left only repeats work.
- The pruning relies on breadth-first order; with a depth-first search, an earlier visit may come with more moves, and the rule would cut correct routes.
- Keep the shortcut condition as `k >= m + n - 3`; with `m = n = 1` it returns 0.

### Language notes

- Python: `best` is a list of lists filled with -1; states are `(r, c, left)` tuples.
- TypeScript: `best` is an `Int32Array` over flattened cells, and each level is an array of `[cell, left]` pairs.
- Java: `int[][] best` filled with `Arrays.fill`; `int[]` triples in an `ArrayDeque`, processed one level at a time.
- Kotlin: `Array(rows) { IntArray(cols) { -1 } }` for `best`; `Triple` states destructured in the loop.
