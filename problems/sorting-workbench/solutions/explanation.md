# Sorting Workbench: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| classic-algorithms | optimal | O(n^2) insertion sort, O(n log n) merge sort and quicksort, O(n) expected quickselect, O(n log w) per merge pass | O(n) | always: the meter specifies the algorithms, so there is one way to build each level |

## How the design grows level by level

The class keeps one thing between calls, the meter: the list that `report()` returns. Every sort computes its own counters in local variables and stores them at the end, which replaces the previous meter. Nothing else is shared, so a sort cannot be influenced by an earlier one, and the input is copied before it is changed.

| Level | Adds | Meter after it |
|-------|------|----------------|
| 1 | insertion sort | `[comparisons, moves]` |
| 2 | a stable merge sort by a column | `[comparisons]` |
| 3 | quicksort and quickselect, one three-way partition | `[partitions, steps]` |
| 4 | an external merge sort | `[runs, passes]` |

The sorts are independent algorithms, but they meet in useful places: the merge of level 2 is the merge that level 4 does with a heap, and the partition of level 3 is the same loop for the sort and for the select.

## Approach: classic-algorithms (The four classic algorithms written as specified)

### Intuition

Each algorithm is the textbook one with its counting points fixed by the statement.

- **Insertion sort** keeps a sorted prefix and slides each new value left past the larger ones. Every shift removes one inversion, so the moves equal the number of inversions in the input; the comparisons are the moves plus one failed comparison for each key that stops against a value instead of at the front. Knuth's *The Art of Computer Programming, Volume 3: Sorting and Searching* (2nd edition, Addison-Wesley, 1998) treats inversions in its chapter on sorting.
- **Merge sort** splits in halves, sorts each half and merges. Taking from the left half on a tie is what keeps equal keys in their input order, so the sort is stable and several stable sorts can be chained from the least important column to the most important one.
- **Quicksort** partitions around a pivot into smaller, equal and larger values, and recurses on the smaller and larger blocks. The partition is the three-way partition that Dijkstra's Dutch national flag problem asks for; *A Discipline of Programming* (Prentice-Hall, 1976) is the reference the NIST Dictionary of Algorithms and Data Structures gives for it. Quicksort itself was published by C. A. R. Hoare, "Quicksort", *The Computer Journal* 5(1), 1962, pp. 10 to 16. **Quickselect** reuses the partition and follows only the side that holds the wanted position.
- **External merge sort** cuts the input into memory-sized runs, sorts each one, and merges groups of `ways` runs in passes until one run remains. A min-heap holding one value per run makes each merge step cheap.

### Algorithm

1. **Insertion sort.** Copy the list. For `i` from 1: take `key = a[i]` and `j = i - 1`. While `j >= 0`: count a comparison; if `a[j] <= key`, stop; otherwise write `a[j]` to `a[j + 1]`, count a move and decrease `j`. Write `key` at `a[j + 1]`. Store `[comparisons, moves]`.
2. **Merge sort by a column.** Split the rows at `floor(n / 2)`, sort both halves recursively, then merge: while both halves have rows, count a comparison and take the left row when `left.key <= right.key`, else the right row; append what remains. Store `[comparisons]`.
3. **Partition.** The pivot is the value at `low + (high - low) div 2`. With `below = scan = low` and `above = high`, while `scan <= above`: a smaller value swaps with `a[below]` and both `below` and `scan` advance; a larger value swaps with `a[above]` and `above` decreases; an equal value advances `scan`. Return `below` and `above`.
4. **Quicksort.** Keep a stack of ranges, starting with the whole list. Pop a range; if it has at least two values, partition it, count one partition and `high - low + 1` steps, and push the two outer ranges. Store `[partitions, steps]`.
5. **Quickselect.** With target `k - 1` and the range `0 .. n - 1`: while the range has at least two values, partition it, count as above, and keep only the side that holds the target; stop when the target is inside the equal block. Return the value at the target. Store `[partitions, steps]`.
6. **External merge sort.** Cut the values into chunks of `memory` and sort each one into a run. Record the number of runs. While more than one run remains, group consecutive runs `ways` at a time, merge each group with a heap of `(value, run, position)` entries, replace the list of runs by the merged runs, and count a pass. Store `[runs, passes]` and return the one run, or an empty list.

### Correctness

Insertion sort keeps the invariant that `a[0 .. i - 1]` is sorted: the shifted values are exactly those larger than the key, and the key lands right after the last value that is not larger. Merge sort is correct because a merge of two sorted lists, always taking the smaller front, is sorted, and it is stable because on equal keys the left half, whose rows came first, goes first (inductively, each half is stable). The partition keeps the invariant that `a[low .. below - 1]` is smaller than the pivot, `a[below .. scan - 1]` is equal to it and `a[above + 1 .. high]` is larger, with `a[scan .. above]` not yet seen; each pass shrinks the unseen part by one, and the loop ends with the three blocks in place. The pivot is among the values, so the equal block is never empty and each recursion works on strictly fewer values. Quickselect is correct because the final position of the `k`-th smallest is `k - 1`, and the partition tells which block contains that position. The external sort is correct because each pass replaces groups of sorted runs by their sorted merges, and the number of runs falls from `r` to `ceil(r / ways)`, which reaches 1.

The counters are exact for the following reasons. In insertion sort, every shift is preceded by one comparison and the last comparison of each key either fails or does not exist, which gives the moves as the inversions. The partition loop takes one pass per value of the range, because every pass advances `scan` or lowers `above`, and the unseen part holds `high - low + 1` values at the start. Passes of the external sort number `ceil(log_w r)` for `r > 1` runs, with `w = ways`.

### Complexity

- Time: O(n^2) insertion sort, O(n log n) merge sort and quicksort, O(n) expected quickselect, O(n log w) per merge pass — insertion sort does up to n(n - 1) / 2 comparisons and moves. Merge sort has about log2(n) levels with n comparisons at most per level. Quicksort with a fixed pivot rule can be quadratic on a bad input, and the middle pivot makes sorted input the good case, not the bad one. Quickselect looks at a range that shrinks on every step, which is linear on average. A merge pass writes each of the n values once, and each write costs a heap operation on a heap of at most `w` entries.
- Space: O(n) — each sort works on a copy of the input, and the runs of the external sort together hold all the values. The heap holds at most `ways` entries.

### Trade-offs

Insertion sort is quadratic but needs no extra memory, is stable, and is fast on lists that are nearly sorted because its work follows the number of inversions. Merge sort has a guaranteed `n log n` bound and is stable, at the price of extra memory for the merge. Quicksort sorts in place and is fast in practice, is not stable, and has a quadratic worst case; the three-way partition keeps lists with many equal values from being a bad case. Quickselect finds one rank in expected linear time and does not sort the rest. The external sort is what is left when the data does not fit in memory: it reads and writes each value once per pass, so the number of passes, which falls with a bigger `ways` or more memory, is what to minimise. Knuth's volume 3 devotes section 5.4 to external sorting, for the many refinements.

### Pitfalls and edge cases

- Count only what the statement names. The loop test `j >= 0` is not a comparison, placing the key is not a move, and the rows copied after a merge side runs out are not comparisons.
- Use `>` for insertion sort and `<=` for the merge: a value equal to the key must not be moved past, and an equal key from the left half must go first. With the other operators the sort works but is no longer stable, and its counters change.
- Do not partition ranges with fewer than two values, and do not count them.
- The pivot is the value in the lower middle position at the time of the partition, not a value remembered from earlier.
- After a smaller value is swapped to `below`, `scan` advances; after a larger value is swapped to `above`, `scan` stays, because the value that came from `above` has not been looked at.
- `quickSelect` takes `k` from 1. The answer is the value at position `k - 1` of the sorted list, with equal values counted separately.
- The last run of the external sort can be shorter than `memory`, and the last group of a pass can have fewer than `ways` runs; a group of one run is copied. One run, or none, needs no pass.
- A sort returns a new list and does not change its input, and every sort replaces the meter.

### Language notes

- Python: `heapq` is a min-heap, so `(value, run, position)` tuples need no wrapper. Slicing makes the copies, and a stack of `(low, high)` tuples avoids deep recursion in the quicksort.
- TypeScript: there is no built-in heap, so the reference writes a small binary heap over `[value, run, position]` arrays. `Array.prototype.sort` needs a comparator for numbers (`(a, b) => a - b`), since without one it converts the elements to strings and compares those (`9` would sort after `80`). The class fields are declared without parameter properties.
- Java: `PriorityQueue<int[]>` with a comparator on the first two entries; `Arrays.sort` on an `int[]` sorts a run. `Arrays.copyOfRange` cuts the chunks, and the quicksort uses an `ArrayDeque` of ranges.
- Kotlin: `PriorityQueue` from `java.util` with `compareBy`; `chunked` cuts the input into runs and the runs into groups; destructuring a `Pair` or an `IntArray` reads the bounds.
- Go: `container/heap` needs a type that implements `heap.Interface`, so the reference defines `fronts`; its documentation describes it as a min-heap. `slices.Clone` and `slices.Sort` copy and sort, and `min` is a built-in. A nil slice encodes as an empty list.
- Rust: `BinaryHeap` is a max-heap, so entries are wrapped in `std::cmp::Reverse` to pop the smallest. Positions in the partition are `i32` because `below - 1` can be `-1` for an empty left block; they are cast to `usize` only to index. `slice::chunks` cuts the input into runs and the runs into groups, and `Vec::split_off` splits the rows for the merge sort.
