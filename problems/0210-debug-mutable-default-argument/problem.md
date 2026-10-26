# Debug: Mutable Default Argument

## Statement

The function `leaf_values` you start from should return the values of all leaves of a binary tree, from left to right. A leaf is a node with no children. An empty tree has no leaves.

The code recurses with an accumulator list that collects the leaves. It is correct on the first call, and only on the first call. Find out why and fix it. Callers pass only `root`; keeping the optional `leaves` parameter is fine as long as calls without it behave correctly.

### Bug report

> **Title:** Leaf export returns more and more data over time
>
> The catalog service exports the leaf categories of a category tree through `leaf_values`. Right after a deploy, the first export is correct. Every export after that contains the leaves of every earlier export too, and responses keep growing until the worker restarts. The unit test for the function passes in CI, where it calls `leaf_values` once, on one tree.

## Input

- `root`: the root of a binary tree, or null for an empty tree

## Output

The leaf values in left-to-right order.

## Examples

### Example 1

<!-- case: ex1 -->

The leaves are 4 and 5 (children of 2) and 3, in that order from left to right. As the first call in the run, this case passes as shipped.

### Example 2

<!-- case: ex2 -->

A single node is a leaf. Shipped, this call returns the leaves of Example 1 followed by 7, because it runs after Example 1 in the same process.

## Constraints

- `0 <= number of nodes <= 1000`
- The tree height is at most 500.
- `-1000 <= node.val <= 1000`

## Follow-ups

- Rewrite the function without the accumulator parameter, either with a nested helper or by concatenating the results of the two subtrees. What does each version cost?
- Which other default values are dangerous in the same way?

## Hints

### Hint 1

Call the function twice in a row on two different small trees, in one Python session. Compare the second result with what you expected.

### Hint 2

Where does the list in `leaves` come from when the caller does not pass one? When is that list created: on every call, or once?

### Hint 3

Print `leaf_values.__defaults__` before and after a call.

### Hint 4

`leaves = leaves or []` looks like a fix but is not. What happens to a recursive call that receives the caller's empty list?
