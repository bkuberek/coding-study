# Max Area of Island: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| dfs | optimal | O(m·n) | O(m·n) | default answer |
| union-find | optimal | O(m·n·α(m·n)) | O(m·n) | land is added over time, or sizes must stay available for later queries |

An island is a connected component of land squares in the grid graph (side-adjacent land squares are linked), and its area is the component's size. Both approaches find every component and its size; one by exploring components one at a time, the other by merging squares into groups and tracking group sizes.

## Approach: dfs (Measure each island with a stack-based flood fill)

### Intuition

Scan the map. Each land square not yet visited is the first square seen of a new island; explore that whole island from it with a stack, counting every square as it comes off the stack. The count at the end of the exploration is the island's area. Keep the largest.

### Algorithm

1. Create a `seen` grid of `false` and set `best = 0`.
2. For every cell in reading order that is land and not seen:
   1. Mark it seen, push it, and set `area = 0`.
   2. While the stack is not empty, pop a cell, add 1 to `area`, and push each side neighbor that is land and not seen, marking it seen.
   3. Set `best = max(best, area)`.
3. Return `best`.

### Correctness

The exploration from a square pushes exactly the land squares of its island: it moves only between side-adjacent land squares and does not stop while an unseen square of the island borders a seen one. Each square is marked when pushed, so it is pushed and popped exactly once, and `area` ends equal to the number of squares of the island. Squares of an explored island are seen, so the scan starts one exploration per island, and `best` is the maximum over all of them.

### Complexity

- Time: O(m·n) — every cell is scanned once, every land square is pushed and popped once, with four neighbor checks per pop.
- Space: O(m·n) — the `seen` grid, plus a stack that can hold a large share of the cells of a big island.

### Trade-offs

The standard answer: a small change to island counting. A recursive flood fill is shorter, but on a 300 by 300 map of land it would nest 90,000 calls; the explicit stack has no such limit. Overwriting land with water instead of keeping `seen` saves memory but destroys the input.

### Pitfalls and edge cases

- Count a square once: either when it is pushed or when it is popped, never both, and mark it when pushing so it cannot be pushed twice.
- A map with no land returns 0, not a negative sentinel.
- Diagonal squares are separate islands.

### Language notes

- Python: a list as the stack and a list of lists for `seen`; tuples hold coordinates.
- TypeScript: cells are encoded as `r * cols + c`, so the stack holds plain numbers and `seen` is one flat `Uint8Array`.
- Java: `ArrayDeque<int[]>` as the stack and `boolean[][]` for `seen`.
- Kotlin: `ArrayDeque<Int>` with encoded cells; `maxOf` keeps the largest area.

## Approach: union-find (Union-find with island sizes)

### Intuition

Treat each land square as a group of size 1 and merge each one with its land neighbors to the right and below. A disjoint-set structure that keeps the size of every group at its root reports the size of the merged group after each merge. The largest size ever reported (or 1, for an isolated square) is the answer.

### Algorithm

1. Number the cells `r * n + c`; every cell starts as its own group of size 1.
2. Set `best = 0`. For every land cell in reading order:
   1. Set `best = max(best, 1)`.
   2. If the cell to the right is land, merge the two groups and update `best` with the merged size.
   3. Do the same with the cell below.
3. Return `best`.

### Correctness

Every pair of side-adjacent land squares is merged once, from its left or upper square, so when the scan ends each group is exactly one island and the size at its root is the island's area. Sizes only grow during the scan, and every group's final size is reported by the merge that completed it (or by step 2.1 for a single square), so the maximum of the reported values equals the largest final group size.

### Complexity

- Time: O(m·n·α(m·n)) — at most two merges per land cell, each nearly constant thanks to path compression and union by size.
- Space: O(m·n) — the parent and size arrays.

### Trade-offs

Same speed in practice and no stack at all. It shines when land appears over time: each new square needs at most four merges, after which the largest island is known at once. For a single static map the flood fill is shorter to write and easier to explain.

### Pitfalls and edge cases

- Report the size of the merged root, not the size of either argument; the arguments are cells, not roots.
- An island of one square is never merged, so `best` must also consider 1 for every land cell.
- Merging two cells that are already in one group must not add sizes again.

### Language notes

- Python: `parent` and `size` are lists, and `find` compresses the path iteratively.
- TypeScript: the disjoint set is a small class over `Int32Array`s; `[rootA, rootB] = [rootB, rootA]` swaps the roots.
- Java: a private static nested class keeps the helper next to `Solution`.
- Kotlin: a private top-level class; `rootA = rootB.also { rootB = rootA }` swaps two variables in one line.
