# Level Order Traversal: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| queue-levels | optimal | O(n) | O(n) | default answer; the natural breadth-first walk |
| dfs-depth | optimal | O(n) | O(n) | a depth-first walk is already at hand, or a follow-up asks for one |

`n` is the number of nodes. Both outputs hold all `n` values, so the output alone is O(n); the working memory beyond it is O(w) for the queue (`w` the widest level) and O(h) for the depth-first stack (`h` the height).

## Approach: queue-levels (Queue drained one level at a time)

### Intuition

A first-in, first-out queue visits nodes in breadth-first order: every node of one level comes out before any node of the next, and within a level the nodes come out left to right. The only extra need is knowing where each level ends, and the queue's length at the start of a level says exactly that.

### Algorithm

1. If `root` is null, return an empty list. Otherwise put `root` in a queue.
2. While the queue is not empty:
   1. Read the number `k` of nodes in the queue: that is the whole current level.
   2. Remove `k` nodes, appending each value to a new list and each non-null child to the back of the queue.
   3. Append the list to the result.
3. Return the result.

### Correctness

Invariant: at the start of each iteration the queue holds exactly the nodes of one level, left to right. It holds for the first level. Removing those `k` nodes in order and appending their children (left before right) leaves the next level in left-to-right order, because the children of a node that is further left on a level are further left on the next level. Every node is on exactly one level, so every value is emitted once, in the right list and position.

### Complexity

- Time: O(n) — each node is queued and removed once.
- Space: O(n) — the output holds every value; the queue itself never holds more than about one level plus part of the next.

### Trade-offs

It is the textbook answer and generalizes directly to the right-side view, zigzag order and bottom-up order. It never recurses, so tree height does not matter.

### Pitfalls and edge cases

- Reading the queue size inside the loop condition of the inner loop (for example `for i in range(len(queue))` written as a `while` on the live queue) mixes levels.
- An empty tree returns an empty list, not a list holding one empty level.
- Queue only non-null children.

### Language notes

- Python: `collections.deque` with `popleft()`; `range(len(queue))` is evaluated once, before the level is drained.
- TypeScript: the reference keeps the current level in an array and builds the next level in a fresh array, which avoids `Array.prototype.shift()` (linear on large arrays).
- Java: `ArrayDeque` with `add` and `poll`; the result type `List<List<Integer>>` boxes the values.
- Kotlin: `List(queue.size) { ... }` builds a level of exactly the current size, removing one node per element; the size is read once, when `List` is called.
- Go: `queue = queue[1:]` drops the front in O(1), and `for range len(queue)` fixes the level size before the body appends the children. An empty tree returns a nil `[][]int`, which the runner encodes as `[]`.
- Rust: `VecDeque` with `pop_front` and `extend(node.left.iter().cloned())`; `Vec::with_capacity(queue.len())` presizes each level.

## Approach: dfs-depth (Depth-first walk that appends by depth)

### Intuition

The output is a list of lists indexed by depth. Any walk that knows each node's depth can drop the value into the right list. The order within a level comes out left to right as long as the walk visits a left subtree before the right one, as pre-order does.

### Algorithm

1. Start with an empty list of levels and walk the tree in pre-order, carrying the depth (root at 0).
2. At each node, if `depth` equals the number of levels so far, append a new empty level.
3. Append the node's value to `levels[depth]`, then visit the left child and the right child with `depth + 1`.
4. Return the levels.

### Correctness

Every node is visited once and its value goes to the list of its own depth. For two nodes on the same level, pre-order visits first the one in the left subtree of their lowest common ancestor, which is also the one further left in the drawing, so each level comes out left to right. A level's list is created when its first (leftmost) node is reached; at that moment every shallower level already exists, because the walk reached this node through one node on each shallower level.

### Complexity

- Time: O(n) — one visit per node with O(1) amortized work.
- Space: O(n) — the output; the recursion (or the explicit stack in the Python reference) adds O(h).

### Trade-offs

Same time and output, smaller working memory on wide trees (O(h) instead of O(w)), but it depends on visiting left before right and, when recursive, on stack depth. It is a good answer to the "without a queue" follow-up.

### Pitfalls and edge cases

- Visiting the right child first (or pushing left before right on an explicit stack) reverses every level.
- Create a level only when `depth == levels.size`; a node can never be more than one level deeper than the deepest existing list.
- Deep trees: the 2000-level hidden path makes the recursion 2000 calls deep.

### Language notes

- Python: the reference uses an explicit stack of `(node, depth)` pairs and pushes the right child before the left, so the left child is popped first.
- TypeScript: a recursive arrow function closes over `levels`.
- Java: a static helper receives the result list as a parameter.
- Kotlin: a local `fun visit` closes over `levels`, typed `MutableList<MutableList<Int>>` and returned as `List<List<Int>>`.
- Go: `levels = append(levels, nil)` opens a level, and appending to a nil `[]int` allocates it on first use.
- Rust: the stack holds `(Rc<RefCell<TreeNode>>, usize)` pairs. `extend` with `map(|right| (Rc::clone(right), depth + 1))` pushes the children, right before left, so the left one pops first.
