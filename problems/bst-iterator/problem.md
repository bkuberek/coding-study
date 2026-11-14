# BST Iterator

## Statement

Build an iterator over a binary search tree that hands out its values in increasing order, one at a time. The tree's values are distinct; every value in a node's left subtree is smaller than the node's value and every value in its right subtree is larger.

The iterator is created from the root of the tree and starts before the smallest value. Each call to `next` moves to the next value in increasing order and returns it, and `hasNext` reports whether any value is still left, without moving. The iterator only reads the tree; it never needs to change it.

Reference: this is our own wording of LeetCode problem 173, [Binary Search Tree Iterator](https://leetcode.com/problems/binary-search-tree-iterator/).

## Input

- `BSTIterator(root)`: creates an iterator over the tree rooted at `root`, which may be null for an empty tree. Trees are written in level order, top to bottom and left to right, with `null` marking a missing child; trailing `null` entries are omitted.
- `next()`: advances to the next value in increasing order and returns it. It is only called while a value is left.
- `hasNext()`: returns whether a later call to `next` would have a value to return.

Each test case is a sequence of operations: the first creates the iterator, and the following ones call its methods.

## Output

For each operation, its return value: `null` for the constructor, the value returned by `next`, and `true` or `false` for `hasNext`.

## Examples

### Example 1

<!-- case: ex1 -->

The values in increasing order are 2, 5, 7, 10, 14, 18. The calls to `next` return them in that order. `hasNext` is true while values are left and false after 18, and asking it never skips a value.

### Example 2

<!-- case: ex2 -->

A single node: `hasNext` is true until its only value 42 has been returned, then false.

## Constraints

- The tree has between `0` and `10^5` nodes.
- `0 <= node value <= 10^6`; all values are distinct, and the tree is a valid binary search tree.
- The tree has at most `3000` levels.
- `next` is only called when `hasNext` would return true.
- At most `2 * 10^5` calls to `next` and `hasNext` in total.

## Follow-ups

- Can `next` and `hasNext` run in O(1) amortized time while the iterator uses memory proportional to the height of the tree, not to the number of nodes?

## Hints

### Hint 1

An in-order walk of a binary search tree visits the values in increasing order. Copying that walk into a list gives a correct iterator; what does it cost in memory?

### Hint 2

The iterative in-order walk keeps a stack of nodes whose left side has been explored but which have not been visited yet. Pause that walk between calls instead of running it to the end.

### Hint 3

Keep the stack as state: `next` pops a node, then pushes the left spine of that node's right subtree. `hasNext` is simply "the stack is not empty".
