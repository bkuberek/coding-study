# Binary Tree Maximum Path Sum

## Statement

You get the root of a non-empty binary tree whose nodes hold integers, possibly negative. A path is a sequence of at least one node in which every two consecutive nodes are parent and child and no node appears twice. A path can start and end anywhere; it does not need to include the root or a leaf. Its sum is the total of its values.

Return the largest sum of any path. Since a path may consist of a single node, the answer is at least the largest value in the tree, even when every value is negative.

Reference: this is our own wording of LeetCode problem 124, [Binary Tree Maximum Path Sum](https://leetcode.com/problems/binary-tree-maximum-path-sum/).

## Input

- `root`: the root of the tree. Trees are written in level order, top to bottom and left to right, with `null` marking a missing child; trailing `null` entries are omitted.

## Output

The largest sum over all non-empty paths of the tree.

## Examples

### Example 1

<!-- case: ex1 -->

The best path is `2 -> 5 -> 3` with sum 10. Going into the left subtree would only lower it: the best path down from -6 is `-6 -> 4`, worth -2.

### Example 2

<!-- case: ex2 -->

Every value is negative, so any longer path only adds losses. The best path is the single node -2.

## Constraints

- The tree has between `1` and `10^5` nodes.
- `-1000 <= node value <= 1000`.
- The tree has at most `3000` levels.

## Follow-ups

- Can you find the answer while visiting each node once?
- How would you return the path itself, not only its sum?

## Hints

### Hint 1

Every path has one highest node. Fix that node: the best path through it goes down at most once into each subtree.

### Hint 2

For each node, the best "downward" path that starts at it and goes only down is its value plus the better of its children's downward paths, or nothing if both are negative.

### Hint 3

Compute downward gains in a post-order walk. At each node, `value + max(0, left gain) + max(0, right gain)` is the best path turning there; keep the maximum of these, and return `value + max(0, left gain, right gain)` to the parent.
