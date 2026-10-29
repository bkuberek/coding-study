# Surrounded Regions: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| border-flood | optimal | O(m·n) | O(m·n) | default answer |
| union-find | optimal | O(m·n·α(m·n)) | O(m·n) | the board changes and the safe set must be kept current |

The `'O'` cells form a grid graph; a region is a connected component of it. A component is captured exactly when it contains no edge cell. Rather than testing each component, both approaches identify the safe cells (those connected to some edge `'O'`) and capture everything else.

## Approach: border-flood (Flood fill from the border to find safe cells)

### Intuition

Testing a region for "touches the edge" requires exploring it, and so does capturing it. Turn the question around: the edge `'O'` cells are certainly safe, and so is every `'O'` connected to one. A single flood fill seeded with all edge `'O'` cells marks every safe cell. Whatever `'O'` is left unmarked afterwards is enclosed.

### Algorithm

1. Mark every `'O'` on the edge of the board with a temporary character `'S'` and push it on a stack.
2. While the stack is not empty, pop a cell and mark and push each side neighbor that is still `'O'`.
3. Scan the board: every `'S'` becomes `'O'` again and every remaining `'O'` becomes `'X'`.

### Correctness

After step 2, a cell is `'S'` exactly when it is an `'O'` connected to some edge `'O'`: the fill only moves between side-adjacent `'O'` cells, and it continues until every `'O'` next to a marked cell is marked. A region contains an edge cell exactly when its cells are connected to one, so the `'S'` cells are the union of all regions that touch the edge, and the unmarked `'O'` cells are the union of the enclosed regions. Step 3 restores the first and captures the second.

### Complexity

- Time: O(m·n) — the edge scan, the fill (each cell pushed at most once) and the final scan are each linear in the number of cells.
- Space: O(m·n) — the stack can hold a large share of the cells; the marks live in the board itself.

### Trade-offs

The standard answer: one search, no extra grid, and it never explores an enclosed region at all. It temporarily writes a third character into the board, which is fine because the function owns the board until it returns. A per-region approach (explore each region, then decide) is also linear but must remember every cell of a region until it knows whether to flip it.

### Pitfalls and edge cases

- Seed the fill with every edge `'O'`, including those on the last row and the last column.
- Use a marker that cannot appear in the input; restoring it is part of the algorithm.
- A board of one row or one column has every cell on the edge: nothing is captured.
- Corner contact does not connect regions.

### Language notes

- Python: the initial stack is built with a comprehension, then marked; tuples hold coordinates.
- TypeScript: the board is `string[][]`, so the marker is the one-character string `"S"`; cells on the stack are encoded as numbers.
- Java: `char[][]` uses the char literals `'O'`, `'X'` and `'S'`; `ArrayDeque<int[]>` is the stack.
- Kotlin: `Array<CharArray>`, a private top-level `const val SAFE = 'S'`, and `row.indices` for the final pass.
- Go: a `[]rune` row holds the characters, so the cells compare against rune literals (`'O'`) and the board is changed in place through the slice. The rewrite pass assigns `row[c]` while ranging over `row`, which is safe because it only changes elements, never the length.
- Rust: the signature takes `&mut Vec<Vec<char>>`, so `solve` changes the caller's board directly, and `iter_mut` hands out each cell as a `&mut char`. The edge scan marks cells while it collects them. The flood loop indexes `board[nr][nc]` instead, because the `iter_mut` borrow has ended by then.

## Approach: union-find (Union-find with a virtual border node)

### Intuition

Add one extra, imaginary cell that stands for "the outside" and connect every edge `'O'` to it. Connect side-adjacent `'O'` cells to each other. A cell is safe exactly when it ends up in the same group as the outside node, which a disjoint-set structure answers with one `find` per cell.

### Algorithm

1. Create a disjoint set with one entry per cell plus one entry `edge`.
2. For every `'O'` cell: if it lies on the edge, merge it with `edge`; merge it with the `'O'` to its right and the `'O'` below it.
3. For every `'O'` cell whose group differs from the group of `edge`, write `'X'`.

### Correctness

Every pair of side-adjacent `'O'` cells is merged, so each group of real cells is one region; edge cells are additionally merged with `edge`, so the group of `edge` is exactly the union of the regions that contain an edge cell. Step 3 changes precisely the cells of the other regions, the enclosed ones.

### Complexity

- Time: O(m·n·α(m·n)) — at most three merges per cell and one `find` per cell, each nearly constant with path compression and union by rank.
- Space: O(m·n) — parent and rank arrays with m·n + 1 entries.

### Trade-offs

More code than the flood fill and no faster on a single board. It suits a variant where cells open up over time: each new `'O'` costs a few merges, and its safety is one `find` away. It also never needs a stack.

### Pitfalls and edge cases

- Compare groups with `find(edge)` computed after all merges, not before.
- Merging edge cells with `edge` before or after merging neighbors does not matter, but every edge `'O'` must be merged.
- Only `'O'` cells are ever merged; walls stay in singleton groups and are never changed.

### Language notes

- Python: two lists hold the parents and ranks; `find` compresses paths iteratively.
- TypeScript: a small class over an `Int32Array` of parents and a `Uint8Array` of ranks (ranks stay below 32).
- Java: a private static nested class with `int[]` parents and `byte[]` ranks.
- Kotlin: a private top-level class with `IntArray` and `ByteArray`; `rank[rootA]++` increments a `Byte` in place.
- Go: the disjoint set holds `parent` and `rank` slices with one extra slot for the virtual edge node, and `rootA, rootB = rootB, rootA` swaps the roots.
- Rust: `std::mem::swap` exchanges the roots and `find` takes `&mut self` because it compresses paths. The final pass iterates the board with `iter_mut`, while `set` is a separate value, so asking the set for a root and writing a cell never borrow the same data.
