# Binary Tree Maximum Path Sum: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| gain-per-node | brute | O(n * h) | O(h) | a first version that makes the "turning node" idea explicit |
| postorder-gain | optimal | O(n) | O(h) | default answer |

`n` is the number of nodes and `h` the height of the tree.

## Approach: gain-per-node (Recompute the best downward gains at every node)

### Intuition

Every path has one highest node where it turns. Below that node it goes down at most once on each side, and on each side it should take the best downward path, or nothing at all if every downward path there has a negative sum. So for a fixed turning node, the best path is its value plus the positive parts of the best downward paths of its two children. Try every node as the turning node.

### Algorithm

1. Define `gain(node)`: 0 for null, otherwise `node.val + max(0, gain(left), gain(right))`, the best sum of a path that starts at `node` and goes only down.
2. For the current node, compute `node.val + max(0, gain(left)) + max(0, gain(right))`.
3. Recursively compute the answer for each existing child and return the largest of the three values.

### Correctness

`gain` is correct by induction: a downward path from a node is the node alone or the node followed by a downward path from one child, and the best one takes the larger child gain when it is positive. A path with highest node `x` consists of `x`, possibly a downward path from `x.left` and possibly one from `x.right`, so the best such path is `x.val` plus the positive parts of the two child gains. The recursion evaluates this for every node, and every path has exactly one highest node, so the maximum is the answer.

### Complexity

- Time: O(n * h) — `gain` scans the whole subtree under each child of every node, so a node is scanned once per ancestor: O(n log n) for random trees, O(n^2) for a path.
- Space: O(h) — the recursion depths of the outer search and of `gain` add up to at most the height.

### Trade-offs

It separates the two ideas of the problem (downward gains and turning nodes) cleanly, which makes it a good stepping stone, but it recomputes the same gains many times; on a 2000-node path that is about two million calls.

### Pitfalls and edge cases

- All values negative: the answer is the largest single value, not 0. Starting from 0 or clamping the turning sum at 0 gives the wrong answer for Example 2.
- Clamping only the children's gains at 0, never the node's own value: the node is always part of its path.
- A path may not branch: the value returned upward uses only one side.

### Language notes

- Python: `max(0, a, b)` takes any number of arguments.
- TypeScript: `Math.max(0, ...)` likewise; the root is non-null by the constraints, asserted with `!`.
- Java: `Math.max` takes two arguments, so three-way maxima are nested. Sums stay within ±10^8, far from `int` overflow.
- Kotlin: `maxOf` has a three-argument overload; `requireNotNull` documents the non-empty guarantee.

## Approach: postorder-gain (One post-order pass returning downward gains)

### Intuition

The brute force needs, at each node, the gains of its two children. A post-order walk computes those first anyway, so one walk can do both jobs: return the node's own gain to its parent, and on the way update the best path turning at the node.

### Algorithm

1. Start `best` at the root's value (a valid path).
2. Define `gain(node)`: 0 for null; otherwise `left = max(0, gain(node.left))`, `right = max(0, gain(node.right))`, update `best = max(best, node.val + left + right)`, and return `node.val + max(left, right)`.
3. Call `gain(root)` and return `best`.

### Correctness

Each call returns the best downward gain of its node, by the same induction as before, because it uses the positive parts of the children's gains. When the call for `x` updates `best`, `x.val + left + right` is the best path whose highest node is `x`. Every node gets exactly one call, so after the walk `best` is the maximum over all turning nodes, the best path sum. The initial value is the root alone, a real path, so `best` never exceeds the true answer.

### Complexity

- Time: O(n) — one call per node and per null child, each O(1).
- Space: O(h) — the recursion stack.

### Trade-offs

Linear and short; this is the expected answer for this hard problem. The subtle part is returning one value (a downward path) while recording another (a turning path); stating the two meanings explicitly is most of the explanation in an interview.

### Pitfalls and edge cases

- Initializing `best` to 0 is wrong when every value is negative; use the root's value or the smallest possible value.
- Returning `node.val + left + right` to the parent would let a path branch.
- The 2000-level hidden path of positive values makes the answer the sum of the whole path, two million, and exercises the recursion depth.

### Language notes

- Python: `nonlocal best` updates the running maximum from the nested function.
- TypeScript: an arrow function closes over `let best`.
- Java: an instance field holds `best`, reset at the start of each call.
- Kotlin: a local `fun gain` captures `var best`.
