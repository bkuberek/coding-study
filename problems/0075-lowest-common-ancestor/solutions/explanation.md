# Lowest Common Ancestor: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| parent-map | optimal | O(n) | O(n) | an iterative answer, or many queries on the same tree |
| recursive | optimal | O(n) | O(h) | default answer; one pass, no extra structures |

`n` is the number of nodes and `h` the height of the tree.

## Approach: parent-map (Parent links and the set of ancestors of p)

### Intuition

With a link from every node to its parent, the ancestors of a node are a walk upward. The lowest common ancestor is the first ancestor of `q` (starting from `q` itself) that is also an ancestor of `p`. The tree has no parent links, so build them in a map first.

### Algorithm

1. Walk the tree with an explicit stack, recording each child's parent in a map, until both `p` and `q` have entries.
2. Walk from `p` up to the root and put every node in a set.
3. Walk from `q` upward and return the first node that is in the set.

### Correctness

The set holds exactly the ancestors of `p`, including `p`. Walking up from `q` visits the ancestors of `q` from the deepest to the root. The common ancestors of both are therefore the nodes on that walk that are in the set, and the first one met is the deepest of them, the lowest common ancestor. The root is an ancestor of everything, so the walk always stops. Both maps are keyed by node identity, which is what the problem asks about: values are only labels.

### Complexity

- Time: O(n) — the map is built in at most one visit per node, and the two upward walks take O(h) each.
- Space: O(n) — the parent map can hold every node; the ancestor set holds at most `h + 1` nodes.

### Trade-offs

It is iterative, so tree height never matters, and the parent map can be reused: after building it once, every further query costs only O(h). For a single query it uses more memory than the recursion. Stopping the build as soon as both nodes are mapped saves work when they are found early.

### Pitfalls and edge cases

- Keys must be the node objects, not their values, in general; here values are unique, but the reference keeps the identity view the problem is about.
- `p == q`: the set contains `p`, and the walk from `q` stops immediately.
- One node is an ancestor of the other: the walk from `q` reaches `p` (or starts there).

### Language notes

- Python: `TreeNode` does not override `__eq__`, so it hashes by identity and works as a dictionary key.
- TypeScript: `Map` and `Set` compare object keys by identity; `parent.get(node)!` asserts that every node on the walk is mapped.
- Java: `TreeNode` keeps `Object`'s identity `equals` and `hashCode`; `HashMap` accepts the `null` parent of the root.
- Kotlin: `generateSequence(p) { parent[it] }` lists a node and its ancestors and ends at the root's `null` parent; `first { it in ancestorsOfP }` finds the answer.
- Go: pointers are comparable and hashable, so `map[*TreeNode]*TreeNode` and `map[*TreeNode]bool` key the nodes by identity directly.
- Rust: `Rc<RefCell<TreeNode>>` does not implement `Hash`, and hashing by value would merge nodes that merely hold equal numbers. The maps are keyed by `Rc::as_ptr(&node)`, the address of the allocation, which is a plain `*const` pointer that is never dereferenced.

## Approach: recursive (Post-order search that reports what each subtree contains)

### Intuition

Let a search of a subtree report what it found: `p` or `q` if it met one of them, null if it met neither. A node whose two subtrees both report something has `p` on one side and `q` on the other, so it is the answer. A node that is itself `p` or `q` can stop: whatever else is below it, it is either the answer or the found node its parent needs to hear about.

### Algorithm

1. If `root` is null, `p` or `q`, return `root`.
2. Search the left and right subtrees recursively.
3. If both searches returned a node, return `root`.
4. Otherwise return whichever result is not null (or null if both are).

### Correctness

Claim: the call on subtree `T` returns the lowest common ancestor if `T` contains both `p` and `q`, the one it contains if it contains exactly one, and null if it contains neither. By induction on height. If `T`'s root is `p` (or `q`), the claim holds: if the other node is below, the root is their lowest common ancestor; if it is not, the root is the one node `T` contains. Otherwise the root is neither. If both subtrees report a node, they contain one each, so the root is the lowest common ancestor. If only one reports, it holds everything `T` contains and its report is already the right answer for `T`. Applied to the whole tree, which contains both nodes, the call returns the lowest common ancestor.

### Complexity

- Time: O(n) — each node is visited at most once.
- Space: O(h) — the recursion stack: O(log n) for the generator's random trees, O(n) for a path.

### Trade-offs

It is short, uses no extra structures and is the answer interviewers expect, but its correctness argument is subtle (a returned node means different things at different levels) and it recurses. It relies on both nodes being in the tree; when that is not guaranteed, it must also count what it found.

### Pitfalls and edge cases

- Comparing values instead of identities works here only because values are unique; compare nodes.
- Stopping at `p` without searching below is correct: if `q` is below `p`, the answer is `p` anyway.
- A search tree shortcut (comparing values to decide a direction) is wrong here: the tree is not ordered.

### Language notes

- Python: `is` compares identity; `left if left is not None else right` avoids relying on the truthiness of nodes.
- TypeScript: `===` compares object identity, and `left ?? right` returns the non-null result.
- Java: `==` on `TreeNode` references is identity, exactly what the base case needs.
- Kotlin: `===` is reference equality, and `left ?: right` returns the non-null result; parameters are nullable to match the generated stub.
- Go: `root == p` compares pointers, which is identity.
- Rust: `Rc::ptr_eq(a, b)` is the identity test (`==` would compare the values inside). The answer is returned as `root.clone()`, a clone of the matched `Rc`, so the result is the same allocation with only a counter bumped.
