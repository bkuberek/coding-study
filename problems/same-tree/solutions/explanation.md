# Same Tree: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| recursive | optimal | O(n) | O(h) | default answer; height is bounded |
| pair-stack | optimal | O(n) | O(h) | the trees may be very deep, or recursion is unwelcome |

`n` is the number of nodes in the smaller tree and `h` its height: both approaches stop at the first difference, so they never look further into the bigger tree.

## Approach: recursive (Compare roots then both subtrees)

### Intuition

Two trees are the same exactly when their roots hold the same value, their left subtrees are the same and their right subtrees are the same. That definition is the algorithm; the null cases are the base case.

### Algorithm

1. If either root is null, return whether both are null.
2. Otherwise return `p.val == q.val` and the result for the two left subtrees and the result for the two right subtrees, evaluated left to right with short-circuiting.

### Correctness

By induction on the height of `p`. If either tree is empty, the trees are the same exactly when both are empty, which step 1 returns. Otherwise both roots exist; the trees are the same if and only if the root values are equal and the corresponding subtrees are the same, because every position in a tree is either the root or a position inside one subtree. The recursive calls are on strictly smaller trees, so by the induction hypothesis they answer correctly.

### Complexity

- Time: O(n) — each call compares one pair of nodes and the calls follow positions present in both trees; the first difference ends the search.
- Space: O(h) — one frame per level on the current path: O(log n) for the generator's random trees, O(n) for a path-shaped tree.

### Trade-offs

It is the clearest answer and almost certainly the one expected. The only cost is the call stack on very deep trees, which the 3000-level constraint keeps safe here.

### Pitfalls and edge cases

- Comparing only values, for example by traversing both trees into lists, loses the shape: a left child and a right child of the same value would look equal. Example 2 shows this.
- One empty tree and one non-empty tree must give false, not a null dereference.
- Comparing `p == q` on nodes tests identity, not structure; only the null case may use it.

### Language notes

- Python: `p is q` in the base case is true only when both are `None`, because two distinct nodes are never the same object.
- TypeScript: `p === q` plays the same role; compare values with `===` too.
- Java: `p == q` compares references, which is what the null check needs, and `p.val == q.val` compares `int` values.
- Kotlin: `===` is reference equality, used for the null check; `` p.`val` `` needs backticks because `val` is a keyword.
- Go: pointers compare with `==`, so `p == q` after the `nil` check is true only when both are `nil`: two distinct nodes are never the same pointer.
- Rust: matching on the pair of references, `match (p, q)`, spells out the three cases (both empty, both present, one empty) and needs no identity test. Both guards are shared `borrow()`s, so passing the same tree twice would also work.

## Approach: pair-stack (Explicit stack of node pairs)

### Intuition

The recursion only ever compares a pair of corresponding positions and then schedules their two child pairs. An explicit stack of pairs does the same scheduling on the heap, so the depth of the tree no longer matters.

### Algorithm

1. Push the pair `(p, q)` onto a stack.
2. While the stack is not empty:
   1. Pop a pair `(a, b)`.
   2. If both are null, continue.
   3. If exactly one is null, or their values differ, return false.
   4. Push `(a.right, b.right)` and `(a.left, b.left)`.
3. Return true.

### Correctness

Every pair pushed is a pair of nodes at the same position in the two trees, starting with the roots, because children are paired side by side. Every position that exists in either tree is eventually popped unless the algorithm returned false earlier: a position is pushed when its parent position matched. If a mismatch exists at some position, all its ancestor positions match, so it is pushed and popped and the algorithm returns false. If no mismatch exists, every pop passes and the loop ends with true.

### Complexity

- Time: O(n) — each pair is pushed and popped once, and pairs only exist below positions that matched.
- Space: O(h) — popping a pair pushes its two child pairs, so the stack holds at most one pending sibling pair per level plus the current pair.

### Trade-offs

It is immune to deep trees and stops at the first difference like the recursion, at the price of a few more lines. A queue instead of a stack gives a level-by-level comparison with O(w) memory; the result is the same.

### Pitfalls and edge cases

- Handle the null pairs before reading `val`.
- Push matching sides together: `(a.left, b.left)`, never `(a.left, b.right)`, unless the task is mirror comparison.
- Two empty trees: the first pop is `(null, null)` and the loop ends with true.

### Language notes

- Python: a list used as a stack (`append`, `pop`) and tuples for the pairs; `None` pairs are fine.
- TypeScript: an array of tuples typed `[TreeNode | null, TreeNode | null][]`; `pop()!` asserts the stack is not empty.
- Java: `ArrayDeque` rejects `null`, so the reference checks a pair's children before pushing and only pushes pairs of two real nodes, as `TreeNode[]` arrays.
- Kotlin: `kotlin.collections.ArrayDeque` accepts nullable elements, so `Pair<TreeNode?, TreeNode?>` with `to` and destructuring keeps it close to the Python version.
- Go: a slice of small `pair` structs is the stack; unlike Java's `ArrayDeque`, it accepts `nil` pointers, so pairs of missing children are pushed and skipped like in Python.
- Rust: the stack is a `Vec<(Option<Rc<RefCell<TreeNode>>>, Option<Rc<RefCell<TreeNode>>>)>`. The children are cloned (a counter bump) before they are pushed, because the `Ref` guards that gave access to them end with the iteration.
