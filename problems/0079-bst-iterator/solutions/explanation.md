# BST Iterator: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| flatten | brute | O(n) to build, O(1) per call | O(n) | memory is not a concern, or the values are needed again |
| controlled-stack | optimal | O(1) amortized per call | O(h) | default answer; memory proportional to the height |

`n` is the number of nodes and `h` the height of the tree.

## Approach: flatten (Flatten the in-order sequence up front)

### Intuition

An in-order walk of a binary search tree produces its values in increasing order. Run that walk once in the constructor, keep the values in a list, and hand them out with an index.

### Algorithm

1. In the constructor, walk the tree in order (left, node, right) and append each value to a list; set the position to 0.
2. `next`: return the value at the position and advance the position.
3. `hasNext`: return whether the position is still inside the list.

### Correctness

The in-order walk of a search tree lists every value exactly once in increasing order. The position counts how many values `next` has returned, so `next` returns them in that order and `hasNext` is true exactly while some value has not been returned.

### Complexity

- Time: O(n) to build, O(1) per call — the constructor visits every node once; afterwards each call is an index access.
- Space: O(n) — the list holds every value, plus O(h) recursion while it is built.

### Trade-offs

It is simple and every call is worst-case O(1), but it pays for the whole tree up front, even if only a few values are ever requested, and its memory grows with the number of nodes rather than with the height. Interviewers usually accept it as a first step and then ask for the O(h) version.

### Pitfalls and edge cases

- An empty tree: the list is empty and `hasNext` is false from the start.
- `hasNext` must not advance the position.
- The constructor walk recurses; the 2000-level hidden paths exercise that depth.

### Language notes

- Python: `has_next` is the snake_case name of `hasNext`; the method named `next` shadows the builtin only inside the class namespace, which is harmless.
- TypeScript: `this.values[this.position++]` reads and advances in one expression.
- Java: an `ArrayList<Integer>` boxes the values; an `int[]` sized by a counting pass would avoid that.
- Kotlin: the `init` block runs the walk; `values[position++]` mirrors the Java idiom.
- Go: `collect` is an unexported method; the runner reaches the class through the exported `NewBSTIterator`, `Next` and `HasNext` by reflection.
- Rust: `new` collects the values with a free function over `&Option<Rc<RefCell<TreeNode>>>`, so the iterator keeps no tree. The generated stub spells `next` and `has_next` with `&mut self`, and clippy's `should_implement_trait` would suggest `Iterator`; the problem fixes the method names, so the lint is allowed on `next`.

## Approach: controlled-stack (Stack of the pending left spine)

### Intuition

The iterative in-order walk keeps a stack of nodes it has reached but not yet visited. Instead of running that walk to the end, pause it between calls. The stack always holds the left spine of what remains: popping its top gives the next value, and the only work left is to push the left spine of that node's right subtree.

### Algorithm

1. Constructor: push `root` and then each left child down to the leftmost node.
2. `next`: pop the top node; push its right child and that child's left descendants (its left spine); return the popped node's value.
3. `hasNext`: return whether the stack is non-empty.

### Correctness

Invariant: the stack holds, from top to bottom, the not-yet-returned nodes whose left subtrees are fully returned or about to be returned, and the top is the smallest value not returned yet. After the constructor, the top is the leftmost node, the minimum. When `next` pops node `x`, everything smaller than `x` has been returned; the next larger value is the leftmost node of `x`'s right subtree if it exists, otherwise the nearest ancestor for which `x` is in the left subtree, which is the node below `x` on the stack. Pushing the left spine of `x.right` puts exactly the first candidate on top, so the invariant holds and values come out in increasing order. The stack is empty exactly when every node has been returned.

### Complexity

- Time: O(1) amortized per call — each node is pushed once and popped once over the whole iteration, so `n` calls to `next` do O(n) work in total. A single call may push up to `h` nodes.
- Space: O(h) — the stack holds at most one root-to-leaf path.

### Trade-offs

It meets the follow-up: memory proportional to the height and constant amortized time, with lazy work (values never asked for are never visited). An individual `next` is O(h) in the worst case, which matters only for strict latency bounds; Morris traversal reaches O(1) extra memory but temporarily modifies the tree.

### Pitfalls and edge cases

- Pushing only the right child, not its whole left spine, skips smaller values in that subtree.
- `hasNext` must be a pure check, with no pushes or pops.
- An empty tree leaves the stack empty, so `hasNext` is false immediately.

### Language notes

- Python: a list as a stack; `bool(self.stack)` is the emptiness test.
- TypeScript: the constructor takes a plain parameter and the stack is a field initialized in the class body; Node's type stripping rejects parameter properties such as `constructor(private root: TreeNode)`.
- Java: `ArrayDeque` with `push` and `pop`; it never holds null because `pushLeftSpine` stops at null.
- Kotlin: `ArrayDeque<TreeNode>` with `addLast` and `removeLast`; `next` and `hasNext` are ordinary methods here, not the `operator` functions of Kotlin's `Iterator`.
- Go: `pushLeftSpine` is an unexported method with a `for` loop whose post statement advances the cursor (`node = node.Left`).
- Rust: the stack holds `Rc<RefCell<TreeNode>>` clones, so the iterator owns what it needs and keeps the tree alive. `push_left_spine` takes the cursor by value and clones each left child out of the `borrow()` guard before pushing the current node. `#[allow(clippy::should_implement_trait)]` stays on `next`: the stub fixes the method name.
