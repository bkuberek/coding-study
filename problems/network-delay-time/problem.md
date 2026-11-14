# Network Delay Time

## Statement

A network has `n` nodes, labeled `1` to `n`, and one-way links between them. Each entry `times[i] = [u, v, w]` says that a signal leaving node `u` reaches node `v` after `w` time units. A link carries the signal in one direction only.

At time 0 node `k` sends a signal. Every node that receives the signal forwards it at once along all its outgoing links. Return the time at which the last node receives the signal, or `-1` if some node never receives it.

Reference: this is our own wording of LeetCode problem 743, [Network Delay Time](https://leetcode.com/problems/network-delay-time/).

## Input

- `times`: the links, each `[u, v, w]` with source `u`, target `v` and travel time `w`.
- `n`: the number of nodes.
- `k`: the node that sends the signal.

## Output

The smallest time by which every node has received the signal, which is the largest shortest travel time from `k` to any node; `-1` if a node cannot be reached at all. Node `k` itself has it at time 0.

## Examples

### Example 1

<!-- case: ex1 -->

From node 2 the signal reaches node 3 at time 1 and node 1 at time 3. Node 4 can be reached through node 3 (time 1 + 2 = 3) or through node 1 (time 3 + 1 = 4); the earlier arrival counts, so node 4 has the signal at time 3, and so does everyone else by then.

### Example 2

<!-- case: ex2 -->

No link leads into node 3, so it never receives the signal from node 1.

## Constraints

- `1 <= n <= 2000`
- `0 <= times.length <= 10^4`
- `1 <= u, v, k <= n` and `u != v`
- `0 <= w <= 100`
- No pair `(u, v)` appears twice.

## Follow-ups

- Which node receives the signal last, and along which route?
- What if some links had negative travel times (but no negative cycles)? Which algorithm still works?
- For a dense network with about `n^2` links, is the heap still worth it?

## Hints

### Hint 1

The time a node receives the signal is the length of the shortest path from `k` to it. The answer is the largest of these, or `-1` if one is infinite.

### Hint 2

All travel times are non-negative, so Dijkstra's algorithm applies: repeatedly settle the unsettled node with the smallest known arrival time and update its neighbors.

### Hint 3

A min-heap of `(time, node)` pairs finds the next node to settle in O(log V). Skip entries whose node is already settled; they are outdated copies.
