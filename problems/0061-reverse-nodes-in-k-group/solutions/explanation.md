# Reverse Nodes in K-Groups: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| value-array | brute | O(n) | O(n) | as an oracle; does not relink the nodes |
| node-stack | intermediate | O(n) | O(k) | a straightforward relinking answer; small k |
| in-place | optimal | O(n) | O(1) | default answer |

`n` is the number of nodes and `k` the group size. Every approach visits each node a constant number of times, so all are linear; they differ in the extra memory and in whether they relink nodes (as the problem demands) or only move values.

## Approach: value-array (Copy the values, reverse each full chunk, write them back)

### Intuition

On an array the task is trivial: reverse each slice `[i, i + k)` that fits, and leave the short slice at the end alone. Copy the values into an array, do that, and write the values back into the nodes in order.

### Algorithm

1. Copy the values into an array.
2. For `start = 0, k, 2k, ...` while `start + k <= n`, reverse the slice `[start, start + k)`.
3. Write the array back into the nodes in list order and return `head`.

### Correctness

The full groups of the list are exactly the slices of step 2, and the leftover is the final slice shorter than `k`, which is not touched. Step 3 writes the i-th array value into the i-th node, so the list reads the rearranged sequence.

### Complexity

- Time: O(n) — copying, reversing (each value moves once) and writing back are all linear.
- Space: O(n) — the array of values.

### Trade-offs

Very hard to get wrong, which makes it the oracle, but it breaks the rule that the nodes, not the values, must move: a caller holding a reference to a node would see its value change. It also needs O(n) memory.

### Pitfalls and edge cases

- The loop bound must be `start + k <= n`; `start < n` would also reverse the leftover.
- `k = 1` reverses one-element slices, which changes nothing, as required.

### Language notes

- Python: slice assignment `values[a:b] = values[a:b][::-1]` reverses a chunk in place.
- Java: `Collections.reverse(values.subList(start, start + k))` reverses a view of the list, which writes through to the list.
- Kotlin: `chunked(k) { ... }` passes each chunk as a temporary window, so the reference copies the leftover chunk with `toList()` before the window is reused.

## Approach: node-stack (Pop each group of k nodes off a stack)

### Intuition

A stack reverses whatever you push onto it. Push the next `k` nodes, then pop them one by one and append them to the result: the group comes out reversed. If fewer than `k` nodes were available, attach them unchanged instead.

### Algorithm

1. Create a dummy result head; `tail = dummy`, `node = head`.
2. Repeat:
   1. Push up to `k` nodes starting at `node` onto a stack; `probe` is the node after the last one pushed.
   2. If fewer than `k` were pushed, link `tail.next = node` and return `dummy.next`.
   3. Pop every node, appending each after `tail`.
   4. Continue with `node = probe`.

### Correctness

Each full group is pushed in list order and popped in reverse, so it is appended reversed, and groups are appended in their original order. The final partial group is linked from its first node, unchanged. Every node's `next` is set exactly once by the appends or kept by the final link, and the last full group's last appended node is followed either by the next group or by the leftover (possibly null), so the list ends correctly.

### Complexity

- Time: O(n) — each node is pushed and popped at most once.
- Space: O(k) — the stack holds at most one group.

### Trade-offs

Relinks the nodes and is easy to explain, but uses O(k) memory, which is O(n) when `k = n`. It is a good stepping stone to the in-place version, which replaces the stack with pointer reversal.

### Pitfalls and edge cases

- The leftover must be linked even when it is empty, so that the last appended node does not keep a stale `next` that points back into the reversed group.
- The stack must be empty before each group; reusing it is fine because every full group pops it empty, and the partial case returns.

### Language notes

- Python: a list used as a stack with `append` and `pop`.
- TypeScript: `stack.pop()!` asserts non-empty inside the `length > 0` loop.
- Java: `ArrayDeque` as a stack (`push`, `pop`) is preferred over the legacy synchronized `Stack` class.
- Kotlin: `kotlin.collections.ArrayDeque` with `addLast` and `removeLast`.

## Approach: in-place (Reverse each full group between two anchors)

### Intuition

Reverse each group with the usual three-pointer list reversal, but anchored at both ends: the node just before the group (`before`) and the node just after it (`after`). Starting the reversal with `previous = after` makes the group's old first node point at `after` automatically; then `before` is linked to the group's old last node. The old first node is now the group's last, so it becomes `before` for the next group.

### Algorithm

1. Create `dummy` before the head and set `before = dummy`.
2. Repeat:
   1. Walk `k` nodes from `before` to find the group's last node `last`; if the list ends first, return `dummy.next`.
   2. Let `after = last.next` and `first = before.next`.
   3. Reverse the nodes from `first` to `last`, starting with `previous = after`.
   4. Link `before.next = last` and set `before = first`.

### Correctness

Invariant: before each iteration, the list from `dummy` to `before` is the final arrangement of the groups processed so far, and `before.next` starts the untouched rest. Step 1 confirms a full group exists; otherwise the untouched rest is the leftover, which must stay as it is, and the answer is complete. Step 3 reverses exactly the `k` group nodes, with the old first node now pointing at `after`; step 4 attaches the reversed group behind `before`. The new `before` (old `first`) is the last node of the arranged part, and its `next` is `after`, the start of the untouched rest, so the invariant holds.

### Complexity

- Time: O(n) — every node is visited twice: once by the look-ahead walk and once by the reversal.
- Space: O(1) — a fixed number of references and one dummy node.

### Trade-offs

Constant memory and true relinking: the answer interviewers are looking for. It has the most pointer bookkeeping of the three, so name the anchors (`before`, `first`, `last`, `after`) out loud before coding. A recursive version (reverse the first group, recurse on the rest) is shorter but uses O(n / k) stack, which is 10^5 frames for `k = 1`.

### Pitfalls and edge cases

- Check that a full group exists before reversing anything; reversing first and undoing later is much harder.
- Start the reversal with `previous = after`, not null, or the reversed group is cut off from the rest of the list.
- Advance `before` to `first` (the old first node), not to `last`.

### Language notes

- Python: `last` becomes None when the look-ahead walks off the end, which ends the function inside the loop.
- TypeScript: `after` is `null` for a group that ends the list, so the reversal loop tests `current !== null` as well as `current !== after`; typing `current` as `ListNode | null` keeps that honest.
- Kotlin: `before.next` is a platform type; annotating `first` as `ListNode` documents that a full group guarantees it is non-null, while `following` must stay `ListNode?` because the last node of the final group points at null.
- Java: identity comparison `current != after` is exactly what the loop needs; no null special case is required, since `after` may be null and `current` reaches it.
