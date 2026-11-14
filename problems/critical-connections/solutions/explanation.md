# Critical Connections: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| remove-each-edge | brute | O(E·(V + E)) | O(V + E) | tiny networks, or to check a faster solution |
| tarjan-low-link | optimal | O(V + E) | O(V + E) | default answer |

Servers are nodes and cables are undirected edges; a critical cable is a bridge, an edge whose removal disconnects the graph. An edge is a bridge exactly when it lies on no cycle. The brute force tests the definition edge by edge; Tarjan's algorithm finds every bridge in one depth-first search.

## Approach: remove-each-edge (Remove each connection and test whether the network splits)

### Intuition

Apply the definition literally: cut one cable, check whether all servers can still reach each other, and put the cable back. Checking connectivity is one graph search from any server.

### Algorithm

1. Build adjacency lists that remember the index of each cable.
2. For every cable `i`: run a depth-first search from server 0 that never uses cable `i`, counting the servers reached. If fewer than `n` are reached, cable `i` is critical.
3. Return the critical cables.

### Correctness

The network is connected, so cutting a cable splits it exactly when some server becomes unreachable from server 0, which is exactly when the search that ignores that cable reaches fewer than `n` servers. Each cable is tested once.

### Complexity

- Time: O(E·(V + E)) — one full search per cable.
- Space: O(V + E) — the adjacency lists, plus one visited array and stack per search.

### Trade-offs

Obviously correct, which makes it a good oracle, but quadratic: with 5000 cables and 2000 servers it already performs about 35 million steps, and the original problem allows 10^5 of each. The low-link method gives the same answer in one search.

### Pitfalls and edge cases

- Skip the cable by index, not by its endpoints, so the check stays right even in variants that allow parallel cables.
- Cables may list their endpoints in either order; the answer echoes each cable as given.
- A network that is a single ring has no critical cable.

### Language notes

- Python: adjacency entries are `(neighbor, cable index)` tuples, and the search is an explicit stack.
- TypeScript: `connections.filter((_, index) => ...)` keeps the critical cables; `Uint8Array` marks visited servers.
- Java: `List.of(a, b)` builds each answer pair as an immutable `List<Integer>`.
- Kotlin: `connections.indices.filter { ... }.map { connections[it].toList() }` turns the critical `IntArray` cables into `List<Int>` pairs.
- Go: adjacency entries are small `link{neighbor, index}` structs, and the search uses a slice as its stack. The answer starts as `[][]int{}` rather than a nil slice so that "no critical cable" encodes as `[]`. The answer pairs are fresh two-element slices, not slices of `connections`.
- Rust: `connected_without` is a closure borrowing `adjacency`, and the final `into_iter().enumerate().filter(...).map(...)` moves each critical cable out of `connections` without copying it. Cable indexes are `usize` and the results go back out as the original `Vec<i32>` pairs.

## Approach: tarjan-low-link (Tarjan's bridge finding with discovery times and low links)

### Intuition

Run one depth-first search and number the servers in the order they are discovered. The search tree's edges go from parents to children; every other cable connects a server to one of its ancestors (in an undirected depth-first search there are no cross edges). For each server `v`, let `low[v]` be the smallest discovery number reachable from `v`'s subtree using at most one non-tree cable. If `low[v]` is larger than the discovery number of `v`'s parent `u`, nothing in `v`'s subtree has another way back to `u` or above, so the tree edge `u`–`v` is the subtree's only link to the rest: a bridge.

### Algorithm

1. Build adjacency lists and set every discovery number to -1.
2. `visit(u, parent)`: give `u` the next discovery number and set `low[u]` to it. For each neighbor `v` of `u` other than `parent`:
   1. If `v` is undiscovered, call `visit(v, u)`, then set `low[u] = min(low[u], low[v])`, and record `[u, v]` as critical if `low[v] > discovered[u]`.
   2. Otherwise `v` is an ancestor reached by a back cable: set `low[u] = min(low[u], discovered[v])`.
3. Call `visit(0, -1)` and return the recorded cables.

### Correctness

Non-tree cables of an undirected depth-first search always join a server to an ancestor, so a cycle through the tree edge `u`–`v` must use a back cable from `v`'s subtree to `u` or one of its ancestors. `low[v]` is exactly the smallest discovery number such back cables reach, computed bottom-up: a subtree's best is the best of its root's own back cables and its children's subtrees. So `low[v] <= discovered[u]` holds exactly when the tree edge lies on a cycle; otherwise it is a bridge. Non-tree cables are never bridges, because each closes a cycle with tree edges. Skipping only the parent avoids treating the tree edge itself as a way back, which is safe because no two servers share two cables.

### Complexity

- Time: O(V + E) — each server is visited once, and each cable is examined twice, once from each end.
- Space: O(V + E) — adjacency lists, two arrays of numbers, and a recursion as deep as the search tree (up to V).

### Trade-offs

Linear and the standard answer; the same discovery and low-link numbers also give articulation points (critical servers) with a slightly different test. The recursion goes up to V levels, fine for the 2000 servers allowed here; for 10^5 servers, convert it to an explicit stack of `(server, next neighbor index)` frames, or raise the stack size.

### Pitfalls and edge cases

- Use `>` in the bridge test; `>=` is the articulation-point test and marks edges inside cycles.
- Update `low[u]` with `discovered[v]` for back cables, not `low[v]`; for bridges both work, but mixing them up breaks the articulation-point variant.
- Skip the parent only once; with parallel cables you would skip by cable index instead.

### Language notes

- Python: the search is a nested function using `nonlocal clock`; the runner's large recursion limit and stack make 2000 levels safe.
- TypeScript: a recursive arrow function over `Int32Array`s; 2000 levels fit Node's default stack.
- Java: the search state lives in fields, so the recursive method takes just the server and its parent; JVM threads in the runner have a large stack.
- Kotlin: a local recursive function that captures the arrays and a `var clock`.
- Go: the recursion is a closure declared with `var visit func(server, parent int)` so that it can call itself, and it updates `clock`, `low`, `discovered` and `bridges` in the enclosing scope. `min` is the built-in (Go 1.21+). Go grows goroutine stacks on demand, so a recursion 2000 levels deep needs no special care.
- Rust: a closure cannot call itself, so the arrays live in a `Search` struct and `visit` is a `&mut self` method. `let adjacency = self.adjacency;` copies the shared reference out of `self` before the loop, which lets the loop read the adjacency list while `self.visit` borrows `self` mutably. The parent is an `Option<usize>` (`None` for the root) instead of a `-1` sentinel, because `usize` cannot hold `-1`.
