# Critical Connections

## Statement

A network has `n` servers, numbered `0` to `n - 1`, joined by two-way cables: `connections[i] = [a, b]` is a cable between servers `a` and `b`. Every server can reach every other one, directly or through other servers.

A cable is critical if cutting it alone would split the network, so that some pair of servers could no longer reach each other. Return all critical cables.

Reference: this is our own wording of LeetCode problem 1192, [Critical Connections in a Network](https://leetcode.com/problems/critical-connections-in-a-network/).

## Input

- `n`: the number of servers.
- `connections`: the cables, each `[a, b]`.

## Output

Every critical cable as a pair `[a, b]`. The cables may be listed in any order, and the two servers of a cable in either order.

## Examples

### Example 1

<!-- case: ex1 -->

Servers 0, 1 and 2 form a ring, and so do 3, 4 and 5: cutting any one cable of a ring leaves the other way around. The cable between 2 and 3 is the only link between the two rings, and the cable to server 6 is its only link, so those two are critical.

### Example 2

<!-- case: ex2 -->

With two servers and one cable, that cable is critical.

## Constraints

- `2 <= n <= 2000`
- `n - 1 <= connections.length <= 5000`
- `0 <= a, b < n` and `a != b`; no pair of servers has two cables.
- The network is connected.

## Follow-ups

- Which servers are critical, that is, would split the network if they failed?
- Cables are added over time. How would you keep the set of critical cables up to date?
- Your depth-first search recurses up to `n` levels deep. How would you write it iteratively for `10^5` servers?

## Hints

### Hint 1

The direct approach cuts each cable in turn and checks whether everything is still reachable. Why is that too slow for many cables?

### Hint 2

A cable is critical exactly when it lies on no cycle. Run one depth-first search and record for every server the time at which it was first discovered.

### Hint 3

For every server, compute the earliest discovery time reachable from its subtree using at most one cable that is not a tree edge (its low link). A tree edge from `u` to child `v` is critical when the low link of `v` is greater than the discovery time of `u`.
