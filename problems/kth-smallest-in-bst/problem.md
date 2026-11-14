# Kth Smallest in a BST

## Statement

You get the root of a binary search tree and a number `k`. All values in the tree are distinct, every value in a node's left subtree is smaller than the node's value, and every value in its right subtree is larger. Return the `k`-th smallest value in the tree, counting from 1: `k = 1` asks for the minimum and `k` equal to the number of nodes asks for the maximum.

Reference: this is our own wording of LeetCode problem 230, [Kth Smallest Element in a BST](https://leetcode.com/problems/kth-smallest-element-in-a-bst/).

## Input

- `root`: the root of a non-empty binary search tree. Trees are written in level order, top to bottom and left to right, with `null` marking a missing child; trailing `null` entries are omitted.
- `k`: the rank of the value to return, `1`-based.

## Output

The value that would be at position `k` if all values of the tree were listed in increasing order.

## Examples

### Example 1

<!-- case: ex1 -->

In increasing order the values are 20, 30, 40, 50, 60, 70, 80. The third one is 40.

### Example 2

<!-- case: ex2 -->

In increasing order the values are 1, 2, 3, 4, 5, 9, 12, so the sixth smallest is 9, the right child of the root.

## Constraints

- The tree has between `1` and `10^5` nodes, `n` in total.
- `1 <= k <= n`.
- `-10^9 <= node value <= 10^9`; all values are distinct, and the tree is a valid binary search tree.
- The tree has at most `3000` levels.

## Follow-ups

- Can you stop as soon as you reach the `k`-th value, without visiting the rest of the tree?
- If the tree changed often (inserts and deletes) and the `k`-th smallest were asked often, what would you store in each node to answer in time proportional to the height?

## Hints

### Hint 1

Which traversal of a binary search tree visits the values in increasing order?

### Hint 2

An in-order walk (left subtree, node, right subtree) produces the sorted order. Count the nodes as you visit them.

### Hint 3

With an explicit stack, the in-order walk can stop the moment the counter reaches `k`, after touching only the path down to the minimum plus the first `k` nodes.
