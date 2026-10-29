# Sort a Linked List: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| insertion-sort | brute | O(n^2) | O(1) | tiny or nearly reverse-sorted lists |
| array-sort | intermediate | O(n log n) | O(n) | in practice, when values may be rewritten |
| top-down-merge | optimal | O(n log n) | O(log n) | default interview answer |
| bottom-up-merge | optimal | O(n log n) | O(1) | the follow-up asks for constant extra memory |

`n` is the number of nodes. Merge sort fits linked lists unusually well: merging needs only sequential access and relinks nodes without a buffer, while the array sorts it competes with (quicksort, heapsort) depend on random access.

## Approach: insertion-sort (Insert each node into a sorted prefix)

### Intuition

Build a sorted list one node at a time. Take each node of the input and walk the sorted list from its start until you find the first larger value, then splice the node in before it.

### Algorithm

1. Create a dummy head for the sorted list.
2. For each input node (save its `next` first):
   1. Start at the dummy and advance while the following sorted node's value is smaller than the node's value.
   2. Splice the node in after that position.
3. Return `dummy.next`.

### Correctness

Invariant: after processing `k` input nodes, the list after the dummy holds exactly those nodes, in non-decreasing order. Inserting the next node after the last sorted node with a smaller value (or right after the dummy if none) keeps everything before it smaller and everything after it at least as large, so the order is preserved.

### Complexity

- Time: O(n^2) — the k-th insertion walks up to k sorted nodes; about n^2 / 4 steps on random input and n^2 / 2 on ascending input.
- Space: O(1) — nodes are relinked, nothing is allocated.

### Trade-offs

Simple, in place and stable in spirit, and linear on input that arrives in descending order (every insertion is at the front). On random input it is quadratic: 10^4 nodes already take a few seconds in Python. Arrays can binary-search the insertion point; lists cannot, which is why this does not improve.

### Pitfalls and edge cases

- Save `node.next` before splicing; the splice overwrites it.
- Ascending input is the worst case here, because the walk starts at the head every time. Remembering the last insertion point and starting there when possible makes sorted input linear.

### Language notes

- Kotlin: the walk condition reads the Java field `spot.next` twice; it is a platform type, so the compiler accepts ``spot.next.`val` `` after the null check even though a field read cannot be smart-cast.
- Rust: the insertion point is a `&mut Option<Box<ListNode>>` cursor over the sorted prefix, advanced with `spot = &mut spot.as_mut().expect(..).next` under an `is_some_and` guard, which reads the next value without holding a borrow into the next iteration. `node.next = spot.take()` then `*spot = Some(node)` splices the node in.

## Approach: array-sort (Copy the values out, sort them, write them back)

### Intuition

Let the standard library do the sorting: copy the values into an array, sort it, and write the values back into the nodes in list order.

### Algorithm

1. Copy every value into an array.
2. Sort the array.
3. Walk the list again and assign the sorted values to the nodes in order.

### Correctness

The array holds the list's multiset of values, sorting orders them, and step 3 writes the i-th smallest value into the i-th node. The list's links never change, so the result is the same list structure holding the sorted sequence.

### Complexity

- Time: O(n log n) — two linear passes plus the library sort.
- Space: O(n) — the array of values.

### Trade-offs

Fast in practice (library sorts are tuned and cache-friendly) and the simplest correct code, which makes it the oracle. It is not what the problem asks for: it uses O(n) extra memory and rewrites values instead of relinking nodes, which matters when callers hold references to nodes or the payload is larger than an `int`.

### Pitfalls and edge cases

- An empty list: the array is empty and nothing is written.
- In TypeScript, `Array.prototype.sort()` without a comparator sorts numbers as strings.

### Language notes

- Python: `list.sort()` is TimSort, O(n log n) and very fast on partially sorted data.
- TypeScript: `Int32Array.from(values).sort()` sorts numerically with no comparator, because typed arrays compare their elements as numbers.
- Java: `Arrays.sort(int[])` is a dual-pivot quicksort on primitives (no boxing); the list is walked once to size the array.
- Kotlin: `IntArray(size) { ... }.apply { sort() }` builds and sorts a primitive array.
- Go: `slices.Sort` sorts the `[]int` in place (pattern-defeating quicksort, O(n log n), not stable, which is irrelevant for plain integers).
- Rust: `sort_unstable` on the `Vec<i32>`, then one `&mut` walk (`as_deref_mut`) writes the values back; the nodes stay in place, as in the other languages.

## Approach: top-down-merge (Merge sort: split at the middle, sort halves recursively)

### Intuition

Cut the list into two halves, sort each half recursively, and merge the two sorted halves. Finding the middle of a list costs a walk, but that walk is linear, the same cost as the merge, so it does not hurt the O(n log n) total.

### Algorithm

1. If the list has zero or one node, return it.
2. Find the end of the left half with `slow = head`, `fast = head.next`, moving `slow` one step and `fast` two steps while `fast` and `fast.next` exist.
3. Cut: `right = slow.next`, `slow.next = null`.
4. Sort both halves recursively and return the merge of the two results (the dummy-head merge from merging two sorted lists).

### Correctness

By strong induction on the length. Lists of length 0 or 1 are sorted. For length `n >= 2`, step 2 places `slow` at index `(n - 1) / 2` (integer division), so both halves are non-empty and shorter than `n`; starting `fast` at `head.next` is what guarantees that for `n = 2`. By the hypothesis both recursive calls return sorted lists of their halves, and merging two sorted lists gives a sorted list of all their nodes.

### Complexity

- Time: O(n log n) — the recursion has about log2 n levels, and each level does linear work in total to find middles and to merge.
- Space: O(log n) — the recursion depth; merges relink nodes and allocate only a dummy node per call.

### Trade-offs

The standard interview answer: it relinks the given nodes, is stable (ties take the left node first), and its O(log n) stack is about 16 frames for 5 * 10^4 nodes. The bottom-up variant removes the stack entirely but is longer and easier to get wrong.

### Pitfalls and edge cases

- Starting `fast` at `head` instead of `head.next` leaves a two-node list split into two nodes and zero nodes, and the recursion never ends.
- Forgetting the cut (`slow.next = null`) makes the left half still contain the right one.
- Use `<=` in the merge to keep the sort stable.

### Language notes

- Python: recursion depth is only about log2 n here, far from any limit.
- TypeScript: the explicit `ListNode | null` on `fast` keeps the type checker from narrowing it to non-null from its initializer.
- Kotlin: `head?.next == null` covers both base cases; afterwards `head` smart-casts to non-null.
- Rust: slow and fast pointers would be two `&mut` cursors into one list, so the split point comes from the length, counted once and passed down the recursion: the left half takes `length.div_ceil(2)` nodes, exactly where `fast = head.next` stops `slow`, and `next.take()` cuts the list. `merge` appends through `tail = tail.next.insert(node)`, which stores the node and returns a reference to it.

## Approach: bottom-up-merge (Merge sort: merge runs of doubling width)

### Intuition

Top-down merge sort spends its stack only on remembering where the halves are. Do the same merges in a different order instead: first merge neighbouring single nodes into sorted pairs, then neighbouring pairs into sorted runs of four, and so on. Each pass walks the list once, cutting off two runs, merging them and appending the result.

### Algorithm

1. Count the nodes; put a dummy before the head.
2. For `width = 1, 2, 4, ...` while `width < n`:
   1. Set `tail = dummy` and `rest = dummy.next`.
   2. While `rest` exists: cut off `left` (the next `width` nodes) and `right` (the following `width` nodes), let `rest` be what follows, merge `left` and `right` after `tail`, and move `tail` to the end of the merged run.
3. Return `dummy.next`.

### Correctness

Invariant: at the start of the pass with width `w`, the list is a sequence of sorted runs of length `w` (the last may be shorter). The pass merges runs pairwise, in order, and relinks the merged runs in the same order, so afterwards the list is a sequence of sorted runs of length `2w`. Initially every single node is a sorted run of length 1. When `w >= n`, one run covers the list, so the list is sorted.

### Complexity

- Time: O(n log n) — about log2 n passes, each linear: cutting, merging and finding the merged run's tail touch every node a constant number of times.
- Space: O(1) — a few references and one dummy node, no recursion.

### Trade-offs

Meets the strictest version of the problem: O(n log n) time with constant extra memory. The bookkeeping (cutting runs, keeping a tail across merges) is fiddly, so in an interview present the top-down version first and offer this as the follow-up.

### Pitfalls and edge cases

- `cutAfter` must handle runs shorter than `width` at the end of the list, returning null for the rest.
- After a merge, `tail` must move to the true end of the merged run, or the next merged pair overwrites part of it.
- The empty list and a single node skip the passes entirely because `width < n` fails at once.

### Language notes

- Python: helper functions with docstrings keep the three steps (cut, merge, advance tail) testable on their own.
- TypeScript and Kotlin: `mergeOnto` reassigns a local copy of `tail` because parameters are read-only in Kotlin and reassigning them in TypeScript hides intent.
- Java: the helpers are `static`, since they use no instance state.
- Rust: a pass takes the whole list out of `list` and rebuilds it behind a dummy node. `cut_run` moves one node at a time out of `rest` into a new run, so the cut costs O(width) like the walk it replaces and no node is ever reachable twice. `merge_onto` returns the tail as a `&mut ListNode` borrowed from its argument, which lets the next merge continue from it.
