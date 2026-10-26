# Clone Graph

## Statement

You get one node of a connected, undirected graph. Each node stores an integer `val` and a list `neighbors` of the nodes it is linked to. Build a deep copy of the whole graph: a brand-new node for every original node, linked to each other exactly as the originals are, and return the copy of the node you were given.

The copy must not share any node object with the original graph, not even one. Every copied node keeps the value of its original, and its `neighbors` list names the copies of the original neighbors in the same order.

Reference: this is our own wording of LeetCode problem 133, [Clone Graph](https://leetcode.com/problems/clone-graph/).

## Input

- `node`: a node of the graph, or null when the graph is empty. Every node in the graph can be reached from it.

In the examples a graph is written as an adjacency list: entry `i` (counting from 1) lists, in order, the values of the neighbors of the node whose value is `i`. Node values are therefore `1` to `V`, and `node` is the node with value `1`. `[]` is the empty graph and `[[]]` a single node with no neighbors.

## Output

The copy of `node`, or null for an empty graph. It is written in the same adjacency-list form, read from the returned node, so a correct copy prints exactly like the input. Returning any original node, directly or as a neighbor of a copy, is an invalid answer.

## Examples

### Example 1

<!-- case: ex1 -->

Nodes 1, 2 and 3 form a triangle, and node 4 hangs off node 2. The copy has the same four values and the same links; node 2's copy lists the copies of 1, 3 and 4 in that order.

### Example 2

<!-- case: ex2 -->

A single node without neighbors is copied into a single new node without neighbors.

## Constraints

- The graph has between `0` and `2000` nodes, with values `1` to `V`, each value used once.
- Every node has at most `100` neighbors.
- Edges are undirected: `b` is a neighbor of `a` exactly when `a` is a neighbor of `b`.
- No node is its own neighbor, and no pair of nodes is linked twice.
- The graph is connected.

## Follow-ups

- What changes if the graph may be disconnected and you get a list of all its nodes instead of one?
- Your recursive copy can go as deep as the number of nodes. Rewrite it so a path of 10^5 nodes is safe.
- How would you copy a directed graph, or a linked list whose nodes also point to a random other node?

## Hints

### Hint 1

The hard part is the cycles: following neighbor links blindly never ends, and copying a node twice breaks the shared structure. What do you need to remember about each original node?

### Hint 2

Keep a map from each original node to its copy. Create the copy the first time you meet a node and reuse it every other time.

### Hint 3

Visit the graph with depth-first or breadth-first search. When you look at an edge from `u` to `v`, make sure `v` has a copy, then append that copy to the neighbors of `u`'s copy.
