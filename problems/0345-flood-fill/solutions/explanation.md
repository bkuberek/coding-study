# Flood Fill: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| dfs | optimal | O(m·n) | O(m·n) | the grid is small and you want the shortest code |
| bfs | optimal | O(m·n) | O(m·n) | the region can be huge, or you will need distances from the start next |

A grid is a graph in disguise: every tile is a vertex, and two tiles share an edge when they are neighbours (above, below, left or right) and have the same colour. The region to repaint is the connected component of the starting tile, so the task is to visit every vertex of one component. Both approaches visit each tile of the region once; they differ in the order, and so in the data structure that remembers what is left to visit. Neither one builds an explicit graph: the neighbours of a tile are computed from its row and column.

## Approach: dfs (Recursive depth-first fill)

### Intuition

Repaint the starting tile, then hand the same job to each of its four neighbours: "if you still have the original colour, repaint yourself and hand the job on". The calls go as far as they can in one direction before they come back and try the next one, which is what depth-first means. The repainting does a second job for free: a repainted tile no longer has the original colour, so it will refuse any later request, and the fill cannot loop.

### Algorithm

1. Read the original colour `old = grid[row][col]`. If `old` equals `newColor`, return the grid unchanged.
2. Define `paint(r, c)`:
   1. If `(r, c)` is outside the grid, or `grid[r][c] != old`, return.
   2. Set `grid[r][c] = newColor`.
   3. Call `paint` on the tile below, above, to the right and to the left.
3. Call `paint(row, col)` and return the grid.

### Correctness

`paint` only continues from a tile it has just repainted, and it only moves to neighbours, so every tile it repaints is joined to the start through tiles of the original colour: nothing outside the region is touched. Conversely, take any tile of the region and a path of neighbours from the start to it. The first tile of the path is repainted. If a tile on the path is repainted, its call asks the next tile of the path, which has the original colour and is inside the grid, unless a call already repainted it. Either way the next tile ends up repainted, so by induction along the path the whole region is. A tile is repainted at most once, because the repaint is what makes later calls on it return at once. That also shows the fill stops, but only under the guard of step 1: if the new colour equalled the old one, a repainted tile would still look like part of the region and the calls would never end.

### Complexity

- Time: O(m·n) — each tile is repainted once, and each repainted tile makes four calls that do constant work, so there are at most about 5·m·n calls.
- Space: O(m·n) — the calls that are still waiting form a stack, and on a snaking region it can hold close to every tile at once.

### Trade-offs

The shortest correct answer and the easiest to read. Its limit is the call stack: the depth reached is as large as the longest chain of unfinished calls, which on a winding region is about the size of the region. The grader runs your code with a raised stack limit and the grids here are at most 50 by 50, so recursion is safe; with a grid of a million tiles it would not be, and `bfs` (or a depth-first fill with an explicit stack of positions) is the answer.

### Pitfalls and edge cases

- Compare the new colour with the original before painting anything. If they are equal, return at once.
- Save the original colour in a variable first. Reading `grid[row][col]` after the first repaint gives the new colour.
- Check the bounds before reading `grid[r][c]`, in that order: the four calls step off the grid at its edges.
- Diagonal tiles are not neighbours: four directions, not eight.
- A region of one tile (every neighbour is another colour, or the grid is a single tile) must still be repainted.

### Language notes

- Python: a nested function reads `grid`, `old_color` and the sizes from the enclosing scope instead of passing them on every call. The grader raises Python's recursion limit; in a script of your own, a long region would stop with `RecursionError` at the interpreter's default limit.
- TypeScript: `paint` is an arrow function that closes over `grid`, `oldColor` and `newColor`, and the grader keeps the depth under what Node's default stack allows.
- Java: a private method takes the grid and both colours as parameters, because Java has no nested functions; arrays are passed by reference, so every call repaints the same grid.
- Kotlin: `r !in grid.indices` is the bounds check; a private member function plays the part of the nested function.
- Go: a closure assigned to a variable declared with `var paint func(r, c int)` can call itself; the declaration must come first, because the closure refers to its own name. Go's stack grows on demand.
- Rust: coordinates travel as `i32` through the helper so that a step to row `-1` is a plain negative number that the first check rejects; they are converted to `usize` only after that check. The grid is passed as `&mut [Vec<i32>]`, a mutable borrow that every recursive call reuses.

## Approach: bfs (Breadth-first fill with a queue)

### Intuition

Instead of letting calls pile up, keep a queue of tiles that were repainted but whose neighbours have not been looked at yet. Take a tile from the front, look at its four neighbours, repaint and queue the ones that belong to the region. The fill grows in rings: first the start, then its neighbours, then theirs. A tile is repainted at the moment it is queued, so it is queued only once.

### Algorithm

1. Read `old = grid[row][col]`. If it equals `newColor`, return the grid unchanged.
2. Repaint `(row, col)` and put it in an empty queue.
3. While the queue is not empty: remove the tile at the front, and for each of its four neighbours inside the grid whose colour is `old`, repaint it and add it to the back of the queue.
4. Return the grid.

### Correctness

Every tile that enters the queue has just been repainted and was reached from a tile already in the region by one neighbour step, so the queue only ever holds region tiles. Suppose some tile of the region were never repainted, and take one at the shortest path distance from the start among those. The previous tile on its path is closer, so it was repainted and queued, and it was taken from the queue at some point; at that moment this tile was a neighbour of it, inside the grid, with the original colour, which is exactly the condition that repaints and queues it. That is a contradiction. The loop ends because each tile enters the queue at most once.

### Complexity

- Time: O(m·n) — each tile is queued and removed at most once, with four constant-time neighbour checks per removal.
- Space: O(m·n) — the queue holds the tiles waiting to be processed, and on a branching region that can be a sizeable share of all tiles at once.

### Trade-offs

Same running time as `dfs` and no call stack to run out of: the queue lives in ordinary memory, so it works on any grid that fits in memory. It is a few lines longer. Visiting the tiles in rings has a bonus that the recursive version lacks: the moment a tile is queued, its distance to the start is one more than the tile that queued it, so with a small change the same loop answers "how many steps from the start" questions. That is the next step in the graph problems that follow this one.

### Pitfalls and edge cases

- Repaint when you queue a tile, not when you take it out. If the repaint waits until removal, a tile with two region neighbours is queued twice, and in a big region the queue grows far beyond the number of tiles.
- Use a real queue. Removing from the front of a plain array or list shifts every other element and turns the fill into quadratic work.
- The same-colour guard matters here too: without it, the first neighbour check would find the tile you just repainted, and the queue never empties.

### Language notes

- Python: `collections.deque` removes from the left end in constant time with `popleft`.
- TypeScript: there is no built-in queue, and `Array.shift()` is linear. The reference preallocates an `Int32Array` for the whole grid and moves a `head` index forward, which is enough because each tile is queued at most once; a tile is stored as `r * cols + c`.
- Java: `ArrayDeque` used as a `Queue` (`add` and `poll`); each tile is an `int[]` of two numbers.
- Kotlin: `ArrayDeque<Pair<Int, Int>>` from the standard library, with `addLast` and `removeFirst`; destructuring `val (r, c) = ...` unpacks a pair.
- Go: a slice is the queue: `queue[0]` is the front, `queue = queue[1:]` drops it, and `append` adds at the back.
- Rust: `VecDeque` with `push_back` and `pop_front`, seeded with `VecDeque::from([(row, col)])`. A small `neighbor` helper uses `checked_add_signed`, which returns `None` for a step below zero instead of wrapping around, then compares the other end with the grid size.
