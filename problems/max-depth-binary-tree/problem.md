# Maximum Depth of a Binary Tree

## Statement

You get the root of a binary tree. Report how many levels it has: the number of nodes on the longest downward path that starts at the root and ends at a leaf. A single node is a tree of depth 1, and an empty tree has depth 0.

Only the shape matters. Values play no part in the answer, so two trees with the same arrangement of nodes always have the same depth.

Reference: this is our own wording of LeetCode problem 104, [Maximum Depth of Binary Tree](https://leetcode.com/problems/maximum-depth-of-binary-tree/).

## Input

- `root`: the root of the tree, or null for an empty tree. Trees are written in level order, top to bottom and left to right, with `null` marking a missing child; trailing `null` entries are omitted.

## Output

The number of nodes on a longest root-to-leaf path, or `0` for an empty tree.

## Examples

### Example 1

<!-- case: ex1 -->

The longest path is `5 -> 8 -> 7 -> 6`, four nodes. The other branches stop one or two levels higher.

### Example 2

<!-- case: ex2 -->

Every node has only a right child, so the tree is a single path of three nodes and its depth is 3.

## Constraints

- The tree has between `0` and `10^5` nodes.
- `-10^4 <= node value <= 10^4`; values may repeat.
- The tree has at most `3000` levels.

## Follow-ups

- Can you compute the depth without recursion, so even a path-shaped tree of 10^5 nodes is safe?
- How would you return the minimum depth instead, the shortest path from the root down to a leaf?

## Hints

### Hint 1

The depth of a tree is one more than the depth of its deeper subtree.

### Hint 2

An empty subtree has depth 0, which is the base case that stops the recursion.

### Hint 3

Without recursion, process the tree level by level with a queue and count how many levels you see.
