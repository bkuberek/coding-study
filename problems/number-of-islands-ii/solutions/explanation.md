# Number of Islands II: Explanation

## Overview

The grid has m * n cells and there are k operations. Counting islands from scratch after every operation repeats almost all of its work; the incremental view is that a new land cell adds one island and each merge with a different neighboring island removes one. Union-find answers "different island?" quickly. α is the inverse Ackermann function, at most 4 in practice.

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| recount | brute | O(m * n + k^2) | O(m * n) | a direct check, or a handful of operations |
| quick-union | intermediate | O(m * n + k^2) | O(m * n) | to see how naive linking degrades |
| union-find | optimal | O(m * n + k * α(m * n)) | O(m * n) | default answer |

## Approach: recount (Recount every island with a search after each operation)

### Intuition

Apply each operation to the grid, then count islands the way the classic Number of Islands problem does: every land cell not yet reached by a search starts a new island, and a search from it marks the whole island.

### Algorithm

1. Keep a land grid and a list of the distinct land cells.
2. For each operation, mark the cell as land (adding it to the list only if it was water).
3. Count islands: for each land cell not seen in this round, count one island and run a depth-first search through land neighbors, marking them seen.
4. Record the count.

### Correctness

Each search marks exactly one island, because it follows every land-to-land edge from every cell it reaches and never crosses water. A cell starts a search only if no earlier search of the round reached it, so every island is counted exactly once. Repeated operations leave the grid unchanged, and the recount reports the same number again.

### Complexity

- Time: O(m * n + k^2) — the grid costs O(m * n) to create; each recount visits every land cell and its four neighbors once, and there are at most k land cells, so k recounts cost O(k^2).
- Space: O(m * n) — the land grid; the seen marks and the cell list add at most O(m * n).

### Trade-offs

Obviously correct, which makes it the oracle, but it throws away everything it learned at each step, although one operation can only merge the at most four islands around one cell. The union-find approaches keep the islands between operations.

### Pitfalls and edge cases

- A repeated cell must not be added to the land list twice.
- Only the four side neighbors connect; diagonal cells form separate islands.

### Language notes

- Python: a set of `(row, col)` tuples marks the cells seen in one recount.
- TypeScript: cells are encoded as `r * n + c` so that a `Set<number>` can mark them.
- Java: an `int[]` of round numbers marks seen cells without reallocating an array per operation: a cell counts as seen when its entry equals the current round.
- Kotlin: the same round-stamping `IntArray`, and `IntArray(positions.size) { ... }` builds the answer one operation at a time.
- Go: the `seen` set keys on `[2]int`, because arrays of comparable elements are comparable and so usable as map keys, which stands in for Python's tuples. `countIslands` is a closure over `land` and `cells`, so it always sees the cells added so far.
- Rust: `HashSet<(usize, usize)>` takes tuple keys directly, and `seen.insert((nr, nc))` returns `false` for a cell already seen, so one call both tests and marks. The helper borrows `land` and `cells` as slices because it only reads them.

## Approach: quick-union (Naive union-find that links roots without balancing or compression)

### Intuition

Give every cell a union-find element and keep the island count as you go. Raising a water cell adds one island. Then look at its four neighbors: each land neighbor whose root differs from the new cell's root belongs to another island, so merge the two and subtract one. Raising a cell that is already land changes nothing.

### Algorithm

1. `parent[x] = x` for every cell `x = r * n + c`; no cell is land; `islands = 0`.
2. For each operation on cell `x`: if it is water, make it land and increment `islands`; for each land neighbor, if its root differs from `x`'s root, link the neighbor's root under `x`'s root and decrement `islands`.
3. Record `islands` after every operation.

### Correctness

Invariant: after each operation, two land cells share a root exactly when they are on the same island, and `islands` is the number of distinct roots among land cells. A new cell is a new root, one island more. An island touching the new cell now forms one island with it, and the root comparison merges each touching island exactly once, because after the first merge the next neighbor from the same island already shares the new cell's root. Water cells never take part in a union.

### Complexity

- Time: O(m * n + k^2) — initialization is O(m * n); without balancing, a tree can be a chain through all land cells, so each find costs up to O(k). The generated combs build exactly that: raising a long row cell by cell links each old root under the new cell, and every tooth below the row starts a find deep inside the chain.
- Space: O(m * n) — the parent and land arrays.

### Trade-offs

The incremental count is the right idea; only the tree shapes are left to chance. On adversarial orders like the comb, the finds cost as much as the recount does.

### Pitfalls and edge cases

- Compare roots, not cells, and compare against the new cell's current root after each merge.
- Skip cells that are already land; processing them again adds a phantom island.

### Language notes

- Python: the grid is flattened to one index per cell, which keeps the parent array a plain list.
- TypeScript: `positions.map` returns the running count for each operation.
- Java: a static `find(parent, x)` helper walks to the root iteratively.
- Kotlin: `val (r, c) = positions[i]` destructures the operation.
- Go: the grid is flattened to `r*n + c`, and `find` is a closure that climbs by reassigning its own parameter. There is no compression, so `parent` chains can grow as long as the cell count.
- Rust: `find` takes `&[usize]` because it never changes `parent`, which is what lets both roots be looked up in one tuple expression before `parent[root_neighbor]` is written. Coordinates are `usize`, so `checked_add_signed` rejects a step off the top or left edge.

## Approach: union-find (Union by size with path compression over the cells)

### Intuition

The same incremental algorithm on a balanced, compressed union-find. Union by size keeps every tree at most log2 of its size deep, and path compression flattens each path a find walks, so every operation costs amortized O(α(m * n)).

### Algorithm

1. `parent[x] = x`, `size[x] = 1` for every cell; `islands = 0`.
2. For each operation on a water cell: make it land, increment `islands`, and for each land neighbor decrement `islands` if `union(neighbor, cell)` merged two different sets (it attaches the smaller root under the larger).
3. Record `islands` after every operation, including repeated cells.

### Correctness

Union by size and path compression change only the tree shapes, not which cells share a root, so the invariant and the argument of the naive version hold unchanged.

### Complexity

- Time: O(m * n + k * α(m * n)) — the arrays cost O(m * n) to create; each operation does at most four unions, eight finds, which Tarjan's analysis bounds by O(α(m * n)) amortized each.
- Space: O(m * n) — parent, size and land arrays, one entry per cell.

### Trade-offs

Each operation costs effectively constant time after the one-time grid setup, which is what makes this the standard dynamic-connectivity answer. When the grid is huge and sparse (m * n far larger than k), a hash map from cell to parent avoids allocating the whole grid, at the cost of slower lookups.

### Pitfalls and edge cases

- Decrement the count only when a union actually merges two different sets.
- Repeated cells still produce an output entry, equal to the previous one.
- Encode cells as `r * n + c` with the column count `n`, not the row count.

### Language notes

- Python: `parent[x], x = root, parent[x]` compresses the path in one tuple assignment.
- TypeScript: `DisjointSets` sets its arrays in the constructor body, with no parameter properties; `union` returns whether it merged, which drives the count.
- Java: a `private static final` nested class over two `int[]` arrays.
- Kotlin: `rootA = rootB.also { rootB = rootA }` swaps the roots before attaching the smaller one.
- Go: `union` returns whether two groups merged, and `&&` short-circuits so it runs only for a land neighbor; each successful merge lowers `islands` by one, exactly as in the Python version.
- Rust: `union` returns a `bool` and takes `&mut self`; the condition `land[nr * n + nc] && set.union(nr * n + nc, cell)` runs the merge only for a land neighbor. The `DisjointSet` struct keeps `parent` and `size` together, and `std::mem::swap` exchanges the roots for union by size.
