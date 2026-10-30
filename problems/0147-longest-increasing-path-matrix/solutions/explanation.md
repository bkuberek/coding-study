# Longest Increasing Path in a Matrix: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| memoization | optimal | O(m * n) | O(m * n) | default answer when recursion depth is safe; also the oracle |
| sorted-cells | intermediate | O(m * n * log(m * n)) | O(m * n) | an iterative DP that is easy to justify |
| topological-sort | optimal | O(m * n) | O(m * n) | no recursion; shows the graph view explicitly |

The cells form a directed graph: an edge goes from a cell to each neighbor with a strictly larger value. Because values strictly increase along every edge, the graph has no cycles, and the question is the longest path in a directed acyclic graph. The DP state is a cell, its value the longest increasing path starting there. A depth-first search from every cell without a memo is correct but re-explores shared suffixes: on a grid where values grow along both axes, the number of increasing paths, and hence the work, is exponential in the side length. It is not among the references.

The time classes use the number of cells as n.

## Approach: memoization (Depth-first search from every cell with a memo table)

### Intuition

The longest increasing path starting at a cell is the cell itself plus the longest path starting at one of its larger neighbors. That value never changes, whichever path led to the cell, so compute it once with a depth-first search and remember it. Starting the search from every cell then costs nothing extra for cells already explored.

### Algorithm

1. Let `explore(r, c)` return the longest increasing path starting at `(r, c)`; 0 in the memo means "not computed".
2. `explore(r, c) = 1 + max(explore(neighbor))` over the neighbors with a larger value, or 1 if there are none; cache it.
3. Return the maximum of `explore` over all cells.

### Correctness

By induction on the value of the cell, from the largest down: a cell with no larger neighbor starts only the one-cell path. Otherwise, a longest path from `(r, c)` continues to some larger neighbor and then follows a path from it, which can be taken to be a longest one, so the recurrence holds. The recursion terminates because every call moves to a strictly larger value; no cycle exists to loop on.

### Complexity

- Time: O(m * n) — each cell is computed once and looks at its four neighbors.
- Space: O(m * n) — the memo, plus a recursion stack as deep as the longest path (at most 2000 here).

### Trade-offs

Short and fast; the standard interview answer. The recursion depth equals the answer, which is why the constraints cap the longest path: on a 200 by 200 snake it would reach 40,000 frames and overflow a default stack. The other two approaches have no recursion.

### Pitfalls and edge cases

- Use strict comparisons: equal neighbors are not steps, and allowing them would create cycles.
- No visited set is needed: an increasing path can never revisit a cell.
- A memo value of 0 can mean "unknown" because every real answer is at least 1.

### Language notes

- Python: a nested function over a list-of-lists memo; the runner raises the recursion limit.
- TypeScript: `Int32Array` rows and a constant list of four steps.
- Java: fields for the grid and the memo, a static step table.
- Kotlin: a local recursive `fun`, steps as `Pair`s destructured in the loop, and `in 0 until rows` range checks.
- Go: the steps are a package-level `[4][2]int`, and the bounds test names both ends because `int` is signed.
- Rust: a `usize` cannot go below zero, so `checked_add_signed(dr)` (stable since 1.66) returns `None` for a step off the top or left edge, and `let ... else { continue }` skips it; the upper bounds are tested afterwards. The steps are `(isize, isize)` pairs.

## Approach: sorted-cells (Tabulate the cells in decreasing order of value)

### Intuition

The recursion computes larger cells before smaller ones. Sorting the cells by value, largest first, gives that order directly: when a cell is processed, all its larger neighbors are already final, so one pass of the recurrence fills the table without recursion.

### Algorithm

1. Fill `longest` with 1.
2. Sort the cells by value, descending.
3. For each cell in that order, set `longest[cell] = max(longest[cell], 1 + longest[neighbor])` for every larger neighbor.
4. Return the maximum of `longest`.

### Correctness

The decreasing order is a topological order of the step graph reversed: every edge goes from a smaller value to a larger one, and the larger end is processed earlier. Equal values are never connected by an edge, so their relative order does not matter. Each update applies the recurrence with final values, so by induction every entry is correct.

### Complexity

- Time: O(m * n * log(m * n)) — the sort dominates; the pass is linear.
- Space: O(m * n) — the order and the table.

### Trade-offs

Iterative and easy to reason about, but the sort adds a log factor that the other two approaches avoid. It is a good bridge between "DP over a table" and "DP over a DAG".

### Pitfalls and edge cases

- Sort by value only; tie-breaking is irrelevant, but comparing with `<=` in the neighbor test would wrongly link equal cells.

### Language notes

- Python: `sorted` with a key on the cell's value.
- TypeScript: cells numbered `r * columns + c`, sorted with a numeric comparator; values up to 2^31 - 1 subtract safely in doubles.
- Java: each `(value, cell)` pair is packed into one `long` (value shifted left by 16 bits) so `Arrays.sort` on primitives orders the cells without boxing.
- Kotlin: `sortedByDescending` on the cell numbers.
- Go: `sort.Slice` over a slice of `[2]int` cells with a comparator that reads the matrix. It is not stable, which is fine here because ties may go either way.
- Rust: `sort_by_key(|&(r, c)| Reverse(matrix[r][c]))`; `std::cmp::Reverse` turns the ascending sort into a descending one.

## Approach: topological-sort (Peel layers of local maxima with Kahn's algorithm)

### Intuition

Run Kahn's algorithm on the step graph from the sinks: a cell with no larger neighbor is a local maximum, the end of every path through it. Remove all of them at once; this is round 1. Their removal turns new cells into local maxima of what remains; remove those in round 2, and so on. A cell removed in round k starts a longest path of exactly k cells, so the number of rounds is the answer.

### Algorithm

1. For every cell, count its larger neighbors (`larger[cell]`, its out-degree).
2. Put all cells with count 0 into the first layer.
3. While the layer is not empty: count a round; for each cell in it, decrement the count of every smaller neighbor, and put the neighbors that reach 0 into the next layer.
4. Return the number of rounds.

### Correctness

Claim: the cells removed in round k are exactly those whose longest increasing path has k cells. Round 1 removes the cells with no larger neighbor, whose longest path is 1. A cell reaches count 0 in round k exactly when all its larger neighbors were removed in rounds before k and at least one in round k - 1 (otherwise it would have reached 0 earlier); by induction its longest path is then 1 + (k - 1) = k. The graph is acyclic, so every cell is eventually removed, and the last round number is the maximum path length.

### Complexity

- Time: O(m * n) — each cell enters a layer once, and each of the at most 4 m n edges is examined a constant number of times.
- Space: O(m * n) — the counts and the layers.

### Trade-offs

Linear without recursion, so it is safe for any path length; it is longer to write than the memoized search and needs the graph view to explain. Counting rounds instead of storing per-cell lengths keeps the memory to one counter per cell.

### Pitfalls and edge cases

- Process the layer completely before counting the next round; mixing layers in one queue without tracking boundaries gives the number of cells, not rounds.
- Decrement only for strictly smaller neighbors: those are the cells that have an edge into the removed cell.

### Language notes

- Python: a generator for the in-grid neighbors and plain lists for the layers.
- TypeScript: an `Int8Array` of counts (at most 4) indexed by cell number.
- Java: one `ArrayDeque<Integer>` processed in chunks of its current size, which delimits the rounds.
- Kotlin: neighbors as lists of pairs and `--larger[nr][nc] == 0` to decrement and test in one step.
- Go: a small `inGrid` closure and the shared `steps` table; each layer is a `[][2]int` grown with `append`, and an empty (nil) next layer ends the loop.
- Rust: `neighbors` is a function that returns `impl Iterator`, built from `filter_map`, `checked_add_signed` and `then_some`. The counts are `u8`, like TypeScript's `Int8Array`, since a cell has at most four neighbors, and a layer is a `Vec<(usize, usize)>`.
