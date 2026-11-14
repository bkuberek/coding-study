# Maximum Depth of a Binary Tree: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| recursive | optimal | O(n) | O(h) | default answer; height is bounded |
| level-count | optimal | O(n) | O(w) | the tree may be very deep, or recursion is unwelcome |

`n` is the number of nodes, `h` the height and `w` the largest number of nodes on one level.

## Approach: recursive (Recursive depth)

### Intuition

The deepest path from the root goes down into whichever subtree is deeper, so the depth of a tree is one (for the root) plus the larger of its two subtree depths. An empty tree has depth 0, which ends the recursion.

### Algorithm

1. If `root` is null, return 0.
2. Compute the depth of the left subtree and of the right subtree recursively.
3. Return 1 plus the larger of the two.

### Correctness

By induction on the height. An empty tree has no nodes on any path, so 0 is right. For a non-empty tree, every root-to-leaf path is the root followed by a root-to-leaf path of one subtree (or by nothing, when the root is a leaf and both subtrees return 0). The longest such path therefore has `1 + max(left depth, right depth)` nodes, and the induction hypothesis says both recursive calls return those depths correctly.

### Complexity

- Time: O(n) — one call per node and one per null child, each doing O(1) work.
- Space: O(h) — the call stack holds one frame per node on the current path. That is O(log n) for the random trees the generator builds and O(n) for a path-shaped tree.

### Trade-offs

It is a one-line recurrence and the answer interviewers expect first. Its cost is the call stack: a path of 10^5 nodes needs 10^5 frames, which is why the constraints cap the height at 3000. The level-by-level version has no such limit.

### Pitfalls and edge cases

- Counting edges instead of nodes: a single node has depth 1 here, not 0.
- An empty tree must return 0, not throw.
- Taking the depth of only the left (or only the right) subtree misses trees that grow on the other side; the path-shaped hidden cases catch this.
- Deep trees: the hidden case with 2000 levels exercises recursion depth.

### Language notes

- Python: the default recursion limit is 1000. The runner raises it and runs cases on a thread with a large stack, but the same code outside the runner fails on a 2000-level tree with `RecursionError`.
- TypeScript: Node's default stack holds several thousand simple frames, which is why test trees stay at or below 3000 levels.
- Java: the runner gives each case a thread with a 256 MiB stack; a plain `main` thread is much smaller.
- Kotlin: `root.left` is a platform type because `TreeNode` is a Java class; declaring the parameter `TreeNode?` keeps the null check explicit, and `maxOf` reads like `Math.max`.
- Go: goroutine stacks grow on demand (up to 1 GB by default), so a 3000-level recursion needs no special care, and the builtin `max` takes the two depths directly.
- Rust: a tree is `Option<Rc<RefCell<TreeNode>>>`, and the helper takes `&Option<Rc<RefCell<TreeNode>>>` so the recursion borrows each link instead of cloning an `Rc`. `node.borrow()` returns a shared guard that is released at the end of the arm. The runner gives each case a thread with a 256 MiB stack, far more than 3000 levels need; a stack overflow in Rust aborts the process instead of panicking.

## Approach: level-count (Count levels with a queue)

### Intuition

The depth is the number of levels. A breadth-first walk visits the tree one level at a time, so counting how many levels it processes gives the answer without using the call stack.

### Algorithm

1. If `root` is null, return 0. Otherwise start with a queue holding `root` and a counter at 0.
2. While the queue is not empty:
   1. Increase the counter: the queue holds exactly one whole level.
   2. Remove exactly as many nodes as the queue held at the start of this step, adding each node's non-null children to the back.
3. Return the counter.

### Correctness

Invariant: at the start of each iteration the queue holds exactly the nodes of one level, in order. It holds for the first level (the root). Draining exactly that many nodes and queuing their children leaves exactly the nodes of the next level, because every node on level `d + 1` is the child of one node on level `d`. The loop therefore runs once per level and stops after the deepest one, so the counter equals the number of levels, which is the depth.

### Complexity

- Time: O(n) — every node is queued and removed once, with O(1) work per visit.
- Space: O(w) — the queue holds at most one level plus part of the next. That is up to about n/2 for a complete tree and close to linear growth for the generator's random trees.

### Trade-offs

It handles any height, including a 10^5-node path, because the queue lives on the heap. On wide, bushy trees it uses more memory than the recursion (O(w) against O(h)). An explicit stack of (node, depth) pairs is a third option with O(h) memory and no recursion.

### Pitfalls and edge cases

- Read the level size before draining. Looping `while` the queue is non-empty inside one level mixes levels and counts only 1.
- Queue only non-null children; Java's `ArrayDeque` rejects `null`.
- An empty tree: do not enqueue null, return 0.

### Language notes

- Python: `collections.deque` with `popleft()`; `list.pop(0)` shifts the whole list on every call.
- TypeScript: there is no built-in queue and `Array.prototype.shift()` is linear on large arrays, so the reference builds a fresh array for each level instead.
- Java: `ArrayDeque` with `add` and `poll`, and a counter read before the inner loop.
- Kotlin: `level.flatMap { listOfNotNull(it.left, it.right) }` builds the next level in one expression; `listOfNotNull` drops the missing children.
- Go: `level = level[1:]` drops the front in O(1), with no shifting like JavaScript's `shift()`. When `append` runs out of capacity it copies only the live part into a new array, so memory stays O(w) amortized. `for range len(level)` evaluates the length once, before the loop body changes the slice.
- Rust: `VecDeque` is the queue (`pop_front`, `extend`); `node.left.iter().cloned()` clones the `Rc` of an existing child, which only bumps a counter. `for _ in 0..level.len()` fixes the level's size before the loop starts.
