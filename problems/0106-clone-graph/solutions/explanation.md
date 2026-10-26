# Clone Graph: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| dfs | optimal | O(V + E) | O(V) | default answer; shortest to write, with a depth bound |
| bfs | optimal | O(V + E) | O(V) | the graph may be deep enough to overflow the call stack |

Both approaches rest on the same idea: a map from every original node to its copy. The map is the visited set of the traversal and also the way to find the copy of a neighbor that was already made. They differ only in the order in which nodes are reached.

## Approach: dfs (Recursive copy with a map of clones)

### Intuition

Copying a node means copying its value and then its neighbors, and copying a neighbor is the same problem again, so recursion fits. Cycles are the only trap: from node 1 you reach node 2 and from node 2 you come back to node 1. If node 1's copy is already in the map before its neighbors are copied, the second visit returns that copy instead of looping forever.

### Algorithm

1. If `node` is null, return null.
2. Define `copy(original)`:
   1. If `original` is in the map, return its copy.
   2. Create `clone` with `original.val` and store `original -> clone` in the map.
   3. For each neighbor of `original`, in order, append `copy(neighbor)` to `clone.neighbors`.
   4. Return `clone`.
3. Return `copy(node)`.

### Correctness

Each original node gets exactly one copy, because a copy is created only when the node is missing from the map and is stored immediately. Every call on a node that is already in the map returns at once, so each node runs steps 2.2 to 2.3 once and the recursion ends. In that single run, the copy's neighbor list is built from the copies of the original's neighbors, in the original order, so every edge of the original appears between the corresponding copies. Since the graph is connected, the recursion from `node` reaches every node, and no original node is ever placed into a copy's neighbor list.

### Complexity

- Time: O(V + E) — each node is copied once, and each adjacency entry (two per undirected edge) causes one map lookup and one append.
- Space: O(V) — the map holds V entries and the recursion can be V calls deep on a path; the copy itself is output.

### Trade-offs

The most natural code for the problem and the usual interview answer. Its weak point is depth: the recursion is as deep as the longest chain of first discoveries, up to V. The constraints keep V at 2000 or less, which every runtime handles; for much larger graphs use `bfs` or an explicit stack.

### Pitfalls and edge cases

- Put the copy into the map before recursing into the neighbors; storing it afterwards loops forever on the first cycle.
- Key the map by the node object, not by `val`. Values happen to be unique here, but the identity of the node is what defines the graph.
- The empty graph: `node` is null and the answer is null, not a node with value 0.
- Never append an original neighbor to a copy; the checker reports it as a shared node.

### Language notes

- Python: `GraphNode` does not override `__eq__`, so a `dict` keyed by nodes uses identity, as needed. The neighbor list is built with one list comprehension of recursive calls.
- TypeScript: `Map<GraphNode, GraphNode>` compares object keys by reference. The recursive helper is a closure over the map; 2000 frames are well inside Node's default stack.
- Java: `HashMap` with `GraphNode` keys uses identity because the class does not override `equals` and `hashCode`; `IdentityHashMap` would make that explicit. Recursion depth is no concern on the runner's 256 MiB stack.
- Kotlin: a local function captures the map; `clones[original]?.let { return it }` returns early from `copy`, because `let` is inline. Use `` original.`val` `` since `val` is a keyword.

## Approach: bfs (Breadth-first copy with a map of clones)

### Intuition

The same map, filled by a queue instead of the call stack. When a node leaves the queue, all its neighbors get copies (new ones for nodes seen for the first time, which also join the queue), and those copies are appended to the node's copy in the original order.

### Algorithm

1. If `node` is null, return null.
2. Map `node` to a new copy and put `node` in a queue.
3. While the queue is not empty:
   1. Take `original` from the front and look up its copy `clone`.
   2. For each neighbor of `original`, in order: if it has no copy yet, create one, store it and enqueue the neighbor; append the neighbor's copy to `clone.neighbors`.
4. Return the copy of `node`.

### Correctness

A node is enqueued exactly when its copy is created, so every node is dequeued once and its copy's neighbor list is filled once, in the original order. Every neighbor of a dequeued node gets a copy, so by induction on the distance from `node`, every node of the connected graph is copied and dequeued. As in `dfs`, each original edge appears between the two copies and only copies are ever linked.

### Complexity

- Time: O(V + E) — each node passes through the queue once and each adjacency entry is handled once.
- Space: O(V) — the map holds V entries and the queue at most V nodes.

### Trade-offs

No recursion, so no stack limit, for a few more lines. It is the safer default on unknown inputs; `dfs` is shorter. Both create the same graph, because the neighbor order comes from the original lists, not from the traversal order.

### Pitfalls and edge cases

- Create the copy and enqueue a node at the same moment; enqueuing nodes that already have a copy repeats work and duplicates neighbors.
- Append the neighbor's copy for every edge, including edges to nodes that were copied earlier; only the enqueue is conditional.
- The single node `[[]]` has an empty neighbor list and must still be copied.

### Language notes

- Python: `collections.deque` for the queue; a `dict` keyed by nodes for the copies.
- TypeScript: an array with a moving head index is the queue, since `shift()` is linear; `new GraphNode(val)` starts with a fresh empty `neighbors` array because default arguments are evaluated per call.
- Java: `ArrayDeque` as the queue and `HashMap` for the copies; `GraphNode.neighbors` is a mutable `ArrayList`.
- Kotlin: `getOrPut` creates and enqueues a missing copy in one expression; `kotlin.collections.ArrayDeque` with `addLast` and `removeFirst` is the queue.
