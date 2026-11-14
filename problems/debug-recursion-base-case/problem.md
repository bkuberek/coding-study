# Debug: Recursion Base Case

## Statement

The function `hasPathSum` you start from should report whether a binary tree has a **root-to-leaf** path whose node values add up to `target`. A path starts at the root and ends at a leaf, a node with no children. An empty tree has no paths, so the answer is `false` for every `target`.

The code is a short recursion that passes many tests. It fails others. Find the input class that breaks it, fix the base case, and keep the recursion.

### Bug report

> **Title:** Budget check approves plans that stop halfway
>
> The planning tool stores a project's cost breakdown as a tree. Each node is a cost item, and a complete plan is a path from the project root down to a leaf task. `hasPathSum` checks whether some complete plan costs exactly the approved budget. Finance found approvals for budgets that no complete plan matches: for a project costing 1 with a single sub-task costing 2, a budget of 1 was approved. The check also approves a budget of 0 for a project that has no cost items at all. Fully balanced breakdowns, where every item has zero or two sub-items, have never caused a problem.

## Input

- `root`: the root of a binary tree, or null for an empty tree
- `target`: the required path sum

## Output

`true` when some root-to-leaf path sums to `target`, otherwise `false`.

## Examples

### Example 1

<!-- case: ex1 -->

The path 5 -> 4 -> 11 -> 2 ends at a leaf and sums to 22. This case passes as shipped.

### Example 2

<!-- case: ex2 -->

The only root-to-leaf path is 1 -> 2, which sums to 3. The root alone sums to 1, but the root has a child, so it is not a leaf and its value alone is not a path. The shipped code answers `true` here.

## Constraints

- `0 <= number of nodes <= 1000`
- The tree height is at most 500.
- `-1000 <= node.val <= 1000`
- `-10^6 <= target <= 10^6`

## Follow-ups

- Return every root-to-leaf path that reaches `target`, not just whether one exists.
- Count paths that reach `target` when a path may start and end at any node on a downward route.

## Hints

### Hint 1

Compare the trees that pass with the ones that fail. Is there a node shape that only the failing trees contain?

### Hint 2

Trace Example 2 by hand. Which call returns `true`, and which node is it called on?

### Hint 3

The base case answers the question "does a path end here?". The code asks it of a missing child. Can a path end at a child that does not exist?

### Hint 4

A leaf is a node whose left and right children are both missing. Where should the check `remaining == 0` happen?
