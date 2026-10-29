# Is the Graph Bipartite: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| bfs-coloring | optimal | O(V + E) | O(V) | default answer; also yields the two teams or an odd cycle |
| union-find | optimal | O((V + E)·α(V)) | O(V) | you already have a disjoint-set structure at hand |

A graph is bipartite exactly when it has no cycle of odd length. Both approaches check this without listing cycles: the first assigns teams and looks for an edge inside a team, the second groups nodes that are forced into the same team and looks for an edge inside a group.

## Approach: bfs-coloring (Two-color each component breadth-first)

### Intuition

Within one piece of the graph, the team of a single node decides everything: its neighbors must be in the other team, their neighbors in the first team, and so on. Spread the two colors with a breadth-first search. If the search ever finds an edge whose two ends already have the same color, no split exists. Pieces are independent, so start a fresh search in every piece that is still uncolored.

### Algorithm

1. Set every node's color to "uncolored".
2. For every node `s` that is uncolored: color it 0 and put it in a queue. While the queue is not empty, take a node `u`; for each neighbor `v`:
   1. If `v` is uncolored, give it the color `1 - color(u)` and enqueue it.
   2. Otherwise, if `color(v) == color(u)`, return `false`.
3. Return `true`.

### Correctness

If the algorithm returns `true`, every edge was examined from at least one end after both ends were colored, and no edge joined two equal colors, so the colors are a valid split. If it returns `false`, it found an edge `u`–`v` of equal colors inside one search tree. In a breadth-first tree, a node's color is the parity of its depth, so `u` and `v` have depths of equal parity; the tree paths from `u` and `v` up to their lowest common ancestor, plus the edge `u`–`v`, form a closed walk of odd length, which contains an odd cycle. A graph with an odd cycle has no valid split, because colors must alternate along the cycle.

### Complexity

- Time: O(V + E) — every node is enqueued once and every adjacency entry is read once.
- Space: O(V) — the color array and the queue.

### Trade-offs

The standard answer, linear, and it produces useful by-products: the colors are the two teams, and the conflicting edge plus the tree paths is an odd cycle that proves the answer `false`. A depth-first search works just as well; breadth-first avoids recursion depth issues on long paths.

### Pitfalls and edge cases

- The graph may be disconnected: a search from node 0 alone misses odd cycles in other pieces.
- Isolated nodes (empty adjacency lists) are fine in either team.
- Check conflicts on every edge, not only on edges to uncolored nodes.

### Language notes

- Python: `collections.deque` for the queue and a list of colors with `-1` for uncolored.
- TypeScript: an `Int8Array` filled with -1 stores the colors; the queue is an array with a moving head index.
- Java: `ArrayDeque<Integer>` boxes the node numbers; with at most 10^4 nodes that cost is negligible.
- Kotlin: `when (color[neighbor])` with the branch `color[node] -> return false` compares against a runtime value, which Kotlin allows in `when` branches.
- Go: a slice serves as the queue (`queue[1:]` pops the front), and `color` is filled with the `uncolored` sentinel because `make` zeroes it, which would read as color 0.
- Rust: the colors are `Vec<Option<bool>>`, so "not colored yet" is `None` instead of a sentinel number and the compiler forces every read to say what happens when a node is uncolored. Neighbors arrive as `i32` and are cast to `usize` for indexing. The match arm `shade if shade == node_color` catches a same-color neighbor before the `Some(_)` arm accepts a differently colored one.

## Approach: union-find (Merge each node's neighbors into one group)

### Intuition

In a valid split, all neighbors of a node `u` are in the same team, the one `u` is not in. So merge all neighbors of every node into one group with a disjoint-set structure: every group then holds nodes that are forced into the same team. A split exists exactly when no edge ends up inside a group.

### Algorithm

1. Create a disjoint set with one group per node.
2. For every node `u`, merge each neighbor of `u` with the first neighbor of `u`.
3. For every node `u` and every neighbor `v` of `u`, if `find(u) == find(v)`, return `false`.
4. Return `true`.

### Correctness

If a split exists, both nodes of every merge are neighbors of the same node, so they are in the same team; by induction every group lies inside one team. An edge joins the two teams, so its ends are never in one group, and the algorithm returns `true`. If no split exists, the graph has an odd cycle `c0, c1, ..., c2k` (with `c2k` linked back to `c0`). For each `i`, the nodes `c(i)` and `c(i+2)` are both neighbors of `c(i+1)`, so step 2 put them in one group; following the even positions, `c0, c2, ..., c2k` all share one group. But `c2k` and `c0` are joined by an edge, so step 3 finds that edge inside a group and returns `false`.

### Complexity

- Time: O((V + E)·α(V)) — one `union` per adjacency entry in step 2 and two `find` calls per entry in step 3, each nearly constant with path compression and union by size.
- Space: O(V) — the parent and size arrays.

### Trade-offs

Same asymptotic speed as the coloring and no queue, but it needs two passes and does not produce the teams or an odd cycle directly, and its correctness argument is less obvious; in an interview it is the second answer, not the first. Its relative, a union-find that also stores each node's parity with respect to its root, checks edges that arrive one at a time in near-constant time each.

### Pitfalls and edge cases

- Merge the neighbors of a node with each other, never the node with its neighbor; that would put both ends of an edge in one group.
- Do every merge before any check: an edge checked too early can look fine and only end up inside a group after later merges.
- Nodes with no neighbors are never merged, which is correct: they fit in either team.

### Language notes

- Python: parent and size lists with iterative path compression; the final check is one `all(...)` over every adjacency entry.
- TypeScript: a small class over `Int32Array`s; the check is `graph.every(...)` with a nested `every`, which stops at the first conflict.
- Java: a private static nested class with `int[]` arrays; the enhanced `for` over `int[]` avoids boxing.
- Kotlin: `graph.withIndex().all { (node, neighbors) -> ... }` destructures each node with its neighbor array; the disjoint set is a private top-level class.
- Go: `for i := 1; i < len(neighbors); i++` skips the first neighbor without slicing, since `neighbors[1:]` panics on an empty list and a node may have no neighbors.
- Rust: `neighbors.iter().skip(1)` is the safe form of Python's `neighbors[1:]` and yields nothing for an empty list, and `neighbors[0]` is only evaluated inside the loop body, so a node without neighbors never reads it.
