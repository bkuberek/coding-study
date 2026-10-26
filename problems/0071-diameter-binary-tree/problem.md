# Diameter of a Binary Tree

## Statement

You get the root of a non-empty binary tree. A path in the tree is a sequence of nodes in which every two consecutive nodes are parent and child, and no node appears twice. Its length is the number of edges it uses, one fewer than the number of nodes.

Return the diameter of the tree: the length of the longest path between any two nodes. The longest path may pass through the root, but it does not have to; it can live entirely inside one subtree.

Reference: this is our own wording of LeetCode problem 543, [Diameter of Binary Tree](https://leetcode.com/problems/diameter-of-binary-tree/).

## Input

- `root`: the root of the tree. Trees are written in level order, top to bottom and left to right, with `null` marking a missing child; trailing `null` entries are omitted.

## Output

The number of edges on a longest path between two nodes of the tree. A single node gives `0`.

## Examples

### Example 1

<!-- case: ex1 -->

The longest path is `6 -> 7 -> 4 -> 10 -> 15 -> 20`: it climbs from the deepest node on the left up to the root and goes down the right side, using 5 edges.

### Example 2

<!-- case: ex2 -->

The root 1 has only a left child. The longest path, `7 -> 5 -> 3 -> 2 -> 4 -> 6 -> 8`, turns at node 2 and never reaches the root; it has 6 edges, while the best path through the root has only 4.

## Constraints

- The tree has between `1` and `10^5` nodes.
- `-10^4 <= node value <= 10^4`; values may repeat.
- The tree has at most `3000` levels.

## Follow-ups

- Recomputing heights for every node repeats a lot of work. Can you find the diameter while visiting each node once?
- How would you return the two endpoints of a longest path instead of its length?

## Hints

### Hint 1

Every path has one highest node, where it turns. What is the longest path that turns at a given node?

### Hint 2

The longest path turning at a node goes as deep as possible into its left subtree and as deep as possible into its right subtree, so its length is the sum of the two subtree heights.

### Hint 3

A post-order walk can return each subtree's height to its parent and, on the way, keep the best sum of two heights seen so far.
