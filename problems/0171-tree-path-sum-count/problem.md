# Count Downward Path Sums

## Statement

You get the root of a binary tree whose nodes hold integers, and an integer `targetSum`. Count the downward paths whose values add up to `targetSum`.

A downward path starts at any node and moves only from a parent to one of its children, stopping at any node below it (or at the start itself). It does not have to start at the root or end at a leaf. Two paths are different when they start or end at different nodes.

Reference: this is our own wording of LeetCode problem 437, [Path Sum III](https://leetcode.com/problems/path-sum-iii/).

## Input

- `root`: the root of the tree, in level-order encoding (`null` marks a missing child); `[]` is the empty tree
- `targetSum`: the required sum

## Output

The number of downward paths whose node values add up to `targetSum`.

## Examples

### Example 1

<!-- case: ex1 -->

The tree is

```text
      4
     / \
    2   -1
   / \    \
  3   1    5
```

Three downward paths add up to 3: the single node 3, the path 2 to 1, and the path 4 to -1. The path 4, -1, 5 adds up to 8 and does not count.

### Example 2

<!-- case: ex2 -->

The tree is a chain of three zeros. Every downward path adds up to 0: three single nodes, two paths of two nodes and one path of three, so the answer is 6.

## Constraints

- The tree has between `0` and `3000` nodes.
- `-1000 <= node value <= 1000`
- `-10^6 <= targetSum <= 10^6`

## Follow-ups

- Walking down from every node costs O(n * h), which is O(n^2) on a path-shaped tree. Can you count all paths in one traversal?
- How does this relate to counting subarrays with a given sum?
- What changes if paths may also go up and turn (any path between two nodes)?

## Hints

### Hint 1

Look at a single root-to-node path: it is an array, and a downward path ending at the current node is a suffix of that array.

### Hint 2

A suffix adds up to `targetSum` when the prefix sum at the current node minus an earlier prefix sum on the same root path equals `targetSum`.

### Hint 3

During a depth-first traversal, keep a hash map of the prefix sums on the current root path. Add the current sum before visiting the children and remove it when you return, so sibling subtrees never see each other's sums.
