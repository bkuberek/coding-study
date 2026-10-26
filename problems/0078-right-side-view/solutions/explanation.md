# Right Side View: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| last-per-level | optimal | O(n) | O(w) | default answer; reuses the level-order walk |
| right-first-dfs | optimal | O(n) | O(h) | wide trees, or a recursive answer is preferred |

`n` is the number of nodes, `w` the largest number of nodes on one level and `h` the height.

## Approach: last-per-level (Breadth-first walk keeping the last node of each level)

### Intuition

The right side view is the last node of every level. A level-order walk with a queue already processes the tree one level at a time, so it only has to remember the last node of each level.

### Algorithm

1. If `root` is null, return an empty list. Otherwise put `root` in a queue.
2. While the queue is not empty:
   1. The queue holds exactly one level; record the value of its last node.
   2. Remove that many nodes, adding each node's non-null children to the back.
3. Return the recorded values.

### Correctness

As in level-order traversal, the queue holds exactly the nodes of one level, left to right, at the start of each iteration, because children are appended left before right and levels never mix. The last element is therefore the rightmost node of that level, which is the node seen from the right. One value is recorded per level, from the top down.

### Complexity

- Time: O(n) — each node is queued and removed once.
- Space: O(w) — the queue holds at most one level plus part of the next; the output has only `h` values.

### Trade-offs

It is the most direct answer and needs no recursion. On very wide trees its queue is larger than the depth-first stack, which matters only for memory.

### Pitfalls and edge cases

- Taking only right children (walking `root.right` repeatedly) misses levels where the right side has ended; Example 2 is that case.
- Read the level's last node before draining the level, or remember the last node removed.
- An empty tree returns an empty list.

### Language notes

- Python: `queue[-1]` peeks at the back of a `deque` without removing it.
- TypeScript: the reference keeps one array per level, so the last node is `level[level.length - 1]`.
- Java: `peekLast()` reads the back of an `ArrayDeque`.
- Kotlin: `level.last()` on the current level list, and `flatMap` with `listOfNotNull` builds the next level.

## Approach: right-first-dfs (Depth-first walk that visits the right child first)

### Intuition

Visit the right subtree before the left one and track the depth. On every depth, the first node this walk reaches is the rightmost one on that level, so a node belongs in the answer exactly when it is the first node seen at its depth, that is when its depth equals the number of values collected so far.

### Algorithm

1. Start with an empty list `view` and call `visit(root, 0)`.
2. In `visit(node, depth)`: return on null. If `depth == len(view)`, append `node.val`.
3. Recurse into `node.right` with `depth + 1`, then into `node.left` with `depth + 1`.
4. Return `view`.

### Correctness

The walk is a pre-order walk that prefers right. For two nodes on the same level, it visits first the one in the right subtree of their lowest common ancestor, which is the one further right, so the first node reached on each level is its rightmost node. `view` has one entry per level already reached; a node at depth `d` with `d == len(view)` is the first node reached on level `d`, because the walk reaches every level `d` only after it has reached levels `0` to `d - 1` on the way down.

### Complexity

- Time: O(n) — one call per node and per null child.
- Space: O(h) — the recursion stack; the output adds `h` values.

### Trade-offs

Memory follows the height instead of the width, and the code is very short. It depends on recursion depth, which the 3000-level limit keeps safe here; the breadth-first version has no such dependency.

### Pitfalls and edge cases

- Recursing left before right yields the left side view.
- Appending whenever `depth >= len(view)` is the same test, but `depth > len(view)` can never happen, so `==` documents the invariant.
- Deep trees: the 2000-level hidden path makes the recursion 2000 calls deep.

### Language notes

- Python: a nested function appends to the enclosing `view` list; no `nonlocal` is needed because the list itself is not reassigned.
- TypeScript: a recursive arrow function closes over `view`.
- Java: a static helper receives the list as a parameter.
- Kotlin: a local `fun` closes over the `MutableList`.
