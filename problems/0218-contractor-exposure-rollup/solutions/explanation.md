# Contractor Exposure Rollup: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| iterative-dfs | optimal | O(V + E) | O(V + E) | default answer |

`V` is the number of contractors reachable from the root and `E` the number of edges among them.

## Approach: iterative-dfs (Iterative depth-first search with on-path and finished sets)

### Intuition

This is three-color depth-first search. A contractor on the current path (gray) that is met again closes a cycle. A contractor that is already finished (black) was reached through another path and has been counted, so it is skipped. A contractor never seen before (white) is counted and explored.

### Algorithm

1. Build a map from each contractor to the list of its children, and a map from contractor to exposure.
2. Start with the root on the path, the total set to the root's exposure (0 if it has no row), and a stack holding the root with an iterator over its children.
3. Look at the top frame. If it has a next child that is on the path, return `-1`. If that child is not finished, add its exposure to the total, put it on the path and push a frame for it. If the child is finished, skip it.
4. When a frame has no more children, pop it, take its contractor off the path and mark it finished.
5. When the stack is empty, return the total.

### Correctness

Depth-first search finds an edge back to a contractor on the current path exactly when the reachable part of the graph contains a cycle, so `-1` is returned if and only if a cycle is reachable from the root. Without a cycle, each contractor turns from unseen to on-path exactly once, and its exposure is added at that moment, so each reachable contractor is counted once, whatever number of paths lead to it. Cycles that the root cannot reach are never visited.

### Complexity

- Time: O(V + E) — each reachable contractor is pushed once and each edge is examined once.
- Space: O(V + E) — the child lists, the two sets and the stack.

### Trade-offs

A recursive search is shorter but is limited by the stack depth, and the constraints allow chains 2000 contractors deep. Kahn's algorithm also detects cycles, but only on the reachable subgraph, so it needs a reachability pass first. Adding up exposures without a finished set counts a shared subcontractor several times, and one visited set that does not separate the path from the finished contractors reports a shared subcontractor as a cycle.

### Pitfalls and edge cases

- One visited set cannot tell a shared subcontractor from a loop (`ex3`, `h5`).
- Counting a shared subcontractor once per path overstates the exposure.
- A root with no exposure row counts as zero (`h1`), and a lone root is a valid input (`h2`).
- A cycle that is not reachable from the root is ignored (`h3`).
- A contractor that hires itself is a cycle (`h4`), and so is a longer loop back to the root (`h10`).
- A duplicated edge changes nothing (`h8`).
- Contractors above the root, or beside it, are not part of the rollup (`h9`).
- A chain 2000 deep (`h7`) is a stack-depth trap for naive recursion in some runtimes.

### Language notes

- Python: `iter(children)` keeps the position of each frame, and `next(iterator, None)` ends a frame. `Decimal` addition is exact.
- TypeScript: `Map<string, string[]>`, two `Set<string>`s, and frames of the form `{ node, next }` with an index cursor. Exposures are added with `plus`.
- Java: `HashMap<String, List<String>>`, two `HashSet`s and a stack of small frame objects with a child index. Use `BigDecimal.add`; the stack lives on the heap, so there is no depth limit.
- Kotlin: `edges.groupBy({ it[0] }, { it[1] })`, an `ArrayDeque` of pairs of contractor and child iterator, and `total += own[child] ?: BigDecimal.ZERO`.
