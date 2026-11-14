# Level Order Traversal

## Statement

You get the root of a binary tree. List its values level by level: first the root, then all nodes one step below it, then all nodes two steps below, and so on. Within a level, list the values from left to right as they would appear in a drawing of the tree.

Return one list per level, from the top level down. An empty tree has no levels.

Reference: this is our own wording of LeetCode problem 102, [Binary Tree Level Order Traversal](https://leetcode.com/problems/binary-tree-level-order-traversal/).

## Input

- `root`: the root of the tree, or null for an empty tree. Trees are written in level order, top to bottom and left to right, with `null` marking a missing child; trailing `null` entries are omitted.

## Output

A list of levels, top to bottom; each level is the list of its values from left to right. An empty tree gives an empty list.

## Examples

### Example 1

<!-- case: ex1 -->

The root 6 is alone on the first level. Its children 2 and 9 form the second level. The third level holds 4 (the right child of 2) and then 7 and 12 (the children of 9). The last level holds 3, the left child of 4.

### Example 2

<!-- case: ex2 -->

Equal values stay separate entries: the second level holds two nodes with value 5. Each 5 has only a right child, and the missing left children leave no gaps: the third level is just `0, 8`.

## Constraints

- The tree has between `0` and `10^5` nodes.
- `-10^4 <= node value <= 10^4`; values may repeat.
- The tree has at most `3000` levels.

## Follow-ups

- Can you produce the levels bottom-up instead, or alternate left-to-right and right-to-left on every other level?
- Can you do it with a depth-first walk, without a queue?

## Hints

### Hint 1

A queue visits nodes in exactly the order the output needs: everything on one level before anything on the next.

### Hint 2

To know where one level ends, read the queue's size before you start removing that level's nodes.

### Hint 3

A depth-first walk works too if you pass the depth along and append each value to the list for its depth; a pre-order walk that goes left before right keeps every level in left-to-right order.
