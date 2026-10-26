# Linked List Cycle: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| visited-set | brute | O(n) | O(n) | the first idea; memory is not a concern |
| fast-slow | optimal | O(n) | O(1) | default answer |

`n` is the number of nodes. Both approaches walk the list; they differ in how they notice that a node repeats.

## Approach: visited-set (Remember every node you have visited)

### Intuition

A walk around a loop must eventually return to a node it has already visited, and a walk along a healthy list never does. Keep a set of the nodes seen so far and stop at the first repeat.

### Algorithm

1. Start with an empty set and `node = head`.
2. While `node` is not null:
   1. If `node` is in the set, return `true`.
   2. Add `node` to the set and move to `node.next`.
3. Return `false`.

### Correctness

If the list has no loop, the walk visits n distinct nodes and reaches null, so the function returns `false`. If it has a loop, the walk enters it after at most n steps and, after at most n more, revisits the first node of the loop, which is already in the set, so the function returns `true`. The set holds node identities, so two distinct nodes with equal values never look like a repeat.

### Complexity

- Time: O(n) — every node is visited at most once before a repeat or null is found; set operations are O(1) on average.
- Space: O(n) — the set holds up to n node references.

### Trade-offs

Simple and robust, which makes it the oracle, and it extends naturally to finding where the loop starts (the first repeated node). Its O(n) memory is what the follow-up asks you to remove.

### Pitfalls and edge cases

- Storing values instead of nodes: `[6, 6, 6, 6]` without a loop would be reported as cyclic.
- The empty list returns `false` without entering the loop.

### Language notes

- Python: `ListNode` keeps the default identity-based `__hash__` and `__eq__`, so a `set[ListNode]` compares nodes, not values. A class that defined `__eq__` without `__hash__` would become unhashable.
- TypeScript: `Set<ListNode>` uses reference equality (SameValueZero) for objects.
- Java and Kotlin: `ListNode` does not override `equals` or `hashCode`, so `HashSet` falls back to identity. `add` returns `false` for an element already present, which combines the check and the insertion.

## Approach: fast-slow (Fast and slow pointers (Floyd))

### Intuition

Send two pointers from the head: `slow` moves one node per step, `fast` moves two. On a healthy list, `fast` simply runs off the end. On a list with a loop, both pointers eventually circle inside it, and since `fast` gains exactly one node per step, the gap between them shrinks by one each step until it is zero: they meet.

### Algorithm

1. Set `slow = fast = head`.
2. While `fast` and `fast.next` are not null:
   1. Move `slow` one node and `fast` two nodes.
   2. If they are the same node, return `true`.
3. Return `false`.

### Correctness

No loop: `fast` is always at least as far along as `slow`, so if they were ever equal after a move, the list would contain a node that `fast` reached twice, which is impossible without a loop. The fast pointer reaches null (or a node whose `next` is null) after about n / 2 steps, and the function returns `false`.

Loop of length `L` starting after `μ` nodes: after at most `μ` steps both pointers are inside the loop. Measure the distance from `fast` forward to `slow` around the loop, a number between 0 and `L - 1`. Each step moves `slow` by 1 and `fast` by 2, so the distance decreases by exactly 1. It reaches 0 within `L` further steps, at which point the pointers are the same node and the function returns `true`. Because the distance decreases by one, `fast` can never jump over `slow`.

### Complexity

- Time: O(n) — at most `μ + L ≤ n` iterations when there is a loop, about n / 2 when there is none.
- Space: O(1) — two references.

### Trade-offs

Constant memory and no modification of the list, which is the classic interview answer. The same pointers solve the follow-ups: after the meeting, a pointer restarted from the head and one left at the meeting point, both moving one step at a time, meet exactly at the loop's first node; counting steps around the loop from the meeting point gives its length. The visited set is easier to explain but costs O(n) memory.

### Pitfalls and edge cases

- Check `fast` and `fast.next` before moving: on an even-length healthy list, `fast` lands on null; on an odd-length one, `fast.next` is null.
- Compare after moving, not before: both pointers start at the head, so comparing first would always return `true`.
- Compare node identity (`is`, `===`, `==` on references), never values.

### Language notes

- Python: `slow is fast` compares identities; `==` would too here, but `is` states the intent and cannot be changed by an `__eq__` override.
- TypeScript: under `strict`, `slow` is typed `ListNode | null`; it is never null while `fast` is not, which the `slow!` assertion records.
- Java: `==` on object references is an identity comparison, which is exactly what is needed.
- Kotlin: `===` is referential equality; `==` calls `equals`, which happens to be identity for `ListNode` but would not be for a data class. `while (fast?.next != null)` also smart-casts `fast` to non-null inside the loop.
