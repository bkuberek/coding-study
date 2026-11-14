# Vertical Order Traversal: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| dfs-sort | intermediate | O(n log n) | O(n) | a depth-first walk is natural, or ties need a custom order |
| bfs-columns | optimal | O(n) | O(n) | default answer |

`n` is the number of nodes.

## Approach: dfs-sort (Depth-first walk then a stable sort by column and row)

### Intuition

Every node has a column and a row (its depth), and the required order is: by column, then by row, then left to right within the row. Collect `(column, row, value)` for every node and sort by the first two keys. A pre-order walk that goes left before right already lists nodes of the same row in left-to-right order, so a stable sort keeps that last tie-break for free.

### Algorithm

1. Walk the tree in pre-order (node, left subtree, right subtree), passing the column and row: the root is `(0, 0)`, a left child `(column - 1, row + 1)`, a right child `(column + 1, row + 1)`.
2. Append `(column, row, value)` for every node.
3. Stable-sort the entries by `(column, row)`.
4. Split the sorted entries into runs of equal column and return each run's values.

### Correctness

After sorting, entries are grouped by column in increasing order, and inside a column ordered by row, top to bottom. For two nodes with the same column and row, the stable sort keeps their pre-order positions. Pre-order visits the node in the left subtree of their lowest common ancestor first, and that node is also the one further left on their shared level, so the tie-break is left to right, as required.

### Complexity

- Time: O(n log n) — the walk is O(n) and the sort of `n` entries dominates.
- Space: O(n) — the entry list, the output and an O(h) recursion stack.

### Trade-offs

It is easy to adapt when the tie-break changes (for example the variant that sorts same-place nodes by value just adds a sort key), but it pays a logarithmic factor for the sort and depends on sort stability, which is a detail interviewers like to probe.

### Pitfalls and edge cases

- Sorting by column only: pre-order would then list a deep node of the left subtree before a shallow node of the right subtree in the same column. The hidden case where node 6 sits two levels below node 3 in column 1 catches this.
- Using an unstable sort, or a sort key that includes the value, breaks the left-to-right tie rule.
- An empty tree returns an empty list.

### Language notes

- Python: `list.sort` is stable; `itertools.groupby` splits consecutive equal columns.
- TypeScript: `Array.prototype.sort` is stable since ES2019; the comparator `a.column - b.column || a.row - b.row` falls through to the row when the columns are equal.
- Java: `List.sort` uses a stable merge sort (TimSort) for objects; `Comparator.comparingInt(...).thenComparingInt(...)` builds the two-key order without boxing.
- Kotlin: `sortedWith(compareBy(...))` is stable, and `groupBy` keeps the first-seen order of keys, which after sorting is increasing column order.
- Go: `cmp.Or(cmp.Compare(a.column, b.column), cmp.Compare(a.row, b.row))` chains the two sort keys, and `slices.SortStableFunc` keeps pre-order among equal keys. There is no `groupby`, so the loop opens a new column whenever the column differs from the previous entry's.
- Rust: `sort_by_key` with a `(column, row)` tuple is stable, and `chunk_by(|a, b| a.0 == b.0)` yields the runs of adjacent entries with the same column.

## Approach: bfs-columns (Breadth-first walk into column buckets)

### Intuition

A breadth-first walk visits nodes level by level and, within a level, left to right. That is exactly the order required inside each column, so appending each value to its column's bucket as it is dequeued produces every column already in order. The columns used are a contiguous range of integers, so remembering the smallest and largest one is enough to emit them in order.

### Algorithm

1. If `root` is null, return an empty list.
2. Put `(root, 0)` in a queue; track the leftmost and rightmost columns seen.
3. While the queue is not empty: remove `(node, column)`, append `node.val` to the bucket of `column`, update the column range, and enqueue the non-null children with `column - 1` and `column + 1`.
4. Return the buckets for every column from leftmost to rightmost.

### Correctness

The queue releases nodes in level order, left to right within a level. Each bucket receives its values in that order, so inside a column the values are top to bottom and left to right on the same level. Every column between the leftmost and rightmost has at least one node, because the path from the root to any node changes column by exactly one per step and therefore passes through every column in between; so no bucket in the emitted range is missing.

### Complexity

- Time: O(n) — each node is queued, removed and appended to a bucket once, with O(1) expected hash-map work.
- Space: O(n) — the buckets hold every value, and the queue holds at most about one level.

### Trade-offs

Linear time and no sorting, which makes it the expected optimal answer. The order requirement comes from the traversal itself, so changing the tie-break (for example to sort by value) would need extra sorting inside buckets.

### Pitfalls and edge cases

- A depth-first walk in place of breadth-first silently breaks the top-to-bottom order inside columns.
- Sorting the map keys works but adds O(c log c) for `c` columns; tracking the range avoids it.
- Equal values are separate entries: never deduplicate.

### Language notes

- Python: `defaultdict(list)` creates buckets on first use, and `range(min(columns), max(columns) + 1)` walks the contiguous column range.
- TypeScript: a `Map<number, number[]>` and a read index into growing arrays replace a real queue, because `Array.prototype.shift()` is linear.
- Java: `computeIfAbsent` creates buckets; a parallel `Deque<Integer>` carries the columns, since `ArrayDeque` cannot hold the `null` a missing child would be.
- Kotlin: `getOrPut` creates buckets, a `Pair<TreeNode, Int>` queue with destructuring carries the column, and `getValue` asserts that every column in the range exists.
- Go: a `map[int][]int` plus the running `lowest` and `highest` columns; the builtin `min` and `max` update them. An empty tree returns nil, encoded as `[]`.
- Rust: `columns.entry(column).or_default().push(..)` is the `defaultdict`. A `BTreeMap` would keep the columns sorted by itself but costs O(log n) per insert, so the reference keeps a `HashMap`, tracks the lowest and highest column, and removes the columns in order.
