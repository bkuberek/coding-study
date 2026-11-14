# Subtree of Another Tree

## Statement

You get the roots of two non-empty binary trees, `root` and `subRoot`. Decide whether `subRoot` appears inside `root` as a complete subtree: there must be a node in `root` such that that node together with every one of its descendants forms exactly the tree `subRoot`, with the same shape and the same values in the same positions.

The match has to be complete. Finding the values of `subRoot` near the top of some node is not enough if that node has extra descendants that `subRoot` does not have. The whole of `root` also counts as one of its own subtrees.

Reference: this is our own wording of LeetCode problem 572, [Subtree of Another Tree](https://leetcode.com/problems/subtree-of-another-tree/).

## Input

- `root`: the root of the tree to search in.
- `subRoot`: the root of the tree to look for.

Trees are written in level order, top to bottom and left to right, with `null` marking a missing child; trailing `null` entries are omitted.

## Output

`true` when some node of `root` is the root of a subtree identical to `subRoot`, otherwise `false`.

## Examples

### Example 1

<!-- case: ex1 -->

The left child of the root is 3, with children 1 and 6 and nothing below them. That subtree is exactly `subRoot`.

### Example 2

<!-- case: ex2 -->

The node 3 still has children 1 and 6, but now 6 has a child 4. The subtree rooted at 3 has four nodes and `subRoot` has three, so it does not match, and no other node of `root` has the value 3.

## Constraints

- `root` has between `1` and `10^5` nodes; `subRoot` has between `1` and `10^5` nodes.
- `-10^4 <= node value <= 10^4`; values may repeat in both trees.
- Each tree has at most `3000` levels.

## Follow-ups

- The direct approach can compare `subRoot` against almost all of `root` many times when values repeat a lot. Can you decide in time linear in the sizes of both trees?
- How would you count the number of nodes of `root` whose subtree equals `subRoot`?

## Hints

### Hint 1

If you can decide whether two trees are the same, try that test at every node of `root`.

### Hint 2

A pre-order walk that also writes down every missing child describes a tree uniquely, and the walk of any subtree is one contiguous block of the walk of the whole tree.

### Hint 3

With both trees written as token sequences, the question becomes whether one sequence occurs inside the other, which a linear-time string matching algorithm such as KMP answers. Compare tokens, not characters, so the value 2 never matches inside 12.
