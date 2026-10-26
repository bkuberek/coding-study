# Count Connected Components: Explanation

## Overview

V is the number of nodes and E the number of edges. α is the inverse Ackermann function, which grows so slowly that α(V) is at most 4 for any V that fits in memory.

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| quick-union | brute | O(V + E * V) | O(V) | to see why union-find needs its two optimizations |
| dfs | optimal | O(V + E) | O(V + E) | the whole graph is known up front |
| union-find | optimal | O(V + E * α(V)) | O(V) | edges arrive one at a time, or you only need the count |

## Approach: quick-union (Naive union-find that links roots without balancing or compression)

### Intuition

Start with every node in its own component and count V components. Process the edges one by one: an edge either joins two different components, which lowers the count by one, or lies inside one component and changes nothing. To tell which, keep each component as a tree of parent pointers whose root names the component; two nodes are in the same component exactly when they have the same root.

### Algorithm

1. Set `parent[x] = x` for every node and `components = V`.
2. `find(x)`: follow parent pointers until a node is its own parent, and return it.
3. For each edge `[a, b]`: if `find(a) != find(b)`, set the parent of `a`'s root to `b`'s root and decrement `components`.
4. Return `components`.

### Correctness

Invariant: after processing a prefix of the edges, the trees are exactly the connected components of the graph formed by that prefix, and `components` is their number. An edge between two trees connects two components into one, which is exactly what linking their roots does; an edge inside one tree joins nothing new. After all edges, the trees are the components of the whole graph.

### Complexity

- Time: O(V + E * V) — initialization is O(V); without balancing, a tree can degenerate into a chain of up to V nodes, so each `find` can take O(V). The generated inputs list star edges hub first, which builds exactly such a chain: every new leaf becomes the root above the hub's old root, and each later `find(hub)` walks the whole chain.
- Space: O(V) — one parent pointer per node.

### Trade-offs

Short and obviously correct, so it is the oracle, and on random inputs it is often fast. Its weakness is structural: the order of the edges decides the shape of the trees, and an unlucky order makes them chains. The two fixes below cost a few lines each.

### Pitfalls and edge cases

- Link roots, not the endpoints themselves: `parent[a] = b` can detach `a` from the rest of its tree.
- Only edges that join two different roots lower the count.
- A node with no edges stays its own root and counts as one component.

### Language notes

- Python: a nested `find` closes over `parent`; a `while` loop avoids recursion depth limits on chains.
- TypeScript: `Array.from({ length: n }, (_, x) => x)` initializes the parent array.
- Java: a static `find(parent, x)` helper keeps the loop free of recursion.
- Kotlin: `IntArray(n) { it }` initializes the parents; destructuring `(a, b)` reads an edge.

## Approach: dfs (Count the depth-first searches needed to cover every node)

### Intuition

A search from any node reaches exactly the nodes of its component. So scan the nodes in order; whenever one has not been reached yet, it starts a new component: count it and search from it, marking everything reachable.

### Algorithm

1. Build adjacency lists, adding each edge in both directions.
2. For each node not yet seen: increment the count, mark it seen and push it on a stack.
3. While the stack is not empty, pop a node and push every neighbor not seen yet, marking it.
4. Return the count.

### Correctness

Each search marks precisely the nodes reachable from its start, which is the start's component, because it follows every edge out of every node it reaches. A node starts a search only if no earlier search reached it, that is, only if its component was not counted yet, and every component's first node in scan order starts one. So the count equals the number of components.

### Complexity

- Time: O(V + E) — every node is pushed once and every edge is examined twice, once from each end.
- Space: O(V + E) — the adjacency lists hold 2E entries; the stack and marks hold O(V).

### Trade-offs

Optimal and simple when the whole graph is given at once. It needs adjacency lists, so it uses more memory than union-find, and it cannot cheaply handle edges that arrive after the search: union-find simply processes the next edge.

### Pitfalls and edge cases

- Add every edge in both directions; the graph is undirected.
- Mark nodes when they are pushed, not when they are popped, or a node can be pushed many times.
- An explicit stack avoids recursion limits on long paths (a path of 2000 nodes would exceed Python's default limit).

### Language notes

- Python: a plain list is a stack with `append` and `pop`.
- TypeScript: `stack.pop() as number` narrows the `number | undefined` result inside the non-empty loop.
- Java: `ArrayDeque<Integer>` with `push` and `pop` is the recommended stack (the legacy `Stack` class is synchronized).
- Kotlin: `kotlin.collections.ArrayDeque` with `addLast` and `removeLast` serves as the stack.

## Approach: union-find (Union by size with path compression)

### Intuition

Keep the quick-union idea and fix the tree shapes. Union by size hangs the smaller tree under the root of the larger one, so a node's depth grows only when its tree at least doubles: no tree gets deeper than log2(V). Path compression makes every node visited by a `find` point straight at the root, so the next `find` on any of them takes one step. Together they make each operation run in amortized O(α(V)) time.

### Algorithm

1. Set `parent[x] = x` and `size[x] = 1` for every node, and `components = V`.
2. `find(x)`: walk up to the root, then walk the same path again and point every node on it at the root.
3. `union(a, b)`: find both roots; if they are equal, report no merge. Otherwise put the root of the smaller tree under the root of the larger one, add the sizes, and report a merge.
4. For each edge, decrement `components` when `union` reports a merge, and return `components`.

### Correctness

Neither optimization changes which nodes share a root. Union by size only chooses which of the two roots becomes the child, and both choices merge the same two sets. Path compression only re-points nodes at the root they already had. So the invariant of the naive version still holds: the trees are the components of the edges processed so far, and the count is their number.

### Complexity

- Time: O(V + E * α(V)) — initialization is O(V); by the Tarjan analysis, any sequence of m operations on V elements with union by size (or rank) and path compression takes O(m * α(V)) time, so each of the 2E finds is amortized O(α(V)). Union by size alone already bounds every `find` by O(log V).
- Space: O(V) — the parent and size arrays.

### Trade-offs

Near-linear, with less memory than adjacency lists, and it works online: you can report the number of components after every edge, which depth-first search cannot do without starting over. The amortized bound means a single `find` can still be slow, but never many of them. Union by rank (merging by tree height instead of node count) gives the same bound; size is handy when the problem also needs component sizes.

### Pitfalls and edge cases

- Compare sizes of roots, not of the original endpoints.
- Path halving (`parent[x] = parent[parent[x]]` while walking up) is a one-pass alternative to the two-pass compression used here, with the same bound.
- A recursive `find` with compression is elegant but can hit recursion limits before the trees become shallow; the iterative form avoids that.

### Language notes

- Python: `parent[x], x = root, parent[x]` re-points `x` and steps to its old parent in one tuple assignment, because the right side is evaluated first.
- TypeScript: a small `DisjointSets` class with private fields assigned in the constructor body (no parameter properties) keeps `find` and `union` together.
- Java: a `private static final` nested class holds the two `int[]` arrays; arrays of primitives avoid boxing.
- Kotlin: a file-private class with `IntArray` fields; `rootA = rootB.also { rootB = rootA }` swaps the two roots in one line.
