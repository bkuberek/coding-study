# Invert Binary Tree

## Statement

You get the root of a binary tree. Turn the tree into its mirror image: at every node, the left subtree and the right subtree trade places. Return the root of the mirrored tree.

Picture holding the tree up to a mirror. A node that was the leftmost leaf becomes the rightmost one, and every parent keeps the same children, just on the opposite sides. Node values never change; only the links between nodes do. You may rearrange the given nodes in place or build new ones.

Reference: this is our own wording of LeetCode problem 226, [Invert Binary Tree](https://leetcode.com/problems/invert-binary-tree/).

## Input

- `root`: the root of the tree, or null for an empty tree. Trees are written in level order, top to bottom and left to right, with `null` marking a missing child; trailing `null` entries are omitted.

## Output

The root of the mirrored tree, written in the same level-order form. An empty tree stays empty.

## Examples

### Example 1

<!-- case: ex1 -->

Every level is read in reverse after mirroring: the second level `2, 9` becomes `9, 2`, and the third level `1, 4, 7, 12` becomes `12, 7, 4, 1`.

### Example 2

<!-- case: ex2 -->

Node 1 was the left child of 3 and becomes its right child. Node 2 was the right child of 1 and becomes its left child, so the root now has no left child, written as `null`.

## Constraints

- The tree has between `0` and `10^5` nodes.
- `-10^4 <= node value <= 10^4`; values may repeat.
- The tree has at most `3000` levels.

## Follow-ups

- Solve it without recursion, so a tree that is a single path of 10^5 nodes cannot overflow the call stack.
- How would you check whether a tree is symmetric, that is, equal to its own mirror, without modifying it?
- Can you build a mirrored copy instead and leave the input tree untouched? What does that cost in memory?

## Hints

### Hint 1

Mirroring the whole tree means mirroring each subtree and then putting the two results on opposite sides.

### Hint 2

The order of visits does not matter: every node needs exactly one swap of its two child links, whether you go top-down, bottom-up or level by level.

### Hint 3

For an iterative version, keep a queue (or stack) of nodes still to swap. Swap a node's children, then add the non-null children to the queue.
