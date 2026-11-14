# Minimum Obstacle Removal: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| dijkstra | intermediate | O(m·n·log(m·n)) | O(m·n) | removal costs are arbitrary non-negative numbers |
| zero-one-bfs | optimal | O(m·n) | O(m·n) | every step costs 0 or 1, as here: default answer |

Model each cell as a node and each move as an edge whose cost is the value of the cell entered: 0 for an empty cell, 1 for an obstacle. The answer is the cheapest path from corner to corner. Unlike the problem that limits removals and minimizes moves, here the number of moves is free and only removals count, so this is a plain shortest-path problem with weights 0 and 1.

## Approach: dijkstra (Dijkstra with a binary heap on removals)

### Intuition

All costs are non-negative, so Dijkstra's algorithm applies: repeatedly settle the unsettled cell with the fewest removals so far, using a min-heap, and offer each neighbor the cost of entering it. The first time the goal is settled, its cost is the answer.

### Algorithm

1. Push `(0, start)` onto a min-heap.
2. Repeat: pop the entry with the smallest cost; skip it if its cell is settled. Otherwise settle it; if it is the goal, return the cost. Push `(cost + grid[neighbor], neighbor)` for every unsettled side neighbor.

### Correctness

This is Dijkstra's algorithm on the cell graph with edge weight `grid[target]`. Non-negative weights guarantee that cells are settled in non-decreasing order of their true cheapest cost, and that the cost recorded at settling is final. The goal is always reachable, because every obstacle may be removed, so the loop ends at the goal.

### Complexity

- Time: O(m·n·log(m·n)) — each cell is settled once and pushes at most four entries; each heap operation costs O(log(m·n)).
- Space: O(m·n) — the settled flags and up to about 4·m·n heap entries.

### Trade-offs

General and familiar: it would handle obstacles with different removal costs unchanged. With only 0 and 1 as costs, the heap's ordering work is unnecessary, and the deque version below drops the log factor.

### Pitfalls and edge cases

- Charge the cost of the cell being entered, not the cell being left; the start is empty and costs nothing.
- Skip outdated heap entries whose cell is already settled.
- The answer can be 0 even when obstacles stand between the corners on the straight route.

### Language notes

- Python: `heapq` over `(cost, row, column)` tuples.
- TypeScript: the reference implements a binary min-heap over `[cost, cell]` pairs, since there is no built-in priority queue.
- Java: `PriorityQueue<int[]>` ordered by `entry[0]`; the loop returns from inside `while (true)`.
- Kotlin: `PriorityQueue<Pair<Int, Int>>(compareBy { it.first })`, with cells encoded as `r * cols + c`.
- Go: `container/heap` needs `Len`, `Less`, `Swap`, `Push` and `Pop`; `entryHeap` holds `entry{cost, r, c}` and orders by cost. Neighbors come from a `[4][2]int` array of deltas with an explicit bounds test, and the closing `panic` only satisfies Go's requirement that the function ends in a return or panic.
- Rust: `BinaryHeap` is a max-heap, so `Reverse` over the `(cost, row, column)` tuple pops the cheapest entry first. `neighbors` uses `checked_add_signed` on the `usize` coordinates, which returns `None` instead of underflowing at row 0 or column 0, and `unreachable!` closes the loop that the grid guarantees always returns.

## Approach: zero-one-bfs (0-1 breadth-first search with a deque)

### Intuition

Dijkstra only needs the frontier ordered by cost. When every step costs 0 or 1, a double-ended queue keeps that order for free: a step onto an empty cell keeps the cost, so the cell goes to the front; a step onto an obstacle adds one, so it goes to the back. The deque then always holds costs `d` at the front and `d + 1` at the back, and taking from the front settles cells in non-decreasing order of cost.

### Algorithm

1. Set every cell's cost to infinity, the start's to 0, and put the start in a deque.
2. While the deque is not empty: take the front cell; if it is the goal, return its cost. For each side neighbor, compute `offered = cost + grid[neighbor]`; if it beats the neighbor's cost, store it and push the neighbor to the front when `grid[neighbor]` is 0, to the back when it is 1.
3. Return the goal's cost.

### Correctness

Invariant: the costs in the deque are non-decreasing from front to back and differ by at most one between the ends. Pushing a cost-`d` cell to the front while the front holds `d`, or a cost-`d + 1` cell to the back, preserves it. So cells come off the front in non-decreasing order of cost, exactly as in Dijkstra's algorithm, and the first time the goal comes off the front its cost is the cheapest. A cell may be pushed twice (once at `d + 1`, later at `d`); its second, cheaper copy comes out first, and the later copy only re-examines neighbors without improving anything.

### Complexity

- Time: O(m·n) — each cell's cost can only drop once from `d + 1` to `d` after its first assignment, so each cell is pushed a constant number of times and expanded with four neighbor checks.
- Space: O(m·n) — the cost grid and the deque.

### Trade-offs

Linear and barely longer than a breadth-first search. It works only for edge costs of 0 and 1 (or, with more buckets, small integers: Dial's algorithm); for arbitrary weights use Dijkstra.

### Pitfalls and edge cases

- Push zero-cost moves to the front and one-cost moves to the back; reversing them breaks the ordering.
- Compare against the stored cost before pushing, or the deque fills with useless copies.
- Return when the goal is taken from the front, which is the moment its cost is final.

### Language notes

- Python: `collections.deque` with `appendleft` and `append`.
- TypeScript: there is no built-in deque, so two arrays play its role: the current cost's list, which grows with zero-cost moves while it is scanned, and the next cost's list for one-cost moves; stale entries are skipped by comparing with the stored cost.
- Java: `ArrayDeque<int[]>` with `addFirst`, `addLast` and `pollFirst`.
- Kotlin: `kotlin.collections.ArrayDeque<Int>` with `addFirst`, `addLast` and `removeFirst`.
- Go: the standard library has no slice-backed deque, so the reference uses `container/list`, whose `PushFront`, `PushBack` and `Remove(Front())` are all O(1); the elements are `[2]int` pairs stored in `any` and asserted back on removal. A ring buffer would avoid the per-element allocation but needs more code.
- Rust: `VecDeque` is the deque, with `push_front`, `push_back` and `pop_front`. The `unreached` sentinel is `rows * cols` cast to `i32`, which the constraints keep at or under 10^5.
