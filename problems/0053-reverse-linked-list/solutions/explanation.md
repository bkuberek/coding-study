# Reverse Linked List: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| value-array | brute | O(n) | O(n) | the first idea; nodes are values you may overwrite |
| iterative | optimal | O(n) | O(1) | default answer |
| recursive | optimal | O(n) | O(n) | the interviewer asks for recursion, and the list is short |

`n` is the number of nodes. Every approach must touch each node, so O(n) time is the floor; the approaches differ in how much memory they need and in whether they rewire links or move values.

## Approach: value-array (Copy the values out, then write them back reversed)

### Intuition

The list's values are just a sequence. Copy them into an array, then walk the list again and write the array back from its end. The nodes keep their order and links; only their values move.

### Algorithm

1. Walk the list from `head` and append every value to an array.
2. Walk the list from `head` again; at each node, pop the last value of the array into the node.
3. Return `head`.

### Correctness

After step 1 the array holds the values `v1, ..., vn` in list order. Popping from the end yields `vn, ..., v1`, and step 2 assigns them to nodes 1 to n in that order, so node `i` receives `v(n + 1 - i)`: exactly the reversed sequence. The links never change, so the result is still a valid list of n nodes starting at `head`.

### Complexity

- Time: O(n) — two passes over the list, each with O(1) work per node.
- Space: O(n) — the array holds every value.

### Trade-offs

Easy to get right, which makes it the oracle, but it misses the point of the exercise: it needs O(n) extra memory and does not reverse the structure. It also only works when callers do not hold references to particular nodes, because the node that held `v1` now holds `vn`. Interviewers almost always ask you to rewire the links instead.

### Pitfalls and edge cases

- An empty list: both loops do nothing and null is returned, which is correct.
- Popping from the front instead of the back (or using a queue) writes the original order back.

### Language notes

- Python: `list.pop()` removes from the end in O(1); `pop(0)` would be O(n).
- TypeScript: `values.pop()!` needs the non-null assertion because `pop` is typed `number | undefined`.
- Java: an `ArrayDeque<Integer>` used as a stack (`push`, `pop`) returns the values last in, first out; it boxes every value.
- Kotlin: `values.removeAt(values.lastIndex)` removes the last element; `removeLast()` would also work but resolves to a JDK 21 method on some toolchains, so the index form is the portable choice.
- Go: the second pass counts an index down from the last value instead of popping, which does the same job without shrinking the slice. Nodes are `*ListNode` values, so writing `node.Val` changes the caller's list.
- Rust: `Vec::pop` takes the values from the back in O(1). The first walk borrows the list immutably (`&head`), the second mutably (`&mut head`), and `head` itself is returned at the end, because only the values moved, not the nodes.

## Approach: iterative (Redirect every link in one pass)

### Intuition

Reversing a list means every `next` link should point at the node before it instead of the node after it. Walk the list once and redirect each link as you pass it. The only danger is losing the rest of the list when you overwrite a node's `next`, so save it first.

### Algorithm

1. Set `previous = null` and `current = head`.
2. While `current` is not null:
   1. Save `following = current.next`.
   2. Set `current.next = previous`.
   3. Move on: `previous = current`, `current = following`.
3. Return `previous`, the old tail and new head.

### Correctness

Invariant: at the top of each iteration, `previous` is the head of the already-reversed prefix (the nodes visited so far, linked backwards and ending in null), and `current` is the head of the untouched suffix. Initially the prefix is empty and the suffix is the whole list. One iteration moves `current` from the suffix to the front of the reversed prefix, keeping both parts intact because `following` was saved before the link was overwritten. When the suffix is empty, `previous` heads the reversal of the whole list.

### Complexity

- Time: O(n) — one iteration per node, each a constant number of pointer assignments.
- Space: O(1) — three references, whatever the list's length.

### Trade-offs

Optimal in time and memory, short, and immune to stack overflow. This is the answer interviewers expect, and the same three-pointer loop is a building block for many harder list problems (reverse in groups, reorder, palindrome check).

### Pitfalls and edge cases

- Overwriting `current.next` before saving it loses the rest of the list.
- Returning `head` instead of `previous`: the old head is now the tail.
- Empty and single-node lists need no special case: the loop runs zero or one time.

### Language notes

- Python: tuple assignment `previous, current = current, following` moves both references at once; the right side is evaluated before either name is rebound.
- TypeScript: the explicit `ListNode | null` annotation on `following` keeps the narrowing of `current` from leaking into its type.
- Kotlin: `current` is a local `var`, so the `while (current != null)` check smart-casts it inside the loop body; a property would not smart-cast.
- Go: `previous, current = current, following` is the same simultaneous assignment as Python's, and `var previous *ListNode` starts as the empty list.
- Rust: the list is owned, so each node is moved, never copied. `while let Some(mut node) = current` takes the node out of `current`, `node.next.take()` moves the rest of the list out and leaves `None` behind, and `node.next = previous` relinks it. No `unsafe` and no clone is needed.

## Approach: recursive (Reverse the rest, then hang the head at its end)

### Intuition

Suppose the rest of the list, starting at `head.next`, is already reversed. Its old first node, `head.next`, is now its tail. Append `head` after that tail and cut `head`'s own link, and the whole list is reversed. The empty list and the single node are already reversed.

### Algorithm

1. If `head` is null or `head.next` is null, return `head`.
2. Let `second = head.next`; reverse the list starting at `second` and remember the returned `newHead`.
3. Set `second.next = head` and `head.next = null`.
4. Return `newHead`.

### Correctness

By induction on the length. Lists of length 0 and 1 are their own reverse. For a longer list, the induction hypothesis says the recursive call returns the reversed suffix, which starts at the old tail and ends at `second`. Step 3 appends `head` after `second` and terminates the list at `head`, which yields the reverse of the whole list with the same new head.

### Complexity

- Time: O(n) — one call per node, each doing constant work.
- Space: O(n) — the recursion is n calls deep, one stack frame per node.

### Trade-offs

Elegant and a common follow-up question, but its stack depth equals the list length. That is why this problem caps lists at 3000 nodes: a list of 10^5 nodes would overflow the default stack in Node and the JVM, and Python's default recursion limit is 1000. Prefer the iterative version in production code.

### Pitfalls and edge cases

- Forgetting `head.next = null` leaves a two-node cycle between the old first two nodes.
- The base case must include the single node; with only the null check, step 2 would recurse on null and step 3 would dereference it.
- Every level returns the same `newHead`; only the deepest call finds it.

### Language notes

- Python: the default recursion limit is 1000 frames (`sys.getrecursionlimit()`); the runner raises it, but your own scripts would need `sys.setrecursionlimit`.
- Kotlin: `head?.next == null` covers both base cases in one check, and afterwards the compiler knows `head` is not null.
- Java and TypeScript: neither eliminates tail calls, and this recursion is not a tail call anyway, because work remains after the call returns.
- Go: the code is the same as Python's; `head.Next.Next = head` works because `head.Next` still points at the old second node, now the tail of the reversed rest.
- Rust: that line has no safe equivalent. The recursive call consumes the rest of the list (a `Box` has one owner), so afterwards there is no reference to its tail, and walking to the tail again would cost O(n) per level, O(n^2) in total. The reference passes the already-reversed part down instead, `reverse_onto(rest, reversed)`: one node moves per call, the depth is the list length, and time and stack stay O(n). It is the iterative loop written as recursion.
