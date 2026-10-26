# Vertical Order Traversal

## Statement

You get the root of a binary tree. Give every node a column: the root is in column 0, a left child is one column to the left of its parent, and a right child is one column to the right. Report the values column by column, from the leftmost column to the rightmost.

Inside a column, list the nodes from the top of the tree down. When two nodes of the same column are on the same level, list them in the order they appear on that level from left to right, which is the order of a level-order (breadth-first) walk.

Reference: this is our own wording of LeetCode problem 314, [Binary Tree Vertical Order Traversal](https://leetcode.com/problems/binary-tree-vertical-order-traversal/).

## Input

- `root`: the root of the tree, or null for an empty tree. Trees are written in level order, top to bottom and left to right, with `null` marking a missing child; trailing `null` entries are omitted.

## Output

One list per column, from the leftmost column to the rightmost. Each list holds the values of that column, top to bottom, with nodes on the same level in left-to-right order. An empty tree gives an empty list.

## Examples

### Example 1

<!-- case: ex1 -->

The columns run from -2 to 2. Column 0 holds the root 4 and, two levels down, both 3 (the right child of 2) and 5 (the left child of 6). They share a level, so 3 comes before 5, as it does from left to right.

### Example 2

<!-- case: ex2 -->

Node 4 is the right child of 2, so it returns to column 0 below the root; its children 5 and 6 land in columns -1 and 1, below 2 and 3. Every column lists its nodes from the top down.

## Constraints

- The tree has between `0` and `10^5` nodes.
- `-10^4 <= node value <= 10^4`; values may repeat.
- The tree has at most `3000` levels.

## Follow-ups

- Can you produce the columns in one pass without sorting, given that the columns form a contiguous range?
- How would the answer change if nodes on the same level and column had to be sorted by value instead?

## Hints

### Hint 1

Record each node's column along with its value. A map from column to list of values collects the groups.

### Hint 2

A breadth-first walk reaches nodes level by level and, within a level, from left to right, which is exactly the order required inside each column.

### Hint 3

The columns that occur are every integer from the smallest to the largest one seen, so tracking those two numbers lets you emit the columns without sorting the keys.
