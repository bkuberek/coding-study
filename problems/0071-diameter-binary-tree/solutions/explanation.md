# Diameter of a Binary Tree: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| height-per-node | brute | O(n * h) | O(h) | a first, obviously correct version |
| postorder-heights | optimal | O(n) | O(h) | default answer |

`n` is the number of nodes and `h` the height of the tree.

## Approach: height-per-node (Recompute both heights at every node)

### Intuition

Every path has exactly one highest node, where it turns from going up to going down. The longest path that turns at a node goes as deep as possible on both sides, so its length in edges is the height of the left subtree plus the height of the right subtree (heights counted in nodes). The diameter is the best of those values over all nodes.

### Algorithm

1. If `root` is null, return 0.
2. Compute `turningHere = height(root.left) + height(root.right)` with a separate recursive height function.
3. Recursively compute the diameters of the left and right subtrees.
4. Return the largest of the three numbers.

### Correctness

Take a longest path and its highest node `x`. Below `x` the path uses at most one downward branch into each subtree, and each branch is at most as long as that subtree's height, so the path has at most `height(x.left) + height(x.right)` edges, and a path of exactly that length exists (go to a deepest node on each side). The recursion evaluates this value at every node, because every node is either the root or a node of one subtree, so the maximum it returns equals the diameter.

### Complexity

- Time: O(n * h) — the height function visits the whole subtree of every node, and a node is inside the subtrees of its `depth` ancestors. That is O(n log n) on the generator's random trees and O(n^2) on a path.
- Space: O(h) — the outer recursion and the height recursion together never go deeper than the tree.

### Trade-offs

It follows the definition directly and is easy to argue about, but it recomputes the same heights over and over. On a path of a few thousand nodes it already does millions of steps, while the post-order version does a few thousand.

### Pitfalls and edge cases

- Assuming the longest path passes through the root: Example 2 is the counterexample, which is why the recursion also looks inside the subtrees.
- Counting nodes instead of edges: with heights counted in nodes, `left + right` is already the number of edges of the path turning here.
- A single node has diameter 0.

### Language notes

- Python: the default recursion limit is 1000; the runner raises it and uses a large thread stack, so the 2000-level hidden case is safe here but would fail in a plain script.
- TypeScript: `Math.max` takes any number of arguments, so the three candidates fit in one call.
- Java: `Math.max` takes two arguments, so the reference combines the two subtree diameters first.
- Kotlin: `maxOf` has a three-argument overload.

## Approach: postorder-heights (One post-order pass returning heights)

### Intuition

The brute force needs two numbers per node: the subtree heights, to evaluate the path turning there, and the node's own height for its parent. A single post-order walk produces exactly that: each call returns its height, and the parent, which now has both children's heights, updates the best path turning at itself.

### Algorithm

1. Keep a running maximum `best = 0`.
2. Define `height(node)`: return 0 for null; otherwise compute `left = height(node.left)` and `right = height(node.right)`, set `best = max(best, left + right)`, and return `1 + max(left, right)`.
3. Call `height(root)` and return `best`.

### Correctness

`height` returns the correct height by induction (the same recurrence as for maximum depth). When the call for node `x` updates `best`, `left + right` is exactly the length of the longest path turning at `x`, by the argument in the brute-force section. Every node gets one call, so after the walk `best` is the maximum over all turning nodes, which is the diameter.

### Complexity

- Time: O(n) — one call per node and per null child, O(1) work each.
- Space: O(h) — the recursion stack: O(log n) for random trees and O(n) for a path.

### Trade-offs

Linear time with the same short structure as a height function; this is the expected answer. The shared `best` variable is the only extra state. A fully iterative version (post-order with an explicit stack and a map of heights) removes the recursion at the cost of clarity.

### Pitfalls and edge cases

- Returning `left + right` instead of `1 + max(left, right)`: the parent needs the height of one branch, not the path length.
- Resetting `best` per call: it must survive across the whole walk. In Java the reference resets the field at the start of each top-level call, so reusing one `Solution` object stays correct.
- Deep trees: the 2000-level hidden path exercises the recursion depth.

### Language notes

- Python: `nonlocal best` lets the nested function update the counter of the enclosing call.
- TypeScript: an arrow function closes over `let best`.
- Java: there are no closures over mutable locals, so the reference uses an instance field (an `int[]` holder is a common alternative).
- Kotlin: a local `fun` can read and write the enclosing `var best` directly.
