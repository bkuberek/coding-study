# Tree From Preorder and Inorder

## Statement

A binary tree with distinct values was walked twice. The pre-order walk lists a node, then everything in its left subtree, then everything in its right subtree. The in-order walk lists everything in a node's left subtree, then the node, then everything in its right subtree. You get both lists, `preorder` and `inorder`. Rebuild the tree and return its root.

Because the values are distinct, the two walks together describe exactly one tree. The tree is an ordinary binary tree, not a search tree, so the values themselves say nothing about the shape.

Reference: this is our own wording of LeetCode problem 105, [Construct Binary Tree from Preorder and Inorder Traversal](https://leetcode.com/problems/construct-binary-tree-from-preorder-and-inorder-traversal/).

## Input

- `preorder`: the values in pre-order (node, left subtree, right subtree).
- `inorder`: the same values in in-order (left subtree, node, right subtree).

## Output

The root of the rebuilt tree, written in level order, top to bottom and left to right, with `null` marking a missing child and trailing `null` entries omitted. Empty lists give an empty tree.

## Examples

### Example 1

<!-- case: ex1 -->

The first pre-order value, 8, is the root. In the in-order list, 1, 3 and 6 come before 8, so they form the left subtree, and 10 and 14 form the right one. Repeating the split inside each part gives 3 with children 1 and 6, and 10 with a right child 14.

### Example 2

<!-- case: ex2 -->

The root is 4, and only 9 comes before it in the in-order list, so 9 is the whole left subtree. On the right, the pre-order part is `2, 7` and the in-order part is `7, 2`: 2 is the root of that part and 7 is its left child.

## Constraints

- `0 <= preorder.length == inorder.length <= 10^5`.
- `-10^9 <= value <= 10^9`; all values are distinct.
- `inorder` holds the same values as `preorder`, and both come from walks of one tree with at most `3000` levels.

## Follow-ups

- Finding each root in the in-order list by scanning costs O(n) per node. How can you find it in O(1)?
- Could you rebuild the tree from its post-order and in-order walks instead? From pre-order and post-order alone?

## Hints

### Hint 1

The first value of `preorder` is the root. Where is it in `inorder`, and what is to its left and to its right?

### Hint 2

Once you know the size of the left subtree, you know which slice of `preorder` belongs to it: the values right after the root. Recurse on both parts.

### Hint 3

Store each value's position in `inorder` in a hash map, and instead of slicing `preorder`, consume it from left to right with one shared cursor: the pre-order walk visits roots in exactly the order the recursion needs them.
