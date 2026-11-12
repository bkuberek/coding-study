# Path Exists in a Graph: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| edge-scan | brute | O(V * E) | O(V) | only as the baseline that shows why an adjacency list helps |
| bfs | optimal | O(V + E) | O(V + E) | default answer; you may also want the number of trails on the way |
| union-find | optimal | O(V + E * α(V)) | O(V) | many "are these two connected" questions, or edges that keep arriving |

A graph is a set of nodes and a set of edges between them. Here the edges have no direction, so a path can use a trail either way. "Is there a path from `source` to `target`?" asks whether the two nodes lie in the same connected component, the set of nodes that can all reach each other. The approaches differ in how they find that out: by repeating a sweep over the edge list, by walking outward from `source`, or by merging nodes into groups.

## Approach: edge-scan (Sweep the connection list until nothing new is reached)

### Intuition

Keep a set of nodes known to be reachable from `source`; at first it is just `source`. Go through the edge list: whenever an edge has one end reached and the other end not, the other end is reachable too. One sweep may not be enough, because an edge near the front of the list may only become useful after a later edge has reached one of its ends. So sweep again, and stop when a whole sweep adds nothing, or as soon as `target` is reached.

### Algorithm

1. Create `reached`, one flag per node, all false, and set `reached[source] = true`.
2. Repeat while the last sweep changed something and `target` is not reached:
   1. For every edge `[a, b]`: if exactly one of `reached[a]` and `reached[b]` is true, set both to true and note that something changed.
3. Return `reached[target]`.

### Correctness

Only nodes joined by a chain of edges to `source` are ever flagged: an edge flags a node only when its other end is already flagged, and `source` is flagged to begin with. Conversely, suppose a path `source = v0, v1, ..., vk = target` exists. Each sweep that has not yet flagged all of the path flags at least the first unflagged `vi` of it, because the edge `[v(i-1), vi]` has exactly one flagged end and a sweep visits every edge. So the sweeps do not stop before `vk` is flagged, and there are at most `k + 1` of them. A sweep that changes nothing means no edge leaves the flagged set, so no path to an unflagged node exists.

### Complexity

- Time: O(V * E) — each sweep reads all E edges, and the number of sweeps is at most one per newly reached node, so at most V.
- Space: O(V) — one flag per node.

### Trade-offs

Almost no code and no data structure beyond an array, which makes it a good first draft and a good test oracle. It is slow because every sweep rereads edges that cannot matter yet. The cost depends on the order of the list: with the edges of a chain listed from the far end, each sweep reaches only one new node, which is the worst case. The adjacency list of the next approach removes the rereading: from a node you look only at the edges that start there.

### Pitfalls and edge cases

- `source == target` is a valid input and the answer is `true` even when the node has no trails.
- Test both ends of each edge: an edge `[a, b]` can bring in `a` through `b` as well as `b` through `a`.
- Without the "changed" flag, the loop never ends when `target` cannot be reached.
- With `n = 1` the edge list is empty, and the only valid query is a node to itself.

### Language notes

- Python: `reached[a] = reached[b] = True` assigns both flags in one statement.
- Kotlin: `for ((a, b) in edges)` unpacks an `IntArray` of two elements.
- Go: `for changed := true; changed && !reached[target]; { ... }` is Go's way to write a `while` loop, and the loop assigns `changed = false` itself at the top of each sweep.
- Rust: the node numbers arrive as `i32`, so the function converts them with `as usize` once before indexing, and borrows the edge list with `for edge in &edges`.

## Approach: bfs (Adjacency list and a breadth-first search)

### Intuition

Give every node a list of the nodes it shares a trail with: its adjacency list. Building the lists takes one pass over the trails: for each trail `[a, b]`, add `b` to the list of `a` and `a` to the list of `b`, because the trail works both ways. Then walk outward from `source`: visit the nodes next to it, then the nodes next to those, and so on, never visiting a node twice. If `target` is ever visited there is a path; if the walk runs out of new nodes first, there is none.

### Algorithm

1. Create `n` empty lists. For every edge `[a, b]`, append `b` to the list of `a` and `a` to the list of `b`.
2. Mark `source` as visited and put it in a queue.
3. While the queue is not empty: remove the node at the front; if it is `target`, return `true`; otherwise, for each node in its list that is not visited, mark it visited and add it to the back of the queue.
4. Return `false`.

### Correctness

A node is added to the queue only as a neighbour of a node taken from the queue, so every queued node is joined to `source` by a chain of trails, and returning `true` is right. If a path `source = v0, ..., vk = target` exists, then by induction every `vi` is queued: `v0` is, and when `v(i-1)` is taken from the queue, `vi` is in its list, so it is either already visited (hence queued earlier) or gets queued now. The loop ends because each node is queued at most once. When the queue empties without a `true`, `target` was never visited, and the argument just made shows no path exists.

### Complexity

- Time: O(V + E) — building the lists reads each edge once and adds two entries; the search takes each node out of the queue once and reads its list once, and the lists hold 2E entries in all.
- Space: O(V + E) — the adjacency lists hold 2E entries over V lists, plus a visited flag per node and a queue of up to V nodes.

### Trade-offs

The usual answer. It is linear and easy to explain. A depth-first search (an explicit stack instead of the queue, or a recursive function) has the same cost and the same structure; the difference is only the order of visits. Breadth-first has the extra property that it reaches nodes in order of the number of trails from `source`, which is what you need when a later problem asks for the shortest route. Compared with `union-find` it answers a single question per run; for many questions on the same trails, build the structure once.

### Pitfalls and edge cases

- Add the edge to both lists. Adding it to one gives a graph in which trails can only be walked one way, and `[3, 2]` could not be used to go from 2 to 3.
- Mark a node visited when it is added to the queue, not when it is removed. Otherwise a node reachable from several visited nodes is queued several times.
- Create the lists for all `n` nodes, including those that appear in no edge: `source` and `target` may be such nodes.
- A queue implemented as a list from which you remove the first element (`list.pop(0)` in Python, `Array.shift()` in JavaScript) takes time proportional to its length per removal.

### Language notes

- Python: `[[] for _ in range(n)]` creates `n` independent lists; `[[]] * n` would create `n` references to one list. `collections.deque` gives `popleft` in constant time.
- TypeScript: `Array.from({ length: n }, () => [])` builds independent arrays. The queue is an array with a moving `head` index, so nothing is removed from the front.
- Java: `List<List<Integer>>` is filled with an `ArrayList` per node; the neighbour loop `for (int neighbor : neighbors.get(node))` unboxes each `Integer`. `ArrayDeque` is the queue.
- Kotlin: `Array(n) { mutableListOf<Int>() }` runs the block once per element, giving independent lists; `ArrayDeque<Int>` with `addLast` and `removeFirst` is the queue.
- Go: `make([][]int, n)` makes `n` nil slices, and `append` on a nil slice is fine, so no per-node setup is needed; the queue is a slice, with `queue = queue[1:]` to drop the front.
- Rust: `vec![Vec::new(); count]` clones the empty vector `count` times, which gives independent lists. `VecDeque` is the queue.

## Approach: union-find (Merge the two ends of every connection)

### Intuition

Start with every node in a group of its own. Reading a trail `[a, b]` means a and b can reach each other, so merge their groups. When all trails have been read, two nodes are in the same group exactly when a path connects them, so the answer is whether `source` and `target` share a group. A disjoint-set structure (also called union-find) stores each group as a tree whose root names the group: `find(x)` walks up to the root, and `union(a, b)` hangs one root under the other.

### Algorithm

1. Create a parent array with `parent[i] = i` and a size array of ones.
2. For every edge `[a, b]`: find the roots of `a` and `b`; if they differ, hang the root of the smaller tree under the root of the larger and add the sizes.
3. Return whether `find(source) == find(target)`.

### Correctness

Merging only ever joins the groups of the two ends of a real trail, so two nodes share a group only if a chain of trails connects them. Conversely, if a path exists, each trail on it was offered to `union`, which leaves its two ends in one group, and groups only grow, so all nodes of the path end in one group; in particular `source` and `target` do. Hanging the smaller tree under the larger and shortening the path in `find` change the shape of the trees but never which nodes share a root.

### Complexity

- Time: O(V + E * α(V)) — creating the arrays costs V and each edge makes two `find` calls and at most one merge; with union by size and a path-shortening `find`, each call costs an amortised α(V), where α is the inverse of Ackermann's function and grows so slowly that it is effectively constant. The bound for this family of algorithms is due to Tarjan, "Efficiency of a Good But Not Linear Set Union Algorithm", Journal of the ACM 22(2), 1975, pages 215 to 225, doi:10.1145/321879.321884.
- Space: O(V) — a parent and a size entry per node.

### Trade-offs

It needs no adjacency list and no search, and it is the only one of the three that handles trails arriving one at a time: after each new trail, one `union` keeps the answer current. It cannot tell you the route, only that one exists, and it cannot handle one-way trails, where the groups are no longer symmetric. For one question on a fixed graph, `bfs` does the same work with less machinery to explain.

### Pitfalls and edge cases

- Merge roots, not the nodes themselves: calling `parent[a] = b` on arbitrary nodes loses the rest of a's group.
- Without union by size or a shortened `find`, a long chain of merges can build a tree as tall as the number of nodes, and `find` becomes linear.
- Compare `find(source)` with `find(target)` after all edges are read. Comparing early would miss trails that come later in the list.
- `source == target` returns `true` without special code, since both finds return the same root.

### Language notes

- Python: the disjoint set is two lists and a nested function; `find` loops instead of recursing, so a tall tree cannot hit the recursion limit.
- TypeScript: a small class over two `Int32Array`s; the swap of the two roots uses destructuring, `[rootA, rootB] = [rootB, rootA]`.
- Java: a private static nested class keeps the helper out of the public API; the swap needs a temporary variable.
- Kotlin: a private top-level class beside `Solution`; `rootA = rootB.also { rootB = rootA }` swaps the two roots.
- Go: `find` is a closure over the two slices; `rootA, rootB = rootB, rootA` swaps without a temporary.
- Rust: a `DisjointSet` struct owns both vectors so that `find` can take `&mut self` while it shortens paths; `std::mem::swap` swaps the two roots.
