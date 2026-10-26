# Network Delay Time: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| bellman-ford | brute | O(V·E) | O(V) | negative travel times are possible, or you need the simplest correct code |
| dijkstra-array | intermediate | O(V^2 + E) | O(V + E) | dense networks with close to V^2 links |
| dijkstra-heap | optimal | O((V + E)·log V) | O(V + E) | default answer for sparse networks |

The signal reaches each node along a shortest path from `k`, so the answer is the largest shortest-path distance from `k`, or -1 if some node is unreachable. This is the single-source shortest-path problem with non-negative weights. V is the number of nodes and E the number of links.

## Approach: bellman-ford (Relax every edge until no arrival time improves)

### Intuition

Start with arrival time 0 at `k` and infinity elsewhere. A link `u -> v` with time `w` can improve `v`: if `arrival[u] + w < arrival[v]`, the route through `u` is faster. Apply this "relaxation" to every link, again and again. A fastest route uses at most V - 1 links, and each full pass extends the set of correct times by at least one more link, so V - 1 passes suffice; stop early when a pass changes nothing.

### Algorithm

1. Set `arrival[k] = 0` and every other arrival to infinity.
2. Repeat up to V - 1 times: for every link `[u, v, w]`, set `arrival[v] = min(arrival[v], arrival[u] + w)`; stop if no value changed during the pass.
3. If any arrival is still infinite, return -1; otherwise return the largest arrival.

### Correctness

Every finite arrival value is the length of some real route, since it is built from a link added to a route to `u`. By induction on `i`, after pass `i` every node whose fastest route has at most `i` links holds its exact time: its last link is relaxed in pass `i` from a predecessor that was exact after pass `i - 1`. With non-negative times (indeed without negative cycles), a fastest route never repeats a node, so it has at most V - 1 links. A pass with no change means no relaxation can ever change anything again, so stopping early is safe.

### Complexity

- Time: O(V·E) — up to V - 1 passes over all E links; with early stopping it is often far less.
- Space: O(V) — one arrival time per node; the links are used as given.

### Trade-offs

The shortest code and the only one here that tolerates negative travel times. Its worst case is far slower than Dijkstra on large networks; it is the right choice only when weights can be negative or when a hop limit is part of the problem (as in the cheapest-flights problem).

### Pitfalls and edge cases

- Guard against adding to infinity in languages with fixed-size integers: skip links whose source is unreached.
- Unreachable nodes keep infinity and make the answer -1.
- With `n = 1` there are no passes and the answer is 0.

### Language notes

- Python: `math.inf` stands for unreached; the result converts back with `int(...)`.
- TypeScript: `Infinity` is a valid `number`, and `Infinity + w` stays `Infinity`, so no guard is needed.
- Java: `Integer.MAX_VALUE` marks unreached nodes and must be checked before adding, or the sum overflows to a negative number.
- Kotlin: `for ((u, v, w) in times)` destructures each `IntArray` link; `maxOf` finds the latest arrival.

## Approach: dijkstra-array (Dijkstra that scans for the closest unsettled node)

### Intuition

With non-negative times, the unsettled node with the smallest tentative arrival can never be improved later: any other route to it would pass through a node that is at least as far. So settle nodes one at a time in order of arrival: pick the closest unsettled node, fix its time, and relax its outgoing links. Finding the closest node by scanning all nodes costs O(V) per step.

### Algorithm

1. Build adjacency lists; set `arrival[k] = 0`, others infinity.
2. Repeat V times: scan for the unsettled node `u` with the smallest arrival; if it is infinite, return -1. Settle `u`, remember its arrival as the latest so far, and relax every link out of `u`.
3. Return the latest settled arrival.

### Correctness

Invariant: every settled node holds its exact shortest time. Suppose `u` is the next node chosen and some faster route to `u` exists; it leaves the settled set at some first unsettled node `x`, whose tentative time is at most that route's time to `x` (its predecessor is settled and was relaxed), which is at most the route's total time to `u` because times are non-negative. That makes `x` at least as close as `u`, contradicting the choice unless the times are equal. Nodes are settled in non-decreasing order of time, so the last settled time is the largest; an infinite minimum means the remaining nodes are unreachable.

### Complexity

- Time: O(V^2 + E) — V scans of V nodes each, plus one relaxation per link.
- Space: O(V + E) — adjacency lists, arrival times and settled flags.

### Trade-offs

No priority queue needed, and on dense networks (E close to V^2) it is actually optimal, since the heap version costs O(E·log V) there. On sparse networks the V^2 scans dominate and the heap version wins.

### Pitfalls and edge cases

- Stop with -1 as soon as the closest unsettled node is unreachable; continuing would settle infinite times.
- Settled nodes must be excluded from the scan.
- Zero-time links are fine; Dijkstra needs non-negative, not positive, times.

### Language notes

- Python: `min(..., key=arrival.__getitem__)` scans the unsettled nodes.
- TypeScript: a plain loop finds the closest unsettled node; `Uint8Array` stores the settled flags.
- Java: `List<List<int[]>>` adjacency; the scan is an explicit loop over `int[] arrival`.
- Kotlin: `(1..n).filter { !settled[it] }.minBy { arrival[it] }` expresses the scan directly, at the cost of a temporary list per round.

## Approach: dijkstra-heap (Dijkstra with a binary min-heap)

### Intuition

Same settling order, but keep the candidates in a min-heap of `(time, node)` pairs instead of scanning. Every time a link offers a time to an unsettled node, push the offer. The smallest offer on top of the heap belongs to the next node to settle; offers for nodes that are already settled are stale and get skipped.

### Algorithm

1. Build adjacency lists and push `(0, k)` onto a min-heap.
2. While the heap is not empty: pop `(time, node)`; if `node` is settled, skip it. Otherwise settle it with `time`, and push `(time + w, neighbor)` for every link to an unsettled neighbor.
3. If all V nodes were settled, return the time of the last one settled; otherwise return -1.

### Correctness

The heap always contains, for every unsettled node with a finite tentative time, an entry carrying that time (plus stale entries with larger times for some nodes). So the smallest valid entry popped is the unsettled node with the smallest tentative time, exactly the node the array version would choose, and the same invariant proves that its time is final. Nodes leave the heap in non-decreasing order of time, so the last settled time is the maximum. If the heap empties before all nodes are settled, the rest are unreachable.

### Complexity

- Time: O((V + E)·log V) — each link pushes at most one entry, and each push or pop costs O(log E) = O(log V).
- Space: O(V + E) — adjacency lists and up to E heap entries.

### Trade-offs

The standard answer for sparse networks. "Lazy deletion" (pushing duplicates and skipping stale entries) avoids a decrease-key operation, which most standard heaps lack, at the cost of a heap that can hold E entries instead of V.

### Pitfalls and edge cases

- Skip popped entries whose node is already settled; processing them again is wasted work and, in variants that count or sum, gives wrong answers.
- Count settled nodes to detect unreachable ones.
- Order heap entries by time first; ordering by node gives a breadth-first search, not Dijkstra.

### Language notes

- Python: `heapq` is a min-heap over tuples, which compare by time first.
- TypeScript: there is no built-in priority queue, so the reference implements a binary min-heap with `push` (sift up) and `pop` (sift down) over `[time, node]` tuples.
- Java: `PriorityQueue<int[]>` with `Comparator.comparingInt(entry -> entry[0])`.
- Kotlin: `PriorityQueue<Pair<Int, Int>>(compareBy { it.first })`; destructuring `val (time, node)` reads an entry.
