# Redundant Connection

## Statement

A network started as a tree: `n` nodes labelled from `1` to `n`, connected without any cycle. Then one more undirected edge was added between two different nodes that were not already directly connected. The resulting `n` edges are listed in `edges`, in some order.

Return an edge whose removal turns the network back into a tree on all `n` nodes. Several edges may qualify; return the one that appears last in `edges`, written exactly as it appears there.

Reference: this is our own wording of LeetCode problem 684, [Redundant Connection](https://leetcode.com/problems/redundant-connection/).

## Input

- `edges`: the `n` undirected edges `[a, b]`, in their listed order

## Output

The edge to remove, as the pair listed in `edges`.

## Examples

### Example 1

<!-- case: ex1 -->

The edges 1-2, 2-3, 3-4 and 1-4 form the cycle 1, 2, 3, 4. Removing any of those four leaves a tree, and the last of them in the list is `[1, 4]`. The edge to node 5 comes later but is not on the cycle, so removing it would disconnect node 5.

### Example 2

<!-- case: ex2 -->

All three edges form a triangle, so any of them could go; `[2, 3]` comes last.

## Constraints

- `n == edges.length`
- `3 <= n <= 1000`
- `edges[i].length == 2`
- `1 <= a, b <= n` and `a != b`
- No edge appears twice, in either direction.
- The edges form a tree on all `n` nodes plus exactly one extra edge.

## Follow-ups

- Why is the answer always the first edge, in list order, whose two endpoints are already connected by earlier edges?
- How fast can you test "already connected" for each new edge?
- In the directed version of this problem, what new cases appear?

## Hints

### Hint 1

A tree on `n` nodes has `n - 1` edges, so the extra edge closes exactly one cycle, and removing any edge of that cycle leaves a tree.

### Hint 2

Add the edges one by one. Before adding `[a, b]`, ask whether `a` and `b` are already connected. The first edge for which they are is the one that closes the cycle, and every other cycle edge comes earlier in the list.

### Hint 3

A union-find structure answers "already connected?" in near-constant time: two nodes are connected exactly when they have the same root.
