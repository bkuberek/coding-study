# Validate a Binary Search Tree: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| subtree-extremes | brute | O(n * h) | O(h) | a direct translation of the definition |
| bounds | optimal | O(n) | O(h) | default answer |
| inorder | optimal | O(n) | O(h) | an iterative answer, or when the sorted-order view is more natural |

`n` is the number of nodes and `h` the height of the tree.

## Approach: subtree-extremes (Compare every node with the extremes of its subtrees)

### Intuition

The definition says every value on the left is smaller and every value on the right is larger. Those conditions are the same as "the largest value on the left is smaller and the smallest value on the right is larger". Compute those extremes for every node and check.

### Algorithm

1. If `root` is null, return true.
2. If the left subtree exists and its largest value is at least `root.val`, return false.
3. If the right subtree exists and its smallest value is at most `root.val`, return false.
4. Return whether both subtrees are valid, recursively.

### Correctness

A node satisfies the search-tree condition exactly when the maximum of its left subtree is below its value and the minimum of its right subtree is above it. The extremes are computed by scanning the whole subtree, because a subtree that is not itself a search tree can hide its largest value anywhere. The recursion applies the check to every node, and the tree is valid exactly when every node passes.

### Complexity

- Time: O(n * h) — the extreme scans visit each node once for every ancestor, which is O(n log n) for the generator's random trees and O(n^2) for a path.
- Space: O(h) — the recursion depth of the check plus that of a scan never exceeds the height.

### Trade-offs

It mirrors the definition and is the safest first step towards the efficient answers, but it repeats work for every ancestor. On a 2000-node path it already does about two million steps.

### Pitfalls and edge cases

- Checking only the children (`left.val < node.val < right.val`) is the classic mistake; Example 2 passes that check and is invalid.
- Looking only at the rightmost path of the left subtree for its maximum assumes the subtree is already valid, which is what is being tested.
- Duplicates are invalid on either side because both comparisons are strict.

### Language notes

- Python: `max` and `min` over the children that exist avoid sentinels.
- TypeScript: `-Infinity` and `Infinity` are safe neutral values for `Math.max` and `Math.min`.
- Java: the helpers are only called on non-null nodes, so no sentinel is needed.
- Kotlin: `node.left?.let(::largest) ?: Int.MIN_VALUE` uses the extreme `Int` as a neutral element; that is safe here because it only enters a `maxOf` together with the node's own value.
- Rust: `largest` and `smallest` return `Option<i32>`, `None` for an empty subtree, so the caller writes `largest(&node.left).is_some_and(|value| value >= node.val)` and needs no separate null check; each combines its children with `filter_map(..).max()`.

## Approach: bounds (Pass down the open interval each node must lie in)

### Intuition

Every position in a binary search tree has an allowed open interval. The root may hold anything. Its left child must be below the root, so its interval is (−∞, root). Going right from there adds a lower bound, and so on: each step down replaces one end of the interval with the parent's value. Checking every node against its interval checks every ancestor relation at once.

### Algorithm

1. Call `within(root, −∞, +∞)`.
2. In `within(node, low, high)`: return true for null; return false if `node.val <= low` or `node.val >= high`.
3. Return `within(node.left, low, node.val)` and `within(node.right, node.val, high)`.

### Correctness

Claim: `within(x, low, high)` is true exactly when the subtree at `x` is a search tree whose values all lie strictly between `low` and `high`. By induction: the empty tree qualifies. A non-empty subtree qualifies exactly when its root is strictly inside the interval, its left subtree is a search tree inside (low, x.val) and its right subtree is a search tree inside (x.val, high), which is what the recursive calls check. With the unbounded interval at the root, the claim is exactly validity.

### Complexity

- Time: O(n) — every node is checked once against two bounds.
- Space: O(h) — the recursion stack.

### Trade-offs

One pass, short code and an argument that is easy to state in an interview. It is the expected answer. It does recurse, so the iterative in-order walk is the alternative when depth is a concern.

### Pitfalls and edge cases

- Sentinels: starting with the smallest and largest 32-bit integers as bounds wrongly rejects a node whose value is exactly one of them. The hidden cases put `-2^31` and `2^31 - 1` in the tree. Use unbounded markers (Python `None`, TypeScript infinities) or a wider type (Java and Kotlin `long`).
- Pass the parent's value as the new bound, not the child's: the left call gets `(low, node.val)`.
- Equal values must fail: compare with `<=` and `>=`.

### Language notes

- Python: integers are unbounded, but `None` for "no bound" keeps the intent clear.
- TypeScript: `number` holds every 32-bit value exactly, so `-Infinity` and `Infinity` are safe bounds.
- Java: `long` bounds starting at `Long.MIN_VALUE` and `Long.MAX_VALUE` lie strictly outside the `int` range; `node.val` widens automatically in the comparisons.
- Kotlin: the same `Long` bounds, with an explicit `toLong()` because Kotlin never widens implicitly.
- Go: `*int` stands for Python's `int | None`, and `&node.Val` points at the node's own field, so passing a bound allocates nothing.
- Rust: `Option<i32>` is `Copy`, so the bounds travel by value; `low.is_some_and(|low| node.val <= low)` is `low is not None and node.val <= low`.

## Approach: inorder (In-order walk that must strictly increase)

### Intuition

An in-order walk (left subtree, node, right subtree) of a binary search tree lists its values in sorted order, and the converse holds too. So the tree is valid exactly when the in-order sequence is strictly increasing, which can be checked by remembering only the previous value. An explicit stack makes the walk iterative.

### Algorithm

1. Start with an empty stack, `node = root` and no previous value.
2. While the stack is not empty or `node` is not null:
   1. Push `node` and move to its left child until `node` is null.
   2. Pop a node. If a previous value exists and the node's value is not larger, return false.
   3. Record its value as the previous value and move to its right child.
3. Return true.

### Correctness

The loop is the standard iterative in-order walk: a node is popped only after its whole left subtree, and its right subtree is walked right after it. A binary tree is a search tree if and only if its in-order sequence is strictly increasing: if it is a search tree, everything before a node in in-order order is in its left subtree or in the left part of an ancestor, hence smaller, and similarly for later values; conversely, if the tree is not a search tree, some node has a left-subtree value at least as large (or a right-subtree value at most as large), and that pair appears in the wrong order in the sequence. Comparing consecutive values suffices because strict increase is a property of adjacent pairs.

### Complexity

- Time: O(n) — every node is pushed and popped once, and the walk stops at the first violation.
- Space: O(h) — the stack holds the path of pending ancestors.

### Trade-offs

It needs no bounds at all, only the previous value, and its iterative form has no recursion limit. The equivalence with sorted order deserves a sentence of justification in an interview; the interval version is easier to argue from the definition.

### Pitfalls and edge cases

- Using `<` instead of `<=` in the violation test accepts duplicates.
- The first value has no predecessor; a sentinel equal to the smallest `int` would reject a leftmost node of value `-2^31`. The references use `None`, `-Infinity` or a `long` below every `int`.
- Collecting the whole sequence first and then checking works but stores O(n) values and gives up the early exit.

### Language notes

- Python: `previous: int | None` starts as `None`, and a list is the stack.
- TypeScript: `-Infinity` is below every value; `pop()!` asserts the stack is non-empty inside the loop.
- Java: `ArrayDeque` as a stack (`push`, `pop`) and a `long previous` starting at `Long.MIN_VALUE`.
- Kotlin: `ArrayDeque` with `addLast` and `removeLast`; the `Int` value is compared with the `Long` previous directly, and stored with `toLong()`.
- Go: with no optional integer, `previous` is paired with a `hasPrevious` flag.
- Rust: `previous` is an `Option<i32>` tested with `is_some_and`. The left-spine loop clones the child `Rc` out of the `borrow()` guard (`node = current.borrow().left.clone()`) before it pushes `current`, so the guard is gone before `current` moves.
