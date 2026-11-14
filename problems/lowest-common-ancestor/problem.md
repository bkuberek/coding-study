# Lowest Common Ancestor

## Statement

You get the root of a binary tree and two of its nodes, `p` and `q`. Find their lowest common ancestor: the deepest node of the tree that has both `p` and `q` in its subtree. A node counts as part of its own subtree, so when `p` is an ancestor of `q`, the answer is `p` itself, and when `p` and `q` are the same node, the answer is that node.

The tree is an ordinary binary tree, not a search tree: its values follow no order, so you cannot decide which way to go by comparing values. Return the node itself, not a copy.

Reference: this is our own wording of LeetCode problem 236, [Lowest Common Ancestor of a Binary Tree](https://leetcode.com/problems/lowest-common-ancestor-of-a-binary-tree/).

## Input

- `root`: the root of the tree. Trees are written in level order, top to bottom and left to right, with `null` marking a missing child; trailing `null` entries are omitted.
- `p`: a node of the tree. In the test data it is written as its value; since all values are distinct, the value identifies one node, and your function receives that node of `root`.
- `q`: another node of the tree, written the same way; it may be the same node as `p`.

## Output

The lowest common ancestor of `p` and `q`, which must be a node of `root`. The test data shows it by its value.

## Examples

### Example 1

<!-- case: ex1 -->

Node 1 is in the left subtree of 4 and node 9 in its right subtree (under 7). No node below 4 holds both, so 4 is the lowest common ancestor.

### Example 2

<!-- case: ex2 -->

Node 6 is the left child of 7, so 7 already has both nodes in its subtree: a node is a common ancestor of itself and its descendants.

## Constraints

- The tree has between `1` and `10^5` nodes.
- `-10^9 <= node value <= 10^9`; all values are distinct.
- `p` and `q` are nodes of the tree; they may be the same node.
- The tree has at most `3000` levels.

## Follow-ups

- If the tree were a binary search tree, how could you find the answer by walking down a single path?
- How would you answer many queries on the same tree quickly?

## Hints

### Hint 1

Write down the path from the root to `p` and the path from the root to `q`. Where do the two paths part?

### Hint 2

Without storing paths: ask each subtree whether it contains `p` or `q`. The answer is the first node, seen from below, where the two are found on different sides, or where the node itself is one of them and the other is below it.

### Hint 3

A recursive search that returns `p` or `q` when it meets one, null when its subtree holds neither, and the current node when both sides return something, does all of this in one pass.
