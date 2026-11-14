# Rotting Oranges: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| simulate-minutes | brute | O((m·n)^2) | O(m·n) | the spreading rule is complicated and you want the most literal simulation |
| multi-source-bfs | optimal | O(m·n) | O(m·n) | default answer |

The minute at which an orange rots equals its distance, counted in side steps through oranges, from the nearest orange that was rotten at the start. The answer is the largest of these distances, or -1 when some fresh orange has no such path at all. The brute force replays the process minute by minute; the optimal approach computes all distances with one breadth-first search that starts from every rotten orange at once.

## Approach: simulate-minutes (Rescan the whole grid once per minute)

### Intuition

Do exactly what the statement says. For each minute, look at every fresh orange and check whether one of its neighbors is rotten; those oranges turn. Apply all changes for the minute together, so that an orange turning in this minute does not spread rot until the next one. Stop when a minute changes nothing.

### Algorithm

1. Set `minutes = 0`.
2. Repeat:
   1. Collect every fresh cell that has a rotten side neighbor.
   2. If none were collected, stop.
   3. Mark all collected cells rotten and add 1 to `minutes`.
3. If a fresh orange remains, return -1; otherwise return `minutes`.

### Correctness

By induction on the minute `t`: after `t` rounds, the rotten cells are exactly the cells whose distance from the starting rot is at most `t`. A round turns precisely the fresh cells adjacent to a cell rotten before the round, and because changes are applied after the scan, no cell turned in round `t` influences round `t`. The loop stops after the first round that changes nothing; from then on nothing can ever change, so remaining fresh oranges are unreachable (answer -1), and otherwise the last change happened in round `minutes`, the largest distance.

### Complexity

- Time: O((m·n)^2) — each round scans all m·n cells, and there can be up to about m·n rounds when the oranges form one long winding chain.
- Space: O(m·n) — the list of cells turning in one round.

### Trade-offs

Very easy to get right, and it adapts to odd rules (two rotten neighbors needed, rot that heals) with a one-line change. It rescans cells that cannot change, so a crate where the rot needs hundreds of minutes costs hundreds of full passes.

### Pitfalls and edge cases

- Do not update the grid during the scan: changing a cell immediately lets rot travel several steps in one minute.
- With no fresh orange at the start the answer is 0, even if there is no rotten orange either.
- A fresh orange next only to empty cells never rots; the final check catches it.

### Language notes

- Python: a list comprehension with `any(...)` collects the turning cells, which keeps the read and write phases visibly separate.
- TypeScript: `touchesRot` is an arrow function closing over the grid; the final check is `grid.some((row) => row.includes(FRESH))`.
- Java: a helper method checks the four neighbors with bounds tests; `List<int[]>` holds the turning cells.
- Kotlin: `flatMap` and `filter` build the list of turning cells as pairs; `FRESH in row` checks an `IntArray` with `contains`.
- Go: Like the other references, it marks oranges in place in `grid`, a slice of slices. The cells that turn this minute are collected in a `[][2]int` before any is changed. A package-level `const` pair names the two states.
- Rust: the parameter is declared `mut grid` so the reference can mark oranges in place. Positions are `usize`, so `checked_add_signed` turns a step off the top or left edge into `None`, and `grid.get(nr).and_then(|row| row.get(nc))` turns one past the other edges into `None` too, which keeps the neighbor test free of bounds arithmetic.

## Approach: multi-source-bfs (Breadth-first search from all rotten oranges at once)

### Intuition

Rot spreads exactly like a breadth-first search: everything at distance 1 from the sources turns first, then everything at distance 2, and so on. Starting the search with every rotten orange in the queue computes the distance to the nearest source for every orange. Processing the queue one level at a time makes each level one minute; counting the fresh oranges up front tells at the end whether any were never reached.

### Algorithm

1. Put every rotten cell in a queue and count the fresh cells in `fresh`.
2. Set `minutes = 0`. While the queue is not empty and `fresh > 0`:
   1. Add 1 to `minutes`.
   2. For each cell currently in the queue (one level), remove it and, for each fresh side neighbor, mark it rotten, decrement `fresh` and append it.
3. Return `minutes` if `fresh == 0`, otherwise -1.

### Correctness

The queue always holds one level of the search: at the start of iteration `t` it holds exactly the cells first reached at distance `t - 1`. Each fresh cell is marked rotten the first time a neighbor at distance `t - 1` is expanded, which is minute `t`, its true rotting time. When `fresh` reaches 0, the last level processed is the largest distance, so `minutes` is the answer. If the queue empties first, the remaining fresh cells have no path of oranges to any source, so the answer is -1. Stopping as soon as `fresh` is 0 also avoids counting one extra minute for the last level, whose cells have no fresh neighbors.

### Complexity

- Time: O(m·n) — every cell enters the queue at most once and is expanded once, with four neighbor checks.
- Space: O(m·n) — the queue can hold a large share of the cells at once.

### Trade-offs

One pass over the oranges instead of one per minute, and the distances it computes are exactly the rotting times, so the follow-up (report every orange's minute) is free. It relies on every orange rotting at its graph distance, which no longer holds under rules like "two rotten neighbors needed"; then the simulation is simpler.

### Pitfalls and edge cases

- Seed the queue with all rotten oranges before the search; starting one search per source gives the wrong minute where two waves meet.
- Count minutes per level, not per cell, and only while fresh oranges remain, or the answer is one too large.
- Return 0 when there were no fresh oranges at all, even if the queue is empty.

### Language notes

- Python: `collections.deque`, with `for _ in range(len(queue))` to process exactly one level per minute.
- TypeScript: no queue class is needed: each minute builds the next frontier as a new array, which also makes the levels explicit.
- Java: `ArrayDeque<int[]>`; the level loop counts down from `queue.size()` taken before the loop starts, since the queue grows during it.
- Kotlin: `repeat(queue.size)` reads the size once, which processes exactly one level; cells are encoded as `r * cols + c` in an `ArrayDeque<Int>`.
- Go: a slice is the queue: `queue[1:]` pops the front, `append` pushes the back, and `for frontier := len(queue); frontier > 0; frontier--` fixes the frontier size before the loop appends to the queue.
- Rust: `VecDeque` is the queue and `for _ in 0..queue.len()` evaluates the length once, so cells pushed during the minute wait for the next one. The grid walk uses `iter().enumerate()` on rows and cells, the form clippy asks for when a loop index only reads the grid.
