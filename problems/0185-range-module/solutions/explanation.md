# Range Module: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| interval-list | brute | O(k) per call | O(k) | few stored intervals, or as a correctness oracle |
| dynamic-segment-tree | optimal | O(log C) per call | O(n log C) | many intervals or many calls; the general technique |

`k` is the number of stored intervals, `n` the number of calls and `C = 10^9` the size of the coordinate range. In the generated sequences `k` grows with `n`, so the interval list costs O(n^2) per sequence and the tree O(n log C).

A third common answer keeps the intervals in a balanced ordered map (Java's `TreeMap`, a sorted container in other languages), which finds the affected intervals in O(log k) and removes merged ones in amortized O(1) each. Python and TypeScript have no such map in the standard library, which is one reason the segment tree is the reference here.

## Approach: interval-list (Sorted list of disjoint intervals rebuilt on every change)

### Intuition

Store the covered set as a sorted list of disjoint half-open intervals that do not even touch (touching ones are merged). Then an addition merges everything it overlaps or touches, a removal trims or splits what it overlaps, and a query is covered exactly when one stored interval contains it.

### Algorithm

1. `addRange(left, right)`: walk the list; copy intervals that end before `left` or start after `right`; absorb every other interval into `[left, right)` by widening it; insert the widened interval at its place.
2. `removeRange(left, right)`: walk the list; keep intervals that do not overlap `[left, right)`; for an overlapping interval keep its parts left of `left` and right of `right`, if any.
3. `queryRange(left, right)`: return whether some stored `[start, end)` has `start <= left` and `right <= end`.

### Correctness

Invariant: the list holds disjoint, non-touching intervals in sorted order whose union is the covered set. Addition replaces the new range and every interval overlapping or touching it by their union, a single interval, and leaves the others alone, so the union grows by exactly `[left, right)` and no two stored intervals touch. Removal keeps exactly the parts of each interval outside `[left, right)`, which are still disjoint and sorted. A range is covered exactly when it lies inside the union; because stored intervals are separated by uncovered gaps, a gapless range inside the union lies inside one interval.

### Complexity

- Time: O(k) per call — each call walks the whole list (a query could stop early, an update rebuilds the list).
- Space: O(k) — the stored intervals.

### Trade-offs

Simple to reason about and fast while the number of intervals is small, but every call costs time proportional to the number of stored intervals. Binary search can find the first affected interval in O(log k), yet inserting or splicing an array is still O(k); only a balanced tree or the segment tree removes that cost.

### Pitfalls and edge cases

- Half-open ranges: intervals that touch (`end == left`) must merge on addition (`end < left` is the "keep separate" test), but a removal that only touches (`end <= left`) changes nothing.
- A removal inside one interval splits it in two; one at an end trims it.
- Keep the list sorted, or the "contained in one interval" query becomes wrong.

### Language notes

- Python and Kotlin: tuples or `Pair`s with destructuring in the loops.
- TypeScript: two parallel arrays of starts and ends, so a rebuild copies small integers instead of allocating one pair per stored interval.
- Java: `int[]` pairs in an `ArrayList`; untouched intervals are reused instead of copied.
- Go: intervals are small `interval{start, end}` structs in a slice, and each change builds a new slice with the exact capacity it needs and swaps it in, as the Python version does with a list. A `switch` with no tag expresses the three-way split of `AddRange` (before, after, overlapping) more clearly than an `if` chain, and `min` and `max` are built in (Go 1.21+).
- Rust: intervals are `(i32, i32)` tuples in a `Vec`; `add_range` shadows its parameters with `let (mut left, mut right) = (left, right)` so the merge loop can widen them, and each change builds a fresh `Vec` and assigns it to `self.intervals`. `iter().any(...)` replaces the search loop of `query_range`.

## Approach: dynamic-segment-tree (Segment tree over the coordinates with lazy assignment)

### Intuition

Think of the line `[1, 10^9)` as the root of a binary tree that halves its range at every level. Each node is either fully covered, fully uncovered (both stored as a single state with no children) or mixed (two children that describe its halves). Adding or removing a range assigns a state to the nodes it covers completely and only splits the nodes cut by its two boundaries, so a call touches O(log C) nodes. After each assignment, a node whose two children agree is collapsed back into a single state, which keeps the tree canonical: a node is mixed exactly when its range is partly covered.

### Algorithm

1. `assign(node, [low, high), [left, right), value)`:
   1. If the ranges do not overlap, return.
   2. If `[low, high)` lies inside `[left, right)`, set the node's state to `value` and drop its children.
   3. Otherwise, if the node has no children, create two children with the node's current state (it was uniform). Recurse into both halves.
   4. If both children now have the same uniform state, take that state and drop the children; else mark the node mixed.
2. `addRange` assigns `COVERED`; `removeRange` assigns `EMPTY`.
3. `queryRange` / `covered(node, [low, high), [left, right))`: return `true` if the ranges do not overlap; if the node is uniform, return whether it is covered; otherwise return `covered(left child) and covered(right child)`.

### Correctness

Invariant: every uniform node describes its whole range exactly, and every mixed node's range is described by its children. An assignment changes exactly the points of `[left, right)`: nodes completely inside get the new state, nodes outside are untouched, and a partially overlapped uniform node is first split into two children with its old state, which describe the same points, before recursing. Collapsing two equal uniform children into their parent describes the same points too. The query answers "is every point of `[left, right)` covered" node by node: non-overlapping nodes do not matter, a uniform overlapping node answers for all its overlapped points at once, and a mixed node delegates to its two halves.

### Complexity

- Time: O(log C) per call — as in any segment tree, an assignment or query visits at most two nodes per level that are cut by the range boundaries, plus their direct children; with canonical collapsing, a query that meets a mixed node fully inside the range follows a single path to an uncovered point. The tree has `log2(10^9) ≈ 30` levels.
- Space: O(n log C) — each call creates at most O(log C) nodes; collapsed nodes become garbage (Java, Kotlin, TypeScript) or stay unused in the pool (Python).

### Trade-offs

Logarithmic in the coordinate range regardless of how fragmented the covered set becomes, and the same tree answers other questions (covered length, first uncovered point) with a field or two more. It is more code than the interval list, allocates nodes, and its cost does not shrink when there are only a few intervals; coordinate compression would need all calls in advance, which an online design cannot assume.

### Pitfalls and edge cases

- Push the state down before recursing into a uniform node: children created empty under a covered parent would lose coverage.
- Use half-open node ranges `[low, middle)` and `[middle, high)`; a unit range `[x, x + 1)` is always either inside or outside a query, so the recursion never needs to split it.
- Compute the midpoint as `low + (high - low) / 2` in fixed-width languages; here `low + high` stays below 2^31, but the habit avoids overflow on larger ranges.
- Without collapsing, a covered region built from many small additions stays mixed, and queries degrade to visiting many nodes.

### Language notes

- Python: nodes live in three parallel lists (`state`, `left`, `right`) indexed by integers, which is faster and lighter than one object per node; recursion depth is only about 31.
- TypeScript: a small `CoverNode` class with nullable children. Its fields are declared and assigned explicitly, because constructor parameter properties are TypeScript-only syntax that Node's type stripping does not run.
- Java: a `private static final class Node` with an `int` state; dropped subtrees are reclaimed by the garbage collector.
- Kotlin: `node.left ?: Node(node.state).also { node.left = it }` creates a missing child on first use; the state constants live in a `companion object`.
- Go: nodes are pointers (`*node`), as in Java: collapsing a node sets its children to `nil`, and the garbage collector reclaims the dropped subtree. The recursive helpers `assign` and `isCovered` are unexported package functions, so only the three public methods are visible to the runner. The tuple assignment `n.state, n.left, n.right = agreed, nil, nil` collapses the node in one statement.
- Rust: a node owns its two children as `Option<Box<[Node; 2]>>`, so collapsing a node with `self.children = None` frees the subtree at once, with no garbage collector and no arena index like the Python lists. `get_or_insert_with` splits a uniform node on first use, and `let [first, second] = &mut **children` hands out both children as disjoint `&mut Node` borrows so they can be assigned recursively. `State` is a small `Copy` enum instead of the integer constants.
