# Reorder List: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| tail-walk | brute | O(n^2) | O(1) | the first idea; tiny lists only |
| node-array | intermediate | O(n) | O(n) | quick, obviously correct linear answer |
| split-reverse-merge | optimal | O(n) | O(1) | default answer; constant extra memory |

`n` is the number of nodes. The difficulty is that the order consumes the list from both ends, and a singly linked list can only be walked forwards. The approaches differ in how they reach the back: by walking there every time, by indexing all nodes, or by reversing the back half once.

## Approach: tail-walk (Walk to the tail for every move)

### Intuition

The node that should follow the first node is the current tail. Walk to it, unhook it, and splice it in after the first node. Then do the same for the node after that splice, and so on.

### Algorithm

1. Set `current = head`.
2. While `current`, `current.next` and `current.next.next` all exist:
   1. Walk from `current` to the node just before the tail (`beforeTail`); let `tail = beforeTail.next`.
   2. Unhook the tail: `beforeTail.next = null`.
   3. Splice it in: `tail.next = current.next`, `current.next = tail`.
   4. Move on: `current = tail.next`.

### Correctness

Invariant: the nodes up to and including `current` are in their final order, and the nodes after `current` are the original middle section `Li, ..., Lj` still in original order. One round moves `Lj`, the last of them, directly after `current`, followed by `Li`, which is exactly the next two positions of the target order; then `current` advances to `Li`. When at most two nodes remain from `current` on, the remaining order is already right (`Li` then `Li+1` are the two middle nodes), so the loop can stop.

### Complexity

- Time: O(n^2) — the round that places the k-th tail walks about n - 2k nodes, about n^2 / 4 steps in total.
- Space: O(1) — a few references.

### Trade-offs

Constant memory and no helper structures, but quadratic: at 10^4 nodes it takes about 2.5 * 10^7 steps. It is useful only to see why the back of a singly linked list is the bottleneck.

### Pitfalls and edge cases

- The loop must stop when two nodes remain after `current`'s predecessor; otherwise it moves the tail in front of itself and creates a cycle.
- Unhook the tail (`beforeTail.next = null`) before splicing it, or the old link survives and closes a loop.

### Language notes

- TypeScript: the inner walk needs `beforeTail.next!` because `strict` cannot see that the loop guard keeps it non-null.
- Kotlin: `current?.next?.next != null` checks all three conditions at once and smart-casts `current` inside the loop; the Java fields are platform types, so `beforeTail.next.next` compiles without `?.`.
- Rust: a `Box` list has one owner per node, so the walk to the tail keeps a single `&mut Option<Box<ListNode>>` cursor (`cursor = &mut cursor.as_mut()?.next`) and `cursor.take()` detaches the tail at the end. `current` is a `&mut Box<ListNode>` that moves forward by reborrowing through the node it just relinked.

## Approach: node-array (Index the nodes, then relink from both ends)

### Intuition

The problem is easy for an array: take index 0, then n - 1, then 1, then n - 2, and so on. So copy the node references into an array once, then link the nodes in that order with two indexes moving towards each other.

### Algorithm

1. Put every node into an array `nodes`.
2. Set `left = 0` and `right = n - 1`.
3. While `left < right`:
   1. Link `nodes[left].next = nodes[right]`, then increase `left`.
   2. If `left == right`, stop.
   3. Link `nodes[right].next = nodes[left]`, then decrease `right`.
4. Set `nodes[left].next = null`; this node is the last one in the new order.

### Correctness

The links set in step 3 follow the target sequence `0, n-1, 1, n-2, ...` exactly: each node links to the next index in that sequence. The two indexes meet at the last node of the sequence (the middle node for odd n, the second middle node for even n), and step 4 terminates the list there, so the old links can no longer create a cycle. The array stores node references, so values are untouched.

### Complexity

- Time: O(n) — one pass to fill the array, one pass to relink.
- Space: O(n) — the array of n references.

### Trade-offs

Linear and hard to get wrong, which makes it the oracle. The extra array is what the optimal approach removes; in an interview this is a good first answer to state before improving the memory.

### Pitfalls and edge cases

- Forgetting step 4 leaves the old `next` of the final node in place, which points back into the list and creates a cycle.
- A single node: the loop does nothing and step 4 sets its `next` to null, which it already was.

### Language notes

- Kotlin: `generateSequence(head) { it.next }.toList()` collects the nodes in one line; the sequence ends at the first null.
- Java: `ArrayList<ListNode>` with `get` and field assignment; there is no boxing here because the elements are already objects.
- Rust: nodes own their successors, so a `Vec<&mut ListNode>` of every node cannot exist while the list is linked. The reference detaches each node into a `VecDeque<Box<ListNode>>` with `node.next.take()`, pops the front and the back alternately into a `Vec`, and relinks that order from the last node to the first, so each node takes over its successor.

## Approach: split-reverse-merge (Split at the middle, reverse the back half, interleave)

### Intuition

The target order takes the front half forwards and the back half backwards, alternately. Reverse the back half once, and both halves can be read forwards: the result is a simple interleave of two lists, the same zipper as merging, but alternating instead of comparing.

### Algorithm

1. Move `slow` one node and `fast` two nodes at a time while `fast.next` and `fast.next.next` exist. `slow` stops at the last node of the front half, index `(n - 1) / 2`.
2. Reverse the list that starts at `slow.next` (the back half) and cut it off with `slow.next = null`.
3. Interleave: with `front = head` and `back` the reversed half, while `back` exists, save both `next` links, link `front -> back -> front's old next`, and advance both.

### Correctness

After step 1, the front half has `ceil(n / 2)` nodes `L0 ... Lm` and the back half the remaining `floor(n / 2)` nodes. Reversing the back half yields `Ln-1, Ln-2, ...`. The interleave produces `L0, Ln-1, L1, Ln-2, ...`, the target order. The front half is at least as long as the back half, so `front` always exists while `back` does, and when `back` runs out, the remaining front node (odd n) or none (even n) already ends with null because of the cut in step 2.

### Complexity

- Time: O(n) — the middle search, the reversal and the interleave each make one pass over at most n nodes.
- Space: O(1) — a constant number of references; all three steps relink in place.

### Trade-offs

The expected answer, and a good test of fluency with three building blocks: fast and slow pointers, in-place reversal and splicing. It has more steps to get wrong than the node array, so state the plan before coding. It destroys the original order temporarily, which matters only if other code reads the list concurrently.

### Pitfalls and edge cases

- The middle loop condition decides the split: `fast.next and fast.next.next` leaves the front half one longer for odd n. The more common `fast and fast.next` stops one node later, which also works but puts the extra node in the back half.
- Forgetting the cut (`slow.next = null`) leaves the front half pointing into the reversed back half, which creates a cycle.
- Save both `next` links before relinking; overwriting `front.next` first loses the rest of the front half.

### Language notes

- Python: the reversal is a separate helper with an explicit `following` reference, which is easier to check than a three-way tuple assignment.
- TypeScript and Kotlin: on an even-length list, the last front node's `next` is null when the last back node is spliced in, so `front` becomes null in the same step as `back`. Typing `front` as nullable and testing both in the loop guard keeps the types honest; in Kotlin, typing `frontNext` as non-null `ListNode` compiles (the Java field is a platform type) but throws `NullPointerException` at exactly that step.
- Kotlin: `fast.next?.next != null` reads Java fields typed as platform types; annotating locals as `ListNode` or `ListNode?` makes the nullability explicit instead of relying on platform types.
- Rust: slow and fast would be two `&mut` cursors into one list, which the borrow checker rejects. The reference counts the nodes first, walks one cursor to node `(n - 1) / 2`, and cuts with `next.take()`: still O(n) time and O(1) extra space. Reversal and interleaving move links with `take()` instead of copying.
