# Pacific Atlantic Water Flow: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| per-cell-search | brute | O((m·n)^2) | O(m·n) | tiny maps, or as a check for the fast version |
| ocean-bfs | optimal | O(m·n) | O(m·n) | default answer |

Water moves from a cell to a side neighbor that is not higher. The question for each cell is whether two sets of target cells (the two coasts) are reachable along such moves. Asking it cell by cell repeats work; reversing the direction of the moves turns the problem into two searches that start at the coasts.

## Approach: per-cell-search (Follow the water downhill from every cell)

### Intuition

Take the statement literally: for every cell, explore all cells its water can reach and see whether the exploration touches a Pacific cell and an Atlantic cell. A depth-first search that only steps to neighbors that are not higher does exactly that exploration.

### Algorithm

1. For each cell `(r, c)`:
   1. Run a depth-first search from `(r, c)` with its own visited set, stepping from a cell to each side neighbor whose height is at most the current cell's height.
   2. Note whether any visited cell is in the top row or left column (Pacific) and whether any is in the bottom row or right column (Atlantic); stop early once both are seen.
   3. If both were seen, add `[r, c]` to the answer.
2. Return the answer.

### Correctness

The search from a cell visits exactly the cells reachable by legal water moves: it only takes legal moves, and it continues from every visited cell until all their legal moves are used. Rain can drain into an ocean exactly when such a route reaches one of that ocean's coast cells, so the cell is added exactly when both oceans are reachable.

### Complexity

- Time: O((m·n)^2) — each of the m·n searches can visit every cell; on a flat map that is m·n steps per search.
- Space: O(m·n) — one visited mark and at most one stack entry per cell for the search in progress.

### Trade-offs

Direct and easy to trust, which makes it the oracle, but each search rediscovers what neighboring searches already learned. With early stopping it is fast on steep, varied terrain; on plateaus and in basins it is quadratic (in a bowl of flat rings, water from every inner cell fills the rings inside it and never reaches a coast), and at 200 by 200 that is over a billion steps.

### Pitfalls and edge cases

- The move rule is "not higher" (`<=`), not "strictly lower"; equal heights let water spread across plateaus.
- Each search needs a fresh visited set. The references avoid clearing by storing the id of the search that marked a cell.
- A cell on the coast already touches its ocean, before any move.

### Language notes

- Python: the visited set is a `set` of tuples, created per search.
- TypeScript: one `Int32Array` holds, for each cell, the id of the last search that visited it, so no array is reallocated or cleared per search.
- Java: the same idea with an `int[][]` filled with -1 once; `ArrayDeque<int[]>` is the stack.
- Kotlin: the search is a local function that captures `seen`, `rows` and `cols`; `nr !in 0 until rows` is the bounds check.
- Go: a flat `[]int` of `rows*cols` entries holds the id of the last search that visited each cell, as in the Java and TypeScript versions, so nothing is reallocated or cleared per search; ids start at 1 because Go zeroes the slice. A slice of `[2]int` is the stack (`stack[len(stack)-1]`, `stack[:len(stack)-1]`, `append`). The long condition is split after `&&`, because Go ends a statement at a line break only after a complete expression.
- Rust: the id grid is a `Vec<Vec<usize>>`, passed as `&mut [Vec<usize>]`, so the search borrows it mutably while `heights` stays a shared borrow. A step off the grid is caught by a `neighbor` helper using `checked_add_signed`, which returns `None` for a negative coordinate instead of wrapping.

## Approach: ocean-bfs (Climb uphill from both coasts)

### Intuition

Reverse every move. Water can go from `a` to its neighbor `b` when `height(b) <= height(a)`; read backwards, a search that starts at the coast may go from `b` to `a` when `height(a) >= height(b)`, that is, uphill or level. The cells such a search reaches from a coast are exactly the cells whose water can flow down to that coast. One multi-source search per ocean, then intersect.

### Algorithm

1. Put every Pacific cell (top row and left column) in a queue and mark it reached.
2. While the queue is not empty, take a cell and mark and enqueue each unmarked side neighbor whose height is at least the current cell's height.
3. Repeat steps 1 and 2 with the Atlantic cells (bottom row and right column) and a second set of marks.
4. Return every cell marked by both searches.

### Correctness

Claim: the Pacific search marks a cell exactly when its water can reach the Pacific. If water can go from a cell `x` along `x = x0, x1, ..., xk` with `xk` on the Pacific coast, the reversed sequence starts at a coast cell and each step goes to a cell that is at least as high, so the search marks every cell of it, `x` included. Conversely, each cell the search marks was reached by such reversed steps from a coast cell, so reading the steps forward gives a legal water route from it to the coast. The same holds for the Atlantic, and a cell is in the answer exactly when both hold.

### Complexity

- Time: O(m·n) — each search enqueues each cell at most once and checks four neighbors per cell; the final scan is m·n.
- Space: O(m·n) — two arrays of marks and a queue of at most m·n cells.

### Trade-offs

Two linear searches replace m·n separate ones, which is the whole point of the problem. Breadth-first and depth-first order are equally correct here, since only reachability matters; the queue version avoids recursion depth issues on large maps. It needs a second marks array, which is negligible.

### Pitfalls and edge cases

- Reverse the comparison: going uphill from the coast means `neighbor >= current`. Using `<=` here searches downhill from the coast and gives wrong cells.
- Seed each search with all its coast cells at once; corner cells belong to both coasts, and a single row or column touches both oceans everywhere.
- Mark cells when enqueuing to avoid duplicates in the queue.

### Language notes

- Python: `collections.deque` for the queue; the coast is built as a set of coordinates so the corner shared by the top row and the left column is enqueued once.
- TypeScript: cells are encoded as `r * cols + c` in a `Uint8Array` of marks, and the queue is a plain array with a moving head.
- Java: two `boolean[][]` arrays and two `ArrayDeque<int[]>` queues, seeded in one pass over the grid; the result is converted with `toArray(new int[0][])`.
- Kotlin: the search takes the coast as a lambda `(Int, Int) -> Boolean`, and the answer is collected with `filter` and `map` over the cell indexes.
- Go: `climb` is a closure over `heights`, and the coast is a list of `[2]int` cells that is built by two short loops (the top or bottom row, then the left or right column). The corner cell appears in both loops, so `climb` skips a cell it has already marked, which makes it enqueue the corner once, as Python's set does. A slice is the queue (`queue[0]`, `queue = queue[1:]`, `append`).
- Rust: `climb` takes the coast as a slice of cells and returns the grid of reached flags; the two coasts are built with `map` and `chain` over the columns and the rows. `VecDeque` is the queue (`pop_front`, `push_back`), and `vec![vec![false; cols]; rows]` makes independent rows.
