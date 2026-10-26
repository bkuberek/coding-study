# Count Downward Path Sums: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| every-start | brute | O(n * h) | O(h) | shallow trees, or as a correctness oracle |
| prefix-backtracking | optimal | O(n) | O(h) | default answer |

`n` is the number of nodes and `h` the height of the tree. On a balanced tree `h` is about log n and the brute force is fast; on a path-shaped tree `h` is close to `n` and it becomes quadratic. The generated trees have height about n / 2.

## Approach: every-start (Walk down from every node)

### Intuition

Every downward path has a top node. For each node, enumerate the paths that start there by walking down with a running sum, and count the prefixes of the walk that hit the target.

### Algorithm

1. Visit every node `start` (any traversal order).
2. From `start`, walk every downward path with a stack of `(node, sum)` pairs, beginning with `(start, start.val)`.
3. Each time a popped sum equals `targetSum`, increment the count; push both children with their extended sums.
4. Return the count.

### Correctness

Each downward path is determined by its top node `start` and its bottom node `b`, a descendant of `start` (or `start` itself). The inner walk from `start` pops every such `b` exactly once, with the sum of the path from `start` to `b`, so each path is tested once.

### Complexity

- Time: O(n * h) — a node is visited once for each of its ancestors (and itself), at most h + 1 times; for a path-shaped tree that is O(n^2).
- Space: O(h) — the explicit stacks hold about one entry per level plus siblings; the reference keeps both traversals iterative, so deep trees do not exhaust the call stack.

### Trade-offs

Straightforward and fine for balanced trees, where it is O(n log n). It recomputes the same partial sums once per ancestor, which the prefix-sum approach avoids by looking backwards instead of forwards.

### Pitfalls and edge cases

- The empty path never counts, so `targetSum = 0` on a single node with value 7 gives 0.
- Do not stop a walk once the sum matches: negative values and zeros below can match again.
- Two nested recursions (one to pick the start, one to walk down) can reach depth 2h, which overflows default stacks on deep trees; iterating avoids it.

## Approach: prefix-backtracking (Prefix sums along the root path with backtracking)

### Intuition

Fix the bottom node `b` instead of the top. The nodes from the root to `b` form an array, and a downward path ending at `b` is a suffix of it. A suffix adds up to `targetSum` exactly when the current prefix sum minus an earlier prefix sum on the same root path equals `targetSum` (the same identity as in Subarray Sum Equals K). A depth-first traversal maintains the prefix sums of the current root path in a hash map: add one when going down, remove it when coming back up.

### Algorithm

1. Start a map `on_path = {0: 1}` (the empty prefix above the root).
2. Visit a node with the sum `above` of its ancestors:
   1. `total = above + node.val`.
   2. Add `on_path[total - targetSum]` to the answer: the number of ancestors (or the empty prefix) where a matching path starts.
   3. Increment `on_path[total]`, visit both children with `total`, then decrement `on_path[total]`.
3. Return the sum of all counts.

### Correctness

Invariant: when a node is visited, `on_path` holds exactly the prefix sums of its proper ancestors' root paths, plus the empty prefix. It holds at the root, and step 2.3 keeps it: the node's own prefix is added only while its children are visited, and removed before returning, so a sibling subtree never sees it. For a node `b` with prefix `total`, the downward paths ending at `b` correspond one-to-one to the prefixes above it (one per possible top node), and such a path has sum `total - prefix`. Step 2.2 therefore counts exactly the paths ending at `b` with sum `targetSum`; summing over all nodes counts every path once.

### Complexity

- Time: O(n) — each node does a constant number of average O(1) map operations.
- Space: O(h) — the recursion depth and the map hold one entry per level of the current path.

### Trade-offs

Linear regardless of the shape, and the expected answer. It needs recursion (or an explicit stack with an "exit" step to undo the map update), and the backtracking step is easy to forget. The brute force is simpler to explain first, then the prefix idea transfers directly from the array version.

### Pitfalls and edge cases

- Seed the map with sum 0 seen once, or paths that start at the root are missed.
- Look up `total - targetSum` before adding `total`; otherwise `targetSum = 0` counts the empty path at every node.
- Forgetting the decrement lets prefixes leak between sibling subtrees (case `h6` catches it).
- Prefix sums reach `h * 1000 <= 3 * 10^6` here, safely inside 32 bits; with larger values use 64-bit sums.

### Language notes

- Python: `Counter` returns 0 for a missing sum without inserting it; the runner raises the recursion limit, but by default Python stops at depth 1000, so deep trees need `sys.setrecursionlimit` or an explicit stack.
- TypeScript: an inner `function` closes over the map and the target; `Map.get` returns `undefined` for a missing sum, hence `?? 0`.
- Java: the map and target live in fields so the recursive helper takes only the node and the sum; `merge(total, -1, Integer::sum)` undoes the increment.
- Kotlin: a local `fun` captures the map; the node value is `` node.`val` `` because `val` is a Kotlin keyword.
