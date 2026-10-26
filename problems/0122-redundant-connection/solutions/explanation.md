# Redundant Connection: Explanation

## Overview

n is the number of nodes, which equals the number of edges. All three approaches add the edges in list order and stop at the first one whose ends are already connected; they differ in how they answer that question. α is the inverse Ackermann function, at most 4 for any practical n.

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| path-search | brute | O(n^2) | O(n) | the direct idea; fine for a few hundred edges |
| quick-union | intermediate | O(n^2) | O(n) | to see where naive union-find degrades |
| union-find | optimal | O(n * α(n)) | O(n) | default answer |

Why the first such edge is the answer: a tree on n nodes has n - 1 edges, so the n edges contain exactly one cycle, and removing any cycle edge leaves a tree. While edges are added in order, no cycle exists until its last edge arrives, and that last edge is exactly the first whose ends are already connected. Every other cycle edge comes earlier in the list, so this edge is the cycle edge that appears last.

## Approach: path-search (Before adding each edge, search the edges so far for a path between its ends)

### Intuition

Build the graph edge by edge. Before adding `[a, b]`, run a depth-first search from `a` over the edges added so far; if it reaches `b`, the new edge would close a cycle, so it is the answer.

### Algorithm

1. Start with empty adjacency lists.
2. For each edge `[a, b]` in order: if a search from `a` over the current lists reaches `b`, return `[a, b]`; otherwise add the edge in both directions.

### Correctness

The search returns `true` exactly when `a` and `b` are connected by edges listed before the current one, because it follows every edge already added from every node it reaches. By the argument in the overview, the first edge for which that holds is the required answer. The input always contains one, so the loop returns before running out of edges.

### Complexity

- Time: O(n^2) — each of the n searches visits at most the n nodes and the fewer than n edges added so far.
- Space: O(n) — the adjacency lists hold at most 2n entries, and each search keeps O(n) marks and stack entries.

### Trade-offs

Clearly correct, so it is the oracle. It repeats a full search for every edge, although all it needs to know is which component each node belongs to, which is precisely the information union-find maintains.

### Pitfalls and edge cases

- Search before adding the edge, or every edge looks redundant.
- Return the edge as listed; `[3, 1]` and `[1, 3]` are different outputs.
- An explicit stack avoids recursion limits on long paths.

### Language notes

- Python: a set of seen nodes and a list used as a stack.
- TypeScript: `stack.pop() as number` is safe inside the non-empty loop.
- Java: a fresh `boolean[]` per search and an `ArrayDeque<Integer>` stack.
- Kotlin: `ArrayDeque(listOf(start))` seeds the stack; `val (a, b) = edge` destructures the pair while `edge` itself is returned unchanged.

## Approach: quick-union (Naive union-find that links roots without balancing or compression)

### Intuition

Keep every component as a tree of parent pointers; two nodes are connected exactly when they have the same root. For each edge, compare the roots of its ends: equal roots mean the edge closes the cycle, different roots mean it merges two components, so link one root under the other.

### Algorithm

1. Set `parent[x] = x` for every node.
2. For each edge `[a, b]`: find both roots by following parent pointers. If they are equal, return the edge; otherwise set the parent of `a`'s root to `b`'s root.

### Correctness

Invariant: the trees are exactly the connected components of the edges processed so far. Linking two different roots merges two components, which is what adding an edge between them does. So equal roots means the ends are already connected, which identifies the answer as explained in the overview.

### Complexity

- Time: O(n^2) — without balancing, trees can become chains of length up to n, so each `find` can cost O(n). The generated inputs contain a large star listed hub first: every star edge hangs the hub's current root under a fresh leaf, so the hub sinks one level deeper each time and every later `find` on it walks the whole chain.
- Space: O(n) — the parent array.

### Trade-offs

Much faster than a search in typical inputs and only a few lines, but its running time depends on the edge order, and the worst case is no better than the search. Union by size and path compression remove that dependence.

### Pitfalls and edge cases

- Link roots, never the endpoints themselves.
- Size the parent array `n + 1`, since nodes are labelled from 1.

### Language notes

- Python: a `while` loop `find` avoids recursion depth issues on long chains.
- TypeScript: the closure `find` reassigns its parameter, which is a local copy.
- Java: a static `find(parent, x)` helper.
- Kotlin: a local `find` with a `var` copy of its argument, since Kotlin parameters are read-only.

## Approach: union-find (Union by size with path compression)

### Intuition

Same structure, with two fixes. Union by size hangs the smaller tree under the larger root, so no tree gets deeper than log2(n). Path compression points every node visited by a `find` directly at its root, flattening the paths that future finds will take. Together they make each operation amortized O(α(n)).

### Algorithm

1. Set `parent[x] = x` and `size[x] = 1`.
2. `find(x)`: walk up to the root, then re-point every node on the path at it.
3. `union(a, b)`: if both roots are equal, report "already connected"; otherwise attach the smaller root under the larger and add the sizes.
4. Return the first edge for which `union` reports "already connected".

### Correctness

Union by size only decides which root becomes the child, and path compression only shortens paths to the same root, so neither changes which nodes share a root. The invariant and the argument of the naive version carry over unchanged.

### Complexity

- Time: O(n * α(n)) — with both optimizations, any sequence of m operations on n elements costs O(m * α(n)) (Tarjan's analysis); here there are at most 2n finds.
- Space: O(n) — the parent and size arrays.

### Trade-offs

Near-linear and independent of the edge order, with two small arrays and no adjacency lists. It is the standard tool whenever edges arrive one at a time and the question is "are these two already connected?". The directed variant (Redundant Connection II) needs extra care for a node with two parents, but the same structure detects the cycle.

### Pitfalls and edge cases

- Compare the sizes of the roots, not of the endpoints.
- The iterative two-pass `find` avoids the recursion depth a naive recursive compression would need on a long chain.

### Language notes

- Python: `parent[x], x = root, parent[x]` re-points and advances in one tuple assignment.
- TypeScript: a `DisjointSets` class whose `union` returns whether it merged keeps the main loop short; fields are assigned in the constructor body, without parameter properties.
- Java: a `private static final` nested class over two `int[]` arrays.
- Kotlin: `edges.firstOrNull { (a, b) -> !sets.union(a, b) }` stops at the first edge that merges nothing.
