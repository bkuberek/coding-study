# Is the Graph Bipartite

## Statement

You get an undirected graph with `V` nodes, numbered `0` to `V - 1`, as an adjacency list: `graph[u]` lists every node that shares an edge with `u`. The graph may fall apart into several pieces that have no edges between them.

The graph is bipartite when its nodes can be split into two teams so that every edge joins a node of one team to a node of the other; no edge may stay inside a team. Decide whether such a split exists.

Reference: this is our own wording of LeetCode problem 785, [Is Graph Bipartite?](https://leetcode.com/problems/is-graph-bipartite/).

## Input

- `graph`: the adjacency list; `graph[u]` holds the neighbors of node `u` in any order.

## Output

`true` if the nodes can be split into two teams with every edge going between the teams, `false` otherwise.

## Examples

### Example 1

<!-- case: ex1 -->

The five nodes form one ring: 0, 1, 2, 3, 4 and back to 0. Going around the ring the teams must alternate, and a ring of odd length cannot alternate all the way round, so no split exists.

### Example 2

<!-- case: ex2 -->

There are three pieces: the path 0, 1, 2, the lone node 3, and the edge between 4 and 5. Put 0, 2 and 4 in one team and 1, 3 and 5 in the other; every edge crosses between them.

## Constraints

- `1 <= V <= 10^4`
- The adjacency lists hold at most `10^5` entries in total.
- `0 <= graph[u][i] < V`, and `graph[u][i] != u` (no node is linked to itself).
- No edge is listed twice in one list, and `v` appears in `graph[u]` exactly when `u` appears in `graph[v]`.

## Follow-ups

- When the answer is `false`, can you return an odd cycle as proof?
- When the answer is `true`, return the two teams.
- Edges arrive one at a time. After each one, report whether the graph is still bipartite.

## Hints

### Hint 1

Pick any node and put it in team A. Its neighbors are then forced into team B, their neighbors into team A, and so on.

### Hint 2

Spreading the teams with a breadth-first or depth-first search either colors every node of the piece, or meets an edge whose two ends got the same team. Remember to start again in every piece of the graph.

### Hint 3

Another view: all neighbors of a node must share one team, and that team differs from the node's. Merge each node's neighbors into one group and check that no node lands in the group of its own neighbors.
