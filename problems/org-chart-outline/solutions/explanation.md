# Org Chart Outline: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| child-lists | optimal | O(n) to load; O(depth) per chain or manager query; O(1) per size; O(n log n) per outline | O(n) | default answer; one index serves all four levels |

Here `n` is the number of rows and `depth` the number of levels of the chart.

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | Turn parent links into child lists | `parents`, `names` and `kids`: for each id, the ids of its reports in the order of the rows; the key `""` holds the roots |
| 2 | Rows in any order, orphans, cycles | `orphans`, the `tops` (roots and orphans in row order), and the set of rows reached from the tops; the cycles are found among the rows not reached |
| 3 | Chains and common managers | nothing new: a chain is a walk over `parents` |
| 4 | Sizes and the outline | `sizes`, computed from the breadth-first order of level 2; the outline is a depth-first walk with a stack of its own |

The early choice that makes the later levels cheap is to build the whole index in a second step, after one pass has recorded every id. A solution that attaches each row to its parent while reading the rows silently assumes that managers come first, and has to be rewritten at level 2. Here `load` first fills `parents`, `names` and `kids` from all the rows, and only then asks which rows are roots, orphans or lost in a cycle.

## Approach: child-lists (Child lists built once from the rows)

### Intuition

The rows store each person's manager, but the questions ask about reports, so the data must be turned around once. After that, a tree is a map from an id to a list of ids, and every question is a short walk over that map: down it for sizes and outlines, up the `parents` links for chains. Cycles and orphans are not special cases of the walk, they are rows the downward walk from the tops never reaches or starts from.

### Algorithm

1. Level 1: for every row in order, record `parents[id]`, `names[id]` and append `id` to `kids[parent]`. `roots` is `kids[""]`, `children(x)` is `kids[x]` and `nameOf(x)` is `names[x]`; missing keys give the empty answer.
2. Level 2: the orphans are the rows with a non-empty parent that is not a key of `names`. The tops are the rows that are roots or orphans, in row order. Walk down from the tops with a queue: every row reached is attached, and the queue lists each parent before its reports. For each row that is not attached, follow `parents` until you reach a row seen before; if the walk stops on a row of the current walk, that row and the ones after it are a cycle. Rotate the cycle so that its first member in the input comes first, and sort the cycles by the position of that member.
3. Level 3: `chain(x)` is empty unless `x` is attached; otherwise it climbs `parents` until the parent is not a known id. `lowestCommonManager` puts the chain of the second id in a set and returns the first member of the first id's chain that is in it.
4. Level 4: `subtreeSize` comes from going through the queue of step 2 backwards and adding each row's size to its parent's size. `outline` keeps a stack of `(id, depth)`: it pops a row, writes `indent + name + " (" + id + ")"`, sorts its children by the requested order and pushes them in reverse, so that the first child is popped next.

### Correctness

Invariant of the downward walk: when a row is dequeued, all its attached reports are appended after it. So the queue is a list of exactly the attached rows, with every parent before its reports, and the rows not in it are those that do not reach a top by climbing, that is, the rows on a cycle or below one. Every row has one parent link, so the rows outside the queue form paths that end in a cycle or in the queue; following links from such a row therefore either enters a cycle (the walk stops on a row of itself) or reaches a row already classified (the walk stops on a row of an earlier walk and finds no new cycle). Each cycle is found by exactly one walk, because the first walk to enter it marks all its members.

Sizes: going through the queue backwards, every row is processed after all of its reports, since reports come later in the queue. So when a row is added to its parent, its own size is final. The outline is a pre-order traversal: popping a row and pushing its children in reverse order lists the row, then the entire subtree of the first child, before the second child is popped, which is the order of a depth-first walk.

### Complexity

- Time: O(n) to load; O(depth) per chain or manager query; O(1) per size; O(n log n) per outline — `load` makes a constant number of passes with O(1) map operations; a chain visits each ancestor once; a size is a map lookup; the outline writes one line per attached row and sorts each child list once, which is O(n log n) in all when the sibling lists are large.
- Space: O(n) — the maps, the child lists, the queue and the sizes each hold one entry per row.

### Trade-offs

- Climbing parent links makes `lowestCommonManager` O(depth). For many queries on a deep chart, binary lifting (a table of the 2^k-th ancestor of each row) answers in O(log n) for O(n log n) space. At this size the plain climb is simpler and fast enough.
- Sorting the children on every `outline` call repeats work when the same order is asked for often. Caching the sorted lists per order trades memory for time.
- A recursive traversal is shorter to write, but it needs one stack frame per level. Python stops at about 1,000 frames by default, and the other languages stop within tens of thousands, well under a chain of 10^5 managers.

### Pitfalls and edge cases

- Assuming the parent's row comes first: a one-pass solution that attaches a row to an already-built parent loses every row that arrives early. The hidden cases at level 2 list rows deepest first.
- Treating a missing parent as a root: an orphan is reported in `orphans()` but is not in `roots()`. A row with an empty parent is a root and never an orphan.
- Looping forever on a cycle: a climb that stops only at "no parent" never ends on `a -> c -> b -> a`. Climb only from attached rows.
- Reporting a cycle from the wrong member, or in the wrong direction: the entry starts at the member whose row is first in the input and follows the parent links, so `[a, c, b]` and not `[a, b, c]`.
- Counting rows below a cycle as orphans or cycle members: they are neither, and they are not attached.
- A person on their own chain: `lowestCommonManager(x, y)` is `x` when `x` manages `y`, and `lowestCommonManager(x, x)` is `x`.
- Comparing text by locale or by case: the sort is by character value, so `B` comes before `a` and the id `10` before `9`. A case-insensitive or numeric sort fails the hidden cases.
- Recursion depth: the hidden case with a chain of 1,500 managers fails a recursive solution in Python, and the generated case with a chain of 100,000 fails the recursive solutions of every language.
- Reusing an old chart: `load` replaces the whole chart, including the orphans and cycles of the earlier one.

### Language notes

- Python sorts with a `key` tuple, so `sorted(ids, key=lambda i: (names[i], i))` is the whole comparator. Its strings compare by code point, which is the same as the ASCII order of the statement.
- TypeScript compares strings with `<` and `>`, which is by UTF-16 unit and so by ASCII value here; `localeCompare` would be wrong. Java and Kotlin `String.compareTo` is the same comparison. Go and Rust compare strings by bytes, which is the same for ASCII.
- Java and Kotlin keep the explicit stack in an `ArrayDeque`; Go and Rust use a slice and `pop`. None of them uses the call stack for the walk.
- Rust takes its parameters by value (`String`, `Vec<Vec<String>>`), so `load` clones the ids it stores in more than one map.
