# Kth Smallest in a BST: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| sort-values | brute | O(n log n) | O(n) | the tree is not known to be a search tree, or as a first answer |
| inorder-stack | optimal | O(h + k) | O(h) | default answer; uses the search-tree order |

`n` is the number of nodes and `h` the height of the tree.

## Approach: sort-values (Collect every value and sort)

### Intuition

The question is about ranks among the values, and sorting answers any rank question. Collect every value, sort, and index. It ignores the search-tree property entirely, which is exactly what makes it a useful baseline.

### Algorithm

1. Visit every node (any order; the references use an explicit stack) and collect its value.
2. Sort the values in increasing order.
3. Return the value at index `k - 1`.

### Correctness

The sorted list holds every value of the tree exactly once, in increasing order, so its element at position `k - 1` is by definition the `k`-th smallest value.

### Complexity

- Time: O(n log n) — the walk is O(n) and the sort dominates.
- Space: O(n) — every value is stored.

### Trade-offs

It works for any binary tree, not only search trees, and it is hard to get wrong. It always touches every node and pays for a sort that the search-tree order makes unnecessary.

### Pitfalls and edge cases

- `k` is 1-based: index `k - 1`.
- In TypeScript, `sort()` without a comparator compares numbers as strings (so 10 sorts before 9).

### Language notes

- Python: `list.sort()` sorts numbers numerically.
- TypeScript: pass `(a, b) => a - b` to `sort`; the values stay within ±10^9, so the subtraction is exact.
- Java: the reference counts the nodes first so the values fit in an `int[]`, which `Arrays.sort` sorts without boxing.
- Kotlin: `removeLast() ?: continue` skips null children pushed onto a nullable `ArrayDeque`; `sorted()` returns a new list.

## Approach: inorder-stack (In-order walk that stops at the kth node)

### Intuition

In a binary search tree, an in-order walk (left subtree, node, right subtree) visits the values in increasing order. The `k`-th node it visits holds the answer, so walk in order and stop there. An explicit stack makes the early stop trivial.

### Algorithm

1. Start with an empty stack and `node = root`.
2. Repeat:
   1. Push `node` and move left until `node` is null.
   2. Pop a node and decrease `k`; if `k` reached 0, return its value.
   3. Move to its right child.

### Correctness

The loop is the standard iterative in-order walk: a node is popped only after every node of its left subtree, and its right subtree is walked before any ancestor that is still on the stack. For a search tree this order is increasing, so the `j`-th popped node holds the `j`-th smallest value. Since `1 <= k <= n`, the walk pops at least `k` nodes before running out, so it returns the `k`-th smallest value.

### Complexity

- Time: O(h + k) — the walk first goes down to the minimum (up to `h` pushes) and then performs `k` pops, each followed by at most a short descent; every push is matched by a pop or by the final stack contents, which are bounded by the height.
- Space: O(h) — the stack holds at most one root-to-leaf path.

### Trade-offs

It uses the search-tree order to avoid both the sort and most of the tree when `k` is small. The follow-up (frequent updates and queries) is answered by storing subtree sizes in each node, which lets a query walk one root-to-leaf path in O(h).

### Pitfalls and edge cases

- `k = 1` is the leftmost node, possibly at the bottom of a long left path; the hidden 2000-level cases test both ends.
- A recursive in-order walk needs a way to stop early (a counter plus an "answer found" check), or it keeps walking after finding the answer.
- Decrement `k` when a node is popped, not when it is pushed.

### Language notes

- Python: a list as a stack; the `while True` loop always returns because `k <= n`.
- TypeScript: `for (;;)` with a return inside; `pop()!` asserts a node is available.
- Java: `ArrayDeque` with `push` and `pop`; `--remaining == 0` combines the decrement and the test.
- Kotlin: `ArrayDeque` with `addLast` and `removeLast`; the compiler accepts `while (true)` without a trailing return because the loop never completes normally.
