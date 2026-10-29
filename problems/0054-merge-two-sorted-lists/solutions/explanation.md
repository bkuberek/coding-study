# Merge Two Sorted Lists: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| collect-sort | brute | O((m + n) log(m + n)) | O(m + n) | as an oracle; ignores the sortedness of the input |
| iterative | optimal | O(m + n) | O(1) | default answer |
| recursive | optimal | O(m + n) | O(m + n) | a short recursive answer is requested and the lists are short |

`m` and `n` are the lengths of the two lists. The two optimal approaches are the same merge step: take the smaller front node, repeat. They differ only in whether the repetition is a loop or a recursion.

## Approach: collect-sort (Collect every value, sort, build a new list)

### Intuition

Forget that the inputs are sorted: put every value into one array, sort it, and turn the array into a fresh list.

### Algorithm

1. Walk both lists and append every value to an array.
2. Sort the array.
3. Build a new list from the sorted values, appending behind a dummy head, and return the node after the dummy.

### Correctness

The array holds exactly the multiset of values of both lists, and sorting puts them in non-decreasing order. The new list has one node per array entry in array order, so its sequence is the sorted union of the inputs, which is the required result.

### Complexity

- Time: O((m + n) log(m + n)) — copying is linear, and sorting m + n values dominates.
- Space: O(m + n) — the array plus m + n new nodes.

### Trade-offs

Obviously correct, which is why it is the oracle, but it throws away the one fact that makes the problem easy: both inputs are already sorted. It allocates a whole new list, and its log factor grows with the input. In an interview it is only a starting point.

### Pitfalls and edge cases

- Both lists empty: the array is empty and the dummy's `next` is null, which is the right answer.
- Sorting numbers as strings (see the TypeScript note) would put `10` before `9`.

### Language notes

- TypeScript: `Array.prototype.sort` compares elements as strings unless given a comparator, so `(a, b) => a - b` is required.
- Java: `Collections.sort` on a `List<Integer>` sorts boxed values with a stable merge sort (TimSort).
- Kotlin: `ArrayList<Int>.sort()` is the in-place standard-library sort; `sorted()` would return a copy.
- Go: `slices.Sort` sorts the ints, and ranging over `[]*ListNode{list1, list2}` walks both lists with one loop. Each new node is a fresh `&ListNode{Val: value}`.
- Rust: the new list is built from its last node to its first (`values.iter().rev()`), so each new `Box` can own the list built so far through `next: merged` and no tail cursor is needed. `sort_unstable` sorts the `i32` values.

## Approach: iterative (Splice behind a dummy head)

### Intuition

The smallest remaining value is always at the front of one of the two lists. Repeatedly detach the smaller front node and append it to the result. When one list runs out, the other one's remaining nodes are already in order and can be attached as a block.

### Algorithm

1. Create a dummy node and set `tail = dummy`.
2. While both lists are non-empty:
   1. If `list1.val <= list2.val`, link `list1` after `tail` and advance `list1`; otherwise do the same with `list2`.
   2. Move `tail` to the node just linked.
3. Link whichever list is non-empty (or null) after `tail`.
4. Return `dummy.next`.

### Correctness

Invariant: the nodes from `dummy.next` to `tail` are the smallest values taken so far, in non-decreasing order, and every value left in either list is at least `tail.val`. Taking the smaller of the two fronts keeps it: both lists are sorted, so their fronts are their minimums, and the smaller front is the minimum of everything left. When one list is empty, the other list's remaining nodes are sorted and each is at least `tail.val`, so attaching them completes a sorted list of all m + n nodes.

### Complexity

- Time: O(m + n) — each loop iteration places one node, and the final link is O(1).
- Space: O(1) — the dummy node and a few references; the result reuses the input nodes.

### Trade-offs

Linear time and constant extra memory, with no recursion depth to worry about. It is the expected answer and the merge step of merge sort on lists (`sort-linked-list`) and of the pairwise approach to `merge-k-sorted-lists`. It relinks the input nodes, so the caller's original lists are consumed.

### Pitfalls and edge cases

- Forgetting to advance `tail` overwrites the same `next` link every time.
- Forgetting step 3 drops the leftover nodes of the longer list.
- Using `<` instead of `<=` is still correct, but `<=` takes ties from `list1` first, which keeps the merge stable.
- Without a dummy node, the first append needs a special case to set the head.

### Language notes

- Python: tuple assignment `tail.next, list1 = list1, list1.next` evaluates the right side first, so `list1.next` is read before `list1` moves.
- TypeScript: `first ?? second` picks the non-null leftover; `||` would also work for objects but `??` states the intent.
- Kotlin: the parameters are read-only, so the reference copies them into local `var`s; `first ?: second` attaches the leftover.
- Go: `tail.Next, list1 = list1, list1.Next` is a simultaneous assignment that reads `list1.Next` before `list1` moves, as in Python. There is no `??` operator, so the leftover is attached with an `if`/`else`.
- Rust: the borrow checker needs the splice in small steps. The comparison borrows both heads, then `smaller.take().unwrap()` detaches the smaller head from its list, `*smaller = node.next.take()` puts the rest back, and `tail` (a `&mut Box<ListNode>`) advances through `tail.next.as_mut().unwrap()`. `list1.or(list2)` attaches whichever list still has nodes.

## Approach: recursive (Keep the smaller head, merge the rest recursively)

### Intuition

The merged list starts with the smaller of the two heads. What follows it is the merge of everything else: the rest of that list and the whole other list. That is the same problem on fewer nodes.

### Algorithm

1. If `list1` is null, return `list2`; if `list2` is null, return `list1`.
2. If `list1.val <= list2.val`, set `list1.next` to the merge of `list1.next` and `list2`, and return `list1`.
3. Otherwise set `list2.next` to the merge of `list1` and `list2.next`, and return `list2`.

### Correctness

By induction on m + n. If either list is empty the other one is the answer. Otherwise the smaller head is the minimum of all values; by the induction hypothesis, the recursive call returns a sorted list of all other nodes, and putting the minimum in front of it gives a sorted list of all nodes.

### Complexity

- Time: O(m + n) — one call per merged node until one list runs out.
- Space: O(m + n) — the recursion depth equals the number of nodes placed before one list empties, up to m + n frames.

### Trade-offs

The shortest correct code, and easy to reason about by induction. The stack depth is the weakness: lists of 10^5 nodes would overflow typical stacks, which is why this problem caps the total at 3000 nodes. The iterative version does the same work in constant space.

### Pitfalls and edge cases

- Both base cases are needed; checking only one dereferences null.
- The recursive result must be assigned to the chosen head's `next`; returning it without linking loses the head.

### Language notes

- Python: each call is a full interpreter frame; the runner raises the recursion limit, but at the default limit of 1000 frames a 3000-node merge would raise `RecursionError`.
- Kotlin: `if` is an expression, so each branch links the rest and yields the chosen head as the function's result.
- Java and TypeScript: no tail-call elimination, and the call is not in tail position anyway, because its result is stored into `next` afterwards.
- Go: the same two-branch code as Python; the call depth is the number of nodes, at most 3000.
- Rust: `match (list1, list2)` with the or-pattern `(None, rest) | (rest, None)` covers both base cases. `first.next.take()` moves the tail out of the chosen node so it can be passed by value, and the result is stored back into `next`. The depth is at most 3000 frames, well inside the runner's thread stack.
