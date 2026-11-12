# Path Exists in a Graph

## Statement

A hiking club maintains `n` campsites, numbered from `0` to `n - 1`, and a list of trails. Each trail joins two campsites and can be walked in either direction. In graph language the campsites are the nodes and the trails are the edges, and because a trail works both ways the graph is undirected.

A path from one campsite to another is a walk that goes from the first to the second along trails, possibly passing through other campsites on the way. A campsite is always reachable from itself, with a walk of zero trails.

Given the campsites, the trails, a starting campsite `source` and a destination `target`, return `true` if some path leads from `source` to `target`, and `false` otherwise.

## Input

- `n`: the number of campsites.
- `edges`: the trails; each entry `[a, b]` joins campsites `a` and `b`, and may be read in either direction.
- `source`: the campsite where the walk starts.
- `target`: the campsite where the walk must end.

## Output

`true` if `target` can be reached from `source` along trails, and `false` otherwise.

## Examples

### Example 1

<!-- case: ex1 -->

The trails link 0 to 1, 1 to 2 and 2 to 3, so the walk 0, 1, 2, 3 reaches the target. The trail `[3, 2]` is listed with its ends in the opposite order, which makes no difference: it can be walked from 2 to 3.

### Example 2

<!-- case: ex2 -->

Same campsites and trails, but now the target is 5. Campsite 5 is joined only to campsite 4, and neither of the two leads to 0, 1, 2 or 3, so there is no path.

## Constraints

- `1 <= n <= 2000`
- `0 <= edges.length <= 5000`
- `edges[i].length == 2`
- `0 <= edges[i][0], edges[i][1] < n` and `edges[i][0] != edges[i][1]`
- No two trails join the same pair of campsites, in either order.
- `0 <= source, target < n`

## Follow-ups

- Your search is allowed to stop as soon as it meets the target. What does that change in the best case, and in the worst case?
- If you had to answer thousands of questions of the form "is there a path from `a` to `b`" on the same trails, what could you compute once and reuse?
- The trails are now one-way. Which part of your solution has to change?

## Hints

### Hint 1

Try the first example on paper. Starting at campsite 0, which campsites can you reach in one step? In two? Stop when you reach the target or when a step brings nothing new.

### Hint 2

To ask "which campsites are next to this one?" quickly, it helps to keep a list for each campsite with its neighbours, called an adjacency list. Reading the edge list for every question would take far too long. Build the lists once: for each trail `[a, b]`, put `b` in the list of `a` and `a` in the list of `b`.

### Hint 3

Keep a record of the campsites you have already visited, so that a ring of trails does not send you round and round. Each campsite only needs to be explored once.

### Hint 4

Put `source` in a queue (or on a stack) and mark it visited. Repeatedly take one campsite out, return `true` if it is the target, and add every unvisited neighbour to the queue after marking it. If the queue empties without meeting the target, return `false`. There is another way to look at the same question: group campsites that are linked, and ask whether `source` and `target` ended up in the same group.
