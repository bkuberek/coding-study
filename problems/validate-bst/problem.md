# Validate a Binary Search Tree

## Statement

You get the root of a binary tree of integers. Decide whether it is a valid binary search tree. In a valid binary search tree, for every node:

- every value in its left subtree is strictly smaller than the node's value;
- every value in its right subtree is strictly larger than the node's value.

The rule is about whole subtrees, not just children: a node deep in the left subtree of the root must still be smaller than the root. Because both comparisons are strict, a tree that contains the same value twice is never valid. An empty tree is valid.

Reference: this is our own wording of LeetCode problem 98, [Validate Binary Search Tree](https://leetcode.com/problems/validate-binary-search-tree/).

## Input

- `root`: the root of the tree, or null for an empty tree. Trees are written in level order, top to bottom and left to right, with `null` marking a missing child; trailing `null` entries are omitted.

## Output

`true` when every node is larger than everything in its left subtree and smaller than everything in its right subtree, otherwise `false`.

## Examples

### Example 1

<!-- case: ex1 -->

Each node sits between the values above it that bound it: 15 is larger than its parent 10 and smaller than the root 20, and the same holds on the right side.

### Example 2

<!-- case: ex2 -->

Node 25 is the right child of 10, and 25 > 10 is fine locally. But 25 is in the left subtree of the root 20, where every value must be smaller than 20, so the tree is not a binary search tree.

## Constraints

- The tree has between `0` and `10^5` nodes.
- `-2^31 <= node value <= 2^31 - 1`.
- The tree has at most `3000` levels.

## Follow-ups

- Can you decide in one pass over the tree, visiting each node once?
- Can you do it without recursion?

## Hints

### Hint 1

Checking each node against its two children is not enough; Example 2 passes that test. What range of values is allowed at each position?

### Hint 2

The root may hold anything. Going left tightens the upper bound to the parent's value, going right tightens the lower bound. Pass the open interval down the recursion.

### Hint 3

Alternatively, an in-order walk of a binary search tree visits the values in sorted order. The tree is valid exactly when that sequence is strictly increasing. Watch out for bounds stored in a type that cannot go beyond the smallest and largest values.
