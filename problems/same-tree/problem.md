# Same Tree

## Statement

You get the roots of two binary trees, `p` and `q`. Decide whether they are the same tree: identical in shape, with equal values in matching positions. Two empty trees are the same; an empty tree and a non-empty one are not.

Matching positions means the same sequence of left and right steps from the root. A tree and its mirror image are therefore different unless the tree is symmetric, and two trees that hold the same values in a different arrangement are different too.

Reference: this is our own wording of LeetCode problem 100, [Same Tree](https://leetcode.com/problems/same-tree/).

## Input

- `p`: the root of the first tree, or null for an empty tree.
- `q`: the root of the second tree, or null for an empty tree.

Trees are written in level order, top to bottom and left to right, with `null` marking a missing child; trailing `null` entries are omitted.

## Output

`true` when the two trees have the same shape and the same value at every position, otherwise `false`.

## Examples

### Example 1

<!-- case: ex1 -->

Both trees have root 6 with children 4 and 9, and 9 has a right child 12 in both. Every position matches.

### Example 2

<!-- case: ex2 -->

Both trees hold the values 5 and 8, but in `p` the 8 is a left child and in `q` it is a right child, so the shapes differ.

## Constraints

- Each tree has between `0` and `10^5` nodes.
- `-10^4 <= node value <= 10^4`; values may repeat.
- Each tree has at most `3000` levels.

## Follow-ups

- Can you stop as soon as the first difference appears, without visiting the rest of either tree?
- How would you instead decide whether one tree is the mirror image of the other?

## Hints

### Hint 1

Two trees are the same exactly when their roots match and their left subtrees are the same and their right subtrees are the same.

### Hint 2

Settle the null cases first: both null means a match, exactly one null means a mismatch.

### Hint 3

Without recursion, keep a stack of pairs `(node from p, node from q)` that still need comparing.
