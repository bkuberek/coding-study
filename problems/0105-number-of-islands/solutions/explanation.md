# Number of Islands: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| dfs | optimal | O(m·n) | O(m·n) | default answer; shortest to write |
| bfs | optimal | O(m·n) | O(m·n) | the grid must stay unchanged, or you also need distances later |
| union-find | optimal | O(m·n·α(m·n)) | O(m·n) | land arrives over time and the count must be kept up to date |

The map is a graph: every land square is a vertex, and two vertices share an edge when the squares are side by side. An island is a connected component, so the task is to count components. Each approach touches every cell a constant number of times; they differ in how they discover a component (a stack, a queue, or merges).

## Approach: dfs (Flood fill with an explicit stack)

### Intuition

Scan the map in reading order. The first land square of an island that the scan meets is the moment to count that island; then erase the whole island, so none of its other squares can be counted later. Erasing is a flood fill: from the first square, keep visiting land neighbors until none are left.

### Algorithm

1. Set `islands = 0`.
2. For every cell `(r, c)` in reading order, if it holds `'1'`:
   1. Add 1 to `islands`.
   2. Overwrite it with `'0'` and push it on a stack.
   3. While the stack is not empty, pop a cell and, for each of its four neighbors inside the map that holds `'1'`, overwrite the neighbor with `'0'` and push it.
3. Return `islands`.

### Correctness

The flood fill started at a land square sinks exactly the squares of its island: it only ever steps between side-adjacent land squares, so it never leaves the island, and every square of the island is reachable by such steps, so it is eventually pushed. Squares are overwritten at the moment they are pushed, so each is pushed once. After the fill, the island has no land left, so the scan finds land again only in an island it has not counted. Each island is therefore counted exactly once, at its first square in reading order.

### Complexity

- Time: O(m·n) — the scan reads every cell once, and each land square is pushed and popped once, with four neighbor checks per pop.
- Space: O(m·n) — on a map that is all land the stack can hold a large share of all cells at once; nothing else is allocated.

### Trade-offs

The shortest correct answer and the usual interview answer. It writes into `grid`, which is fine here but not when the caller needs the map afterwards; then use a separate `visited` array (as `bfs` does) at the cost of one bit or byte per cell. The explicit stack is what makes it safe on big maps: a recursive flood fill is shorter to write but needs one call frame per square on a long winding island.

### Pitfalls and edge cases

- Mark a square when you push it, not when you pop it. Marking on pop lets the same square enter the stack several times, which wastes time and, with a counter of squares, gives wrong sizes.
- Check bounds before reading a neighbor; the four steps go off the map on the border.
- Diagonal neighbors do not count: only four steps, not eight.
- Recursion: 300 by 300 of solid land would mean up to 90,000 nested calls, far beyond Node's default stack and Python's default recursion limit.

### Language notes

- Python: a list used as a stack (`append` and `pop`) is the idiom; tuples hold the coordinates.
- TypeScript: the stack holds one number per cell (`r * cols + c`) instead of an array per cell, which avoids allocating a small array for every push. `grid` is `string[][]`, so the comparison is with the one-character string `"1"`.
- Java: `char[][]` compares with the char literal `'1'`. `ArrayDeque` is the recommended stack (`push`, `pop`); the legacy `Stack` class is synchronized and slower.
- Kotlin: `Array<CharArray>` with char literals; `kotlin.collections.ArrayDeque` with `addLast` and `removeLast` serves as the stack, and `nr in 0 until rows` reads as a bounds check.
- Go: a slice of `[2]int` coordinates is the stack: `stack[len(stack)-1]` reads the top, `stack[:len(stack)-1]` pops it and `append` pushes. A `[2]int` is a small value type, so a push allocates nothing beyond the slice's growth. The grid is `[][]rune`, compared with the rune literal `'1'`, and the function sinks the input grid in place, as the Python version does.
- Rust: a `Vec<(usize, usize)>` is the stack (`pop`, `push`), and the function owns the grid (`mut grid`), so sinking cells needs no copy. A step off the grid is caught by a small `neighbor` helper using `checked_add_signed`, which returns `None` for a negative coordinate instead of wrapping.

## Approach: bfs (Flood fill with a queue)

### Intuition

Same scan and same "count, then erase the island" idea, but the island is explored in rings around its first square, with a queue. Instead of overwriting the map, a separate `visited` grid records which land squares were already reached, so the input stays as it was.

### Algorithm

1. Create a `visited` grid of `false` and set `islands = 0`.
2. For every cell `(r, c)` in reading order that is land and not visited:
   1. Add 1 to `islands`, mark `(r, c)` visited and put it in a queue.
   2. While the queue is not empty, take the front cell; for each of its four neighbors inside the map that is land and not visited, mark it visited and append it.
3. Return `islands`.

### Correctness

The breadth-first search from a square reaches exactly the land squares connected to it, for the same reason as the depth-first fill: it moves only along side-adjacent land, and it does not stop while some connected land square is unvisited. `visited` plays the role of sinking, so the scan starts a new search only from a square of an island not yet counted.

### Complexity

- Time: O(m·n) — every cell is scanned once; every land square enters and leaves the queue once.
- Space: O(m·n) — the `visited` grid has one entry per cell, and the queue can hold many cells of a large island at once.

### Trade-offs

Same speed as `dfs`, and it leaves `grid` untouched. The order of visits does not matter for counting, but breadth-first order gives each square its distance from the start square for free, which is what the next problems in this pattern (rotting oranges, shortest paths) build on. The extra `visited` grid is the price.

### Pitfalls and edge cases

- Use a real queue: `list.pop(0)` in Python or `Array.shift()` in TypeScript is O(length) per call and turns a large island into quadratic work.
- Mark visited when enqueuing, not when dequeuing, or the same square is enqueued once per land neighbor.
- A map of a single cell is valid input: one row and one column.

### Language notes

- Python: `collections.deque` gives O(1) `popleft`.
- TypeScript: there is no built-in queue. The reference preallocates an `Int32Array` of size `m·n` and moves a head index forward, because every cell is enqueued at most once over the whole run; `visited` is a `Uint8Array`.
- Java: `ArrayDeque` as a `Queue` (`add`, `poll`) and a `boolean[][]` for `visited`.
- Kotlin: `ArrayDeque<Int>` with `addLast` and `removeFirst`; `Array(rows) { BooleanArray(cols) }` builds independent rows.
- Go: a slice is the queue: `queue[0]` reads the front, `queue = queue[1:]` pops it in O(1) and `append` pushes at the back. `make([][]bool, rows)` creates only the outer slice, so each row of `visited` gets its own `make([]bool, cols)`.
- Rust: `VecDeque` is the queue (`pop_front`, `push_back`), seeded with `VecDeque::from([(row, col)])`. `vec![vec![false; cols]; rows]` clones the inner vector once per row, so the rows are independent.

## Approach: union-find (Union-find over land squares)

### Intuition

Start by treating every land square as an island of its own. Two side-by-side land squares are on the same island, so merge their groups; a merge that joins two different groups reduces the island count by one, and a merge of two squares already in the same group changes nothing. A disjoint-set structure performs the merges and answers "same group?" in near-constant time.

### Algorithm

1. Number the cells `r * n + c` and create a disjoint set with one group per cell.
2. Set `islands = 0`. For every land cell in reading order:
   1. Add 1 to `islands`.
   2. If the cell to the right is land and `union` joins two different groups, subtract 1.
   3. Do the same with the cell below.
3. Return `islands`.

### Correctness

After all merges, two land squares are in the same group exactly when a chain of side-adjacent land squares links them, because every edge of the grid graph was offered to `union` once (each pair is seen from its left or upper square) and union-find groups are the connected components of the edges offered. The counter starts at the number of land squares and drops by one per merge of two distinct groups, so it ends at the number of groups that contain land, which is the number of islands. Water cells are never merged, so their singleton groups are not counted.

### Complexity

- Time: O(m·n·α(m·n)) — two `union` calls per land cell, each nearly constant with path compression and union by size; α is the inverse Ackermann function, at most 4 for any real input.
- Space: O(m·n) — the parent and size arrays have one entry per cell.

### Trade-offs

A little more code and a little more memory than the flood fills for the same answer on a static map. Its strength is incremental updates: if land is added one square at a time (the follow-up), each addition costs a few `union` calls instead of a new flood fill, and the count stays current. It also never recurses and never needs a stack or queue.

### Pitfalls and edge cases

- Count only successful unions; `union` on two squares already in one group must not decrease the count.
- Without path compression and union by size, chains can grow long and `find` becomes linear.
- Offer each edge once (right and down) or count carefully; offering both directions is still correct here because the second offer finds the same group.

### Language notes

- Python: the disjoint set is two lists and two nested functions; `parent[cell], cell = root, parent[cell]` compresses the path iteratively, with no recursion.
- TypeScript: a small class over `Int32Array`s, since there is no library disjoint set.
- Java: a private static nested class with `int[]` arrays keeps the helper out of the public API.
- Kotlin: a private top-level class next to `Solution`; `rootA = rootB.also { rootB = rootA }` swaps the two roots.
- Go: `find` and `union` are closures over the two slices. `parent[cell], cell = root, parent[cell]` is a safe one-line path compression: Go evaluates the index on the left and the right-hand sides first, and then assigns, so it writes `parent` at the old `cell` before `cell` moves on. Tuple swaps like `rootA, rootB = rootB, rootA` need no temporary.
- Rust: a small `DisjointSet` struct owns `parent` and `size` so that `find` and `union` can borrow `self` mutably, which closures over two vectors could not do both at once. Path compression reads the next link before overwriting it (`let next = self.parent[cell]`), and `std::mem::swap` swaps the two roots.
