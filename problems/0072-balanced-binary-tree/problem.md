# Balanced Binary Tree

## Statement

You get the root of a binary tree. Decide whether it is height-balanced: at every node, the heights of the left subtree and the right subtree differ by at most one. The height of a tree is the number of nodes on its longest downward path from the root, and an empty tree has height 0.

The condition must hold at every node, not only at the root. A tree whose two halves have equal heights can still be unbalanced deep inside one of them. An empty tree is balanced.

Reference: this is our own wording of LeetCode problem 110, [Balanced Binary Tree](https://leetcode.com/problems/balanced-binary-tree/).

## Input

- `root`: the root of the tree, or null for an empty tree. Trees are written in level order, top to bottom and left to right, with `null` marking a missing child; trailing `null` entries are omitted.

## Output

`true` when the subtree heights differ by at most one at every node, otherwise `false`.

## Examples

### Example 1

<!-- case: ex1 -->

Both subtrees of the root have height 2, and below them the largest difference is at node 12, whose left side is empty (height 0) and whose right side is one leaf (height 1). Every difference is at most one.

### Example 2

<!-- case: ex2 -->

At the root the two sides both have height 3, so the root is fine. Node 2, however, has a left subtree of height 2 (`4 -> 6`) and no right child, a difference of two.

## Constraints

- The tree has between `0` and `10^5` nodes.
- `-10^4 <= node value <= 10^4`; values may repeat.
- The tree has at most `3000` levels.

## Follow-ups

- The direct approach computes the height of the same subtree once for every ancestor. Can you decide while visiting each node once?
- Can you stop as soon as the first unbalanced node is found?

## Hints

### Hint 1

Write a height function first. A node is fine when the heights of its two children differ by at most one; the tree is balanced when every node is fine.

### Hint 2

Calling the height function at every node repeats work. Let one post-order walk return the height of each subtree to its parent.

### Hint 3

Use a special return value, such as `-1`, to mean "this subtree is already unbalanced", and pass it straight up without looking at the rest of the tree.
