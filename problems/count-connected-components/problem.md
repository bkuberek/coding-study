# Count Connected Components

## Statement

An undirected graph has `n` nodes, numbered from `0` to `n - 1`, and the edges listed in `edges`, where `[a, b]` joins nodes `a` and `b`. Two nodes belong to the same connected component when some path of edges leads from one to the other; a node with no edges forms a component on its own.

Return the number of connected components.

Reference: this is our own wording of LeetCode problem 323, [Number of Connected Components in an Undirected Graph](https://leetcode.com/problems/number-of-connected-components-in-an-undirected-graph/).

## Input

- `n`: the number of nodes
- `edges`: undirected edges `[a, b]`

## Output

The number of connected components.

## Examples

### Example 1

<!-- case: ex1 -->

Nodes 0, 1 and 2 are linked in a row, nodes 3 and 4 are linked to each other, and node 5 has no edges: three components.

### Example 2

<!-- case: ex2 -->

The edge between 1 and 2 joins the pairs {0, 1} and {2, 3} into a single component.

## Constraints

- `1 <= n <= 2000`
- `0 <= edges.length <= 5000`
- `edges[i].length == 2`
- `0 <= a, b < n` and `a != b`
- No edge appears twice, in either direction.

## Follow-ups

- Every edge that joins two different components reduces the count by one. Can you count without building adjacency lists at all?
- If edges keep arriving one by one and you must report the count after each, which approach still works?
- Why does a naive union-find get slow on some inputs, and which two small changes fix it?

## Hints

### Hint 1

A depth-first or breadth-first search from an unvisited node marks its whole component. Count how many searches you need to start.

### Hint 2

Alternatively, start with `n` components, one per node, and merge the components of the two endpoints of each edge. A merge of two different components lowers the count by one; an edge inside one component changes nothing.

### Hint 3

A disjoint-set forest stores each component as a tree with a representative root. Hang the smaller tree under the larger one's root, and point every node on a search path directly at its root: then each operation is practically constant time.
