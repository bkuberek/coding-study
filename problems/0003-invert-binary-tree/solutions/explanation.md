# Invert Binary Tree: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| recursive | optimal | O(n) | O(h) | default answer; height is bounded |
| iterative-bfs | optimal | O(n) | O(w) | the tree may be very deep, or recursion is unwelcome |

`n` is the number of nodes, `h` the height and `w` the largest number of nodes on one level.

## Approach: recursive (Recursive swap)

### Intuition

The mirror of a tree is its root with the mirror of the right subtree on the left and the mirror of the left subtree on the right. That definition is already a recursive algorithm, with the empty tree as the base case.

### Algorithm

1. If `root` is null, return null.
2. Mirror the left subtree and remember the result.
3. Set `root.left` to the mirror of the right subtree.
4. Set `root.right` to the remembered mirror of the left subtree.
5. Return `root`.

### Correctness

By induction on the height. The empty tree is its own mirror. For a non-empty tree, the induction hypothesis says both recursive calls return correctly mirrored subtrees, and placing them on opposite sides is exactly the definition of the mirror at the root. Each node is the root of exactly one call, so every node gets its children swapped exactly once. A second swap would undo the first.

### Complexity

- Time: O(n) — one call per node plus one per null child (n + 1 of them), each doing O(1) work.
- Space: O(h) — the call stack holds one frame per level on the current path. That is O(log n) for the random trees the generator builds, and O(n) for a tree that is a single path.

### Trade-offs

It is the shortest correct solution and the one interviewers expect first. Its weakness is the call stack: a path-shaped tree of 10^5 nodes would need 10^5 frames, which overflows default stacks in every language here. That is why the constraints cap the height at 3000. Without that cap, prefer the queue-based version.

### Pitfalls and edge cases

- Overwriting before saving: `root.left = invert(root.right); root.right = invert(root.left)` reads the already replaced `root.left`, so both sides end up as the same subtree. Save one side first, or use a simultaneous assignment.
- An empty tree must return null, not throw.
- Skewed trees are the deep case: the hidden case with 2000 levels exercises recursion depth.
- Swapping values instead of links is wrong: a node's value stays, its subtrees move.

### Language notes

- Python: `root.left, root.right = invert_tree(root.right), invert_tree(root.left)` evaluates the whole right side before assigning, so no temporary is needed. CPython's default recursion limit is 1000. The runner raises it and runs cases on a thread with a large stack, but outside the runner a 2000-level tree raises `RecursionError`.
- TypeScript: Node's default stack holds several thousand simple frames, which is why test trees stay at or below 3000 levels. Compare with `=== null`.
- Java: the runner gives each case a thread with a 256 MiB stack. A plain `main` thread (often 512 KiB to 1 MiB) is much smaller.
- Kotlin: `root.left` is a platform type (`TreeNode!`) because `TreeNode` is a Java class. Declaring the function with `TreeNode?` keeps null checks explicit. The early `if (root == null) return null` smart-casts `root` to non-null for the rest of the body.

## Approach: iterative-bfs (Level-order swap with a queue)

### Intuition

Each node needs one swap, and the order of swaps does not matter, since swapping a node's links never changes which nodes are in its subtree. A queue visits every node level by level without using the call stack.

### Algorithm

1. If `root` is null, return null. Otherwise put `root` in a queue.
2. While the queue is not empty:
   1. Take the next node from the front.
   2. Swap its `left` and `right` links.
   3. Add each non-null child to the back of the queue.
3. Return `root`.

### Correctness

Every node enters the queue exactly once: the root at the start, and every other node when its parent is processed, since each node has one parent. Processing swaps that node's two links once. After the loop, every node has had its children swapped exactly once, which is the mirror image. Swapping a parent before its children is harmless: the children are queued as nodes, and their own links are swapped later, independently of which side they now hang on.

### Complexity

- Time: O(n) — each node is enqueued and dequeued once, with O(1) work per visit.
- Space: O(w) — the queue holds at most about one level and the start of the next, bounded by the widest level. That is at most about n/2 for a complete tree, and close to linear growth for the generator's random trees.

### Trade-offs

It handles any height, including a 10^5-node path, because it uses heap memory instead of the call stack. It is a few lines longer than the recursive version and uses more memory on wide, bushy trees (O(w) versus O(h)). Using a stack instead of a queue gives an iterative depth-first version with O(h) memory. Both are fine answers to the "no recursion" follow-up.

### Pitfalls and edge cases

- Queue only non-null children. A queue of nulls either crashes (Java's `ArrayDeque` rejects `null`) or needs extra checks.
- Return the original `root`, not the last processed node.
- An empty tree: do not enqueue null.

### Language notes

- Python: use `collections.deque` with `popleft()`. `list.pop(0)` shifts the whole list and makes the loop O(n^2).
- TypeScript: there is no built-in queue, and `Array.prototype.shift()` is O(n) on large arrays. The reference keeps a read index into an array that only grows. Destructuring `[node.left, node.right] = [node.right, node.left]` swaps without a temporary.
- Java: `ArrayDeque` is the standard queue (`add`, `poll`) and is faster than `LinkedList`, but it throws on `null` elements, so check children before adding them.
- Kotlin: `kotlin.collections.ArrayDeque` is the idiomatic queue (`addLast`, `removeFirst`). `node.left = node.right.also { node.right = node.left }` is the Kotlin swap idiom, and `node.left?.let(pending::addLast)` enqueues only real children.
