# Balanced Binary Tree: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| top-down | brute | O(n * h) | O(h) | a first, obviously correct version |
| bottom-up | optimal | O(n) | O(h) | default answer |

`n` is the number of nodes and `h` the height of the tree.

## Approach: top-down (Compare subtree heights at every node)

### Intuition

The definition has two parts: the root's two subtree heights differ by at most one, and both subtrees are balanced themselves. Checking exactly that, with a separate height function, is a correct first answer.

### Algorithm

1. If `root` is null, return true.
2. Compute the heights of `root.left` and `root.right` with a recursive height function.
3. Return true only if they differ by at most one, the left subtree is balanced and the right subtree is balanced (checked recursively, with short-circuiting).

### Correctness

By induction on the height. An empty tree is balanced. A non-empty tree is balanced exactly when its root satisfies the height condition and every node of both subtrees does, which is the conjunction the algorithm evaluates; the recursive calls are correct by the induction hypothesis.

### Complexity

- Time: O(n * h) — the height function walks the whole subtree under each node it is called on, so a node is visited once for every ancestor. On balanced trees (the hard case, because nothing short-circuits) `h` is about log n, which gives O(n log n).
- Space: O(h) — the outer recursion and the height recursion together never go deeper than the tree.

### Trade-offs

It mirrors the definition and is easy to get right, but it recomputes heights. Its short-circuiting makes it fast on trees that are unbalanced near the root, and slowest on trees that really are balanced.

### Pitfalls and edge cases

- Checking only the root: Example 2 has equal heights at the root and is still unbalanced below.
- Comparing the minimum and maximum leaf depth instead of subtree heights is a different (stricter) property and rejects valid balanced trees such as the hidden Fibonacci-shaped cases.
- An empty tree is balanced; an empty subtree has height 0.

### Language notes

- Python: `abs` and short-circuiting `and` keep the condition in one expression.
- TypeScript and Java: `Math.abs` on the height difference; heights are small, so there is no overflow concern.
- Kotlin: `abs` comes from `kotlin.math`, which needs an import.
- Go: the standard library has no integer `abs` (`math.Abs` takes a `float64`), so the height gap is range-checked with `-1 <= gap && gap <= 1`.
- Rust: `(left - right).abs()` is a method on `i32`; heights are small, so the subtraction cannot overflow.

## Approach: bottom-up (Post-order heights with an early exit)

### Intuition

A post-order walk knows both children's heights when it reaches a node, which is exactly what the balance condition needs. Let each call return its subtree's height, or a sentinel `-1` meaning "something below is already unbalanced", and the whole check takes one pass.

### Algorithm

1. Define `checkedHeight(node)`: return 0 for null.
2. Compute `left = checkedHeight(node.left)`; if it is `-1`, return `-1` without visiting the right side.
3. Compute `right = checkedHeight(node.right)`; if it is `-1`, or `|left - right| > 1`, return `-1`.
4. Otherwise return `1 + max(left, right)`.
5. The tree is balanced exactly when `checkedHeight(root)` is not `-1`.

### Correctness

Claim: `checkedHeight(x)` returns `-1` if the subtree at `x` is unbalanced and its height otherwise. By induction: for null it returns 0, the height of an empty balanced tree. For a node, if either child's subtree is unbalanced, so is `x`'s, and the call returns `-1`. If both are balanced, the children return their true heights, and `x`'s subtree is balanced exactly when they differ by at most one, in which case `1 + max(left, right)` is its height. Real heights are never negative, so the sentinel cannot be confused with one.

### Complexity

- Time: O(n) — each node is visited at most once, and the walk stops early on the first unbalanced subtree.
- Space: O(h) — the recursion stack: O(log n) for balanced trees, O(n) for a path.

### Trade-offs

One pass and no repeated work, with the same amount of code as the brute force. Packing "balanced?" and "height" into one integer is a small trick worth explaining in an interview; returning a pair is the more explicit alternative.

### Pitfalls and edge cases

- Forgetting to propagate the sentinel: if a child returns `-1` and the parent computes `1 + max(-1, x)`, the failure disappears.
- Checking the right child before testing the left result wastes the early exit, but stays correct.
- Deep trees: the hidden path of 2000 nodes exercises the recursion. Its first unbalanced node is the third from the bottom, so the walk goes all the way down before the sentinel travels back up.

### Language notes

- Python: a module-level `UNBALANCED` constant documents the sentinel.
- TypeScript: compare with `===` against the constant.
- Java: a `private static final int` constant; all arithmetic stays in `int`.
- Kotlin: the constant lives in a `companion object` as `const val`, and `abs` is imported from `kotlin.math`.
- Go: a `const unbalanced = -1` plays the sentinel, and the gap check is written as two comparisons because there is no integer `abs`.
- Rust: `Option<i32>` replaces the sentinel: `None` means unbalanced, and `?` returns it from the enclosing call at once, which is the early exit of the Python version, so no constant is needed.
