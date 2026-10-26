# Right Side View

## Statement

You get the root of a binary tree. Imagine standing to the right of the tree and looking at it level by level: on each level you see only the rightmost node, and every other node of that level is hidden behind it. Return the values you see, from the top level to the bottom one.

The visible node of a level is not always a right child. When the right part of the tree is shallower, the view on the lower levels comes from nodes on the left side.

Reference: this is our own wording of LeetCode problem 199, [Binary Tree Right Side View](https://leetcode.com/problems/binary-tree-right-side-view/).

## Input

- `root`: the root of the tree, or null for an empty tree. Trees are written in level order, top to bottom and left to right, with `null` marking a missing child; trailing `null` entries are omitted.

## Output

The value of the rightmost node of every level, from the top level down. An empty tree gives an empty list.

## Examples

### Example 1

<!-- case: ex1 -->

The levels are `8`, then `3, 10`, then `1, 6, 14`. The rightmost nodes are 8, 10 and 14.

### Example 2

<!-- case: ex2 -->

The right side of the tree stops after the second level. On the third and fourth levels the only nodes are 4 and 7 under the left child, so they are the ones you see.

## Constraints

- The tree has between `0` and `10^5` nodes.
- `-10^4 <= node value <= 10^4`; values may repeat.
- The tree has at most `3000` levels.

## Follow-ups

- How would you return the left side view instead?
- Can you solve it with a depth-first walk and memory proportional to the height?

## Hints

### Hint 1

Walk the tree level by level; the answer for a level is its last node.

### Hint 2

In a depth-first walk that visits the right child before the left one, the first node you reach on each depth is the rightmost node of that level.

### Hint 3

With that walk, a node belongs in the answer exactly when its depth equals the number of values collected so far.
