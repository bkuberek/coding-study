# Remove Nth Node From End: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| node-array | brute | O(L) | O(L) | the first idea; random access makes the index arithmetic obvious |
| two-pass | optimal | O(L) | O(1) | simplest constant-memory answer |
| one-pass-gap | optimal | O(L) | O(1) | the interviewer asks for a single pass |

`L` is the length of the list and `n` the position from the end. The node to remove is at 0-based index `L - n` from the front; every approach finds its predecessor, at index `L - n - 1`, and relinks around it.

## Approach: node-array (Index every node in an array)

### Intuition

A linked list has no indexes, but an array of its nodes does. Collect the nodes, compute the index of the node to remove, and relink its predecessor.

### Algorithm

1. Put every node into an array `nodes`; let `target = L - n`.
2. If `target` is 0, the head is removed: return `nodes[0].next`.
3. Otherwise set `nodes[target - 1].next = nodes[target].next` and return `head`.

### Correctness

Position `n` from the end is index `L - n` from the front, because the tail (position 1) is index `L - 1`. Step 3 makes the predecessor skip exactly that node; every other link is unchanged, so the remaining nodes keep their order. When the target is the head, there is no predecessor, and returning the second node removes it.

### Complexity

- Time: O(L) — one pass to fill the array, then O(1) work.
- Space: O(L) — the array of node references.

### Trade-offs

Easy to reason about, but it pays O(L) memory for random access the problem does not really need. It is a fine first answer that leads straight to the two-pass version.

### Pitfalls and edge cases

- Removing the head needs its own branch here, because index `-1` does not exist (and in Python `nodes[-1]` silently means the tail).
- A one-node list with `n = 1` returns `nodes[0].next`, which is null: the empty list.

### Language notes

- Kotlin: `generateSequence(head) { it.next }.toList()` collects the nodes; `nodes[0].next` reads a Java field of platform type and may be null, which is fine as a `ListNode?` return.

## Approach: two-pass (Count the length, then walk to the predecessor)

### Intuition

The only thing the array gave us was `L`. Count the nodes in one pass, then walk `L - n` steps from a dummy node placed before the head: that lands exactly on the predecessor of the node to remove, even when that node is the head.

### Algorithm

1. Count the nodes: `length = L`.
2. Create `dummy` with `dummy.next = head`, and set `before = dummy`.
3. Advance `before` by `L - n` nodes.
4. Set `before.next = before.next.next` and return `dummy.next`.

### Correctness

From the dummy, which acts as index -1, `L - n` steps reach index `L - n - 1`: the predecessor of the node at index `L - n`, which is position `n` from the end. Step 4 skips that node. When `n = L`, zero steps leave `before` at the dummy, step 4 skips the head, and `dummy.next` is the new head.

### Complexity

- Time: O(L) — at most two passes over the list.
- Space: O(1) — a counter, the dummy node and one reference.

### Trade-offs

Constant memory and very hard to get wrong, which makes it the oracle. It walks part of the list twice; in practice that costs almost nothing, but interviewers like to ask for the one-pass version.

### Pitfalls and edge cases

- Without the dummy, removing the head needs a special case, and forgetting it is the most common bug in this problem.
- Return `dummy.next`, not `head`: after removing the head, `head` still points at the removed node.

### Language notes

- TypeScript: `before.next!` asserts what the counting guarantees: fewer than `L` steps never run off the list.
- Kotlin: `repeat(length - n) { ... }` reads as "walk this many steps"; `before` is a `var` captured by the lambda, which is fine because it is typed as non-null `ListNode`.

## Approach: one-pass-gap (Two pointers n nodes apart)

### Intuition

Instead of measuring the list, measure from its end: keep two pointers a fixed distance apart and slide them together. When the leading pointer falls off the end, the trailing one is exactly that distance from the end. A gap of `n + 1` positions puts the trailing pointer on the predecessor of the node to remove.

### Algorithm

1. Create `dummy` before the head; set `lead = trail = dummy`.
2. Move `lead` forward `n + 1` times.
3. While `lead` is not null, move both `lead` and `trail` one node forward.
4. Set `trail.next = trail.next.next` and return `dummy.next`.

### Correctness

Number the dummy as index -1 and the nulls after the tail as index L. After step 2, `lead` is at index `n` and `trail` at -1, a gap of `n + 1`. Step 3 keeps the gap and stops when `lead` reaches index L (null), so `trail` is at index `L - n - 1`, the predecessor of the node at index `L - n`. Because `n <= L`, step 2 never moves `lead` past index L.

### Complexity

- Time: O(L) — `lead` visits each node once; `trail` follows behind it.
- Space: O(1) — the dummy node and two references.

### Trade-offs

A single pass, which matters when the list is a stream you can only read once or when you are asked for it explicitly. It does the same total number of steps as the two-pass version, so it is not faster in any meaningful way; it is a showcase of the "fixed gap" two-pointer pattern, which also finds the k-th node from the end.

### Pitfalls and edge cases

- The gap must be `n + 1`, not `n`, so that `trail` stops on the predecessor; with a gap of `n` it stops on the node itself, which cannot be unlinked in a singly linked list.
- Starting both pointers at the dummy (not the head) is what makes `n = L` work.

### Language notes

- TypeScript: `lead!.next` in the first loop is safe because `n + 1 <= L + 1` steps from the dummy stay within the list or land on the final null.
- Kotlin: `for (step in 0..n)` runs `n + 1` times. A plain loop keeps `lead` a local that smart-casts in `while (lead != null)`; capturing it in a `repeat` lambda would disable the smart cast.
- Java: the same pointer arithmetic; `trail.next.next` may be null when the tail is removed, which is the correct new `next`.
