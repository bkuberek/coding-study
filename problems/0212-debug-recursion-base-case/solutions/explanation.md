# Debug: Recursion Base Case: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| leaf-base-case | optimal | O(n) | O(h) | default answer: the empty tree is `false`, and only a leaf compares the remaining sum |

## Approach: leaf-base-case (Leaf as the base case)

### Intuition

The base case is attached to the wrong thing. The shipped code says "when I reach a missing node, the path is complete if nothing remains", so it treats every null child as a leaf. For a leaf that is harmless: both children are null, the check sees the right remaining sum, and the answer is right. For a node with only one child it is wrong: its missing side looks like a path that ends right there, so a prefix that stops at an inner node is accepted as a complete root-to-leaf path. The same base case makes the empty tree answer `true` for `target == 0`, although an empty tree has no paths.

That is why balanced breakdowns never failed: when every node has zero or two children, null children only appear below leaves. The fix moves the completion check to the leaf itself, and makes a null node mean "no path here".

### Debugging approach

1. **Classify passing and failing inputs.** The ticket names the distinguishing property: balanced breakdowns work. Failing trees contain a node with exactly one child.
2. **Minimize.** The smallest failure is two nodes, `[1, 2]` with target 1 (Example 2). The empty tree with target 0 is a zero-node failure.
3. **Trace the call that returns `true`.** For `[1, 2]` and target 1: `hasPathSum(1, 1)` computes remaining 0 and calls `hasPathSum(2, 0)`, which is false. It then calls `hasPathSum(null, 0)` for the missing right child, which returns `0 == 0`. The `true` comes from a null node, not from a leaf.
4. **State what the base case should mean,** then check it against the trace: a null subtree contains no paths, so its answer is `false` for any target. "Is the path complete?" is a question only a leaf can answer.
5. **Watch for the half-fix.** Adding a leaf check but keeping `return target == 0` for null still fails `h7`, `h9`, `h13` and `h15`, because a one-child node still recurses into its null side.

### Algorithm

1. If `root` is null, return `false`: there is no path in an empty subtree.
2. Subtract `root.val` from the target to get `remaining`.
3. If `root` is a leaf (both children null), return whether `remaining == 0`.
4. Otherwise return whether the left subtree or the right subtree has a path summing to `remaining`. A null child contributes `false` by step 1.

### Correctness

By induction on the tree height. A null tree has no root-to-leaf paths, so `false` is right for every target. A leaf has exactly one root-to-leaf path, itself, which sums to `target` exactly when `target - val == 0`. An inner node's root-to-leaf paths are the node followed by a root-to-leaf path of a non-null child. So a path sums to `target` exactly when some child's subtree has a path summing to `target - val`, and that is what the recursion returns: the null side contributes `false`, the non-null side is correct by induction. The original code violated the null case. It returned `target == 0` for a null tree, so it counted a non-existent path that ends at a missing child.

### Complexity

- Time: O(n) — each node is visited at most once, and `or` short-circuits once a path is found.
- Space: O(h) — the recursion stack is as deep as the tree height `h`, which is O(log n) when balanced and O(n) for a chain.

### Trade-offs

The recursive form mirrors the definition and is the expected interview answer. An iterative DFS with an explicit stack of `(node, remaining)` pairs gives the same result without recursion depth limits. That matters in Python (default limit about 1000 frames) and for very deep trees on any runtime. Defining the base case at the leaf costs one extra check per node and removes a whole class of bugs.

### Pitfalls and edge cases

- The general trap: a recursion's base case must describe a real instance of the problem. "Null child" and "leaf" are different things. The same bug breaks minimum depth: counting a null child as depth 0 makes a one-child node look shallow.
- The empty tree is `false` even for `target == 0`. There is no path, not even an empty one.
- Negative values mean you cannot stop early when the running sum passes `target`: a later negative node can bring it back.
- Zero-valued nodes do not make a node a leaf. Check the children, not the values.

### Prevention

- Write the base cases from the definition before writing the recursive step: what is the answer for an empty tree, and what is it for a single node?
- Test the tree shapes that separate the cases: empty, a single node, a left-only chain, a right-only chain, and a node with exactly one child. Balanced example trees hide this bug.
- A property test against a brute-force enumerator, which lists every root-to-leaf path explicitly and checks their sums, catches it on random small trees.

### Language notes

- Python: recursion depth is limited, about 1000 frames by default, which is why the constraints cap the height at 500. `or` short-circuits like `||`.
- TypeScript: check `=== null` explicitly. The support class uses `null` for missing children, not `undefined`.
- Java: `TreeNode` fields are public and nullable. `target - root.val` cannot overflow under these constraints; with unbounded values, use `long`.
- Kotlin: `root.left` is a Java platform type, so `== null` checks are needed and are what the reference uses. `` root.`val` `` needs backticks because `val` is a keyword.
