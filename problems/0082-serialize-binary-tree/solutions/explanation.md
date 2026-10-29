# Serialize and Deserialize a Binary Tree: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| preorder-markers | optimal | O(n) | O(n) | default answer; the shortest code |
| level-order | optimal | O(n) | O(n) | deep trees, or a format that matches the usual level-order notation |

`n` is the number of nodes. Both strings hold `2n + 1` tokens: one per node and one marker per missing child.

## Approach: preorder-markers (Pre-order values with a marker for every missing child)

### Intuition

A pre-order walk alone is ambiguous, because it does not say where a subtree ends. Writing a marker for every missing child fixes that: each subtree is written as its root, then its left subtree, then its right subtree, and every empty subtree is one marker. Reading the tokens back with the same recursion always knows what the next token means.

### Algorithm

1. `serialize`: walk in pre-order; write the value of each node and `#` for each null child; join the tokens with commas.
2. `deserialize`: split the string at the commas and read tokens with a recursive `read`: if the next token is `#`, return null; otherwise create a node with that value, then set its left child to `read()` and its right child to `read()`.
3. `serializeDeserialize` returns `deserialize(serialize(root))`.

### Correctness

By induction on the tree: `serialize` writes a tree `T` as the token block `B(T)`, which is `#` for an empty tree and `v, B(left), B(right)` otherwise. `read` called at the start of `B(T)` consumes exactly that block and returns a tree equal to `T`: for `#` it returns null; otherwise it creates the root with value `v`, then (by the induction hypothesis) the first `read` consumes `B(left)` and returns a copy of the left subtree, and the second consumes `B(right)` and returns a copy of the right subtree. Every node it returns is created by `read`, so the result shares no node with the input. The delimiter keeps multi-digit and negative values intact.

### Complexity

- Time: O(n) — each node and each missing child produces one token, and each token is parsed once.
- Space: O(n) — the string, the token list and the new tree; the recursion adds O(h).

### Trade-offs

It is the shortest correct format and the most common interview answer, and it streams naturally: decoding needs only a cursor. The recursion depth follows the tree height, which matters for very deep trees; the level-order format is iterative in both directions.

### Pitfalls and edge cases

- Leaving out the markers loses the shape: `[1, 2]` and `[1, null, 2]` would serialize alike.
- Joining values without a delimiter makes `1,2` and `12` indistinguishable; negative values add a `-` that must not be mistaken for a separator.
- The empty tree serializes to `#` and must decode to null, not to a node with a default value.
- Returning `root` from `serializeDeserialize` (skipping the round trip) is rejected by the tests: the result must not share nodes with the input.

### Language notes

- Python: `iter` over the split tokens and `next(tokens)` give a cursor without index bookkeeping.
- TypeScript: `Number(token)` parses negative values; the cursor is a `let` captured by the closure.
- Java: a `StringBuilder` builds the string; a small `Reader` class holds the token array and the cursor, because Java lambdas cannot mutate captured locals.
- Kotlin: `joinToString` and `split` handle the delimiter; `TreeNode(value).apply { left = read(); right = read() }` keeps the order left, then right, explicit.
- Go: a `strings.Builder` collects the text, and `read` is a closure over the token slice and the cursor (declared with `var read func() *TreeNode` first, because a closure cannot call itself by name before it exists). `node.Left = read()` then `node.Right = read()` are separate statements, so the order is fixed.
- Rust: `data.split(",")` is an iterator, so passing `&mut Split` down the recursion is the cursor, with no index. `node.left = read(tokens)` runs before `node.right = read(tokens)` because the statements are in that order. Nodes are built as plain `TreeNode` values and wrapped in `Rc<RefCell<..>>` once their children are set; `serialize` only reads, so it takes `node.borrow()`.

## Approach: level-order (Breadth-first values with a marker for every missing child)

### Intuition

Write the tree level by level, with a marker for every missing child of every real node. When reading back, a queue of the nodes built so far says exactly whose children the next two tokens are: they belong to the node at the front of the queue. It is the same idea as the level-order notation used in the tests, without trimming trailing markers.

### Algorithm

1. `serialize`: breadth-first from the root with a queue; for each real node write its value, and write `#` for every null child (the root counts as a child of nothing, so an empty tree is `#`).
2. `deserialize`: if the first token is `#`, return null. Otherwise create the root and queue it. While the queue is not empty, remove a node and read the next two tokens as its left and right children, creating and queueing a node for each value.
3. `serializeDeserialize` returns `deserialize(serialize(root))`.

### Correctness

`serialize` writes the root's token and then, for each real node in breadth-first order, the tokens of its two children. `deserialize` creates nodes in the same breadth-first order, because it queues each created node exactly when `serialize` queued the corresponding original node, and it reads each node's two child tokens in the same position where `serialize` wrote them. Induction on the queue position shows that the `i`-th created node has the value and children of the `i`-th original node, so the trees are equal. All nodes are newly created.

### Complexity

- Time: O(n) — `2n + 1` tokens are written and read once each.
- Space: O(n) — the string, the tokens, the queue (up to a level) and the new tree.

### Trade-offs

Iterative in both directions, so tree height never matters, and the format reads like the familiar level-order notation. It is slightly more code than the pre-order version, and decoding needs a queue instead of a single cursor.

### Pitfalls and edge cases

- Read exactly two tokens per dequeued node, including markers; skipping markers misaligns every later child.
- Queue only real nodes when decoding; markers have no children.
- The empty tree is the single token `#`.

### Language notes

- Python: `collections.deque` for both queues; values parse with `int`, which accepts a leading `-`.
- TypeScript: a read index into a growing array instead of `Array.prototype.shift()`.
- Java: `ArrayDeque` rejects null, so `serialize` writes markers for missing children instead of queueing them, and `StringJoiner` handles the separators.
- Kotlin: `ArrayDeque<TreeNode?>` accepts null children while serializing; `TreeNode(...).also(queue::addLast)` creates, queues and assigns a child in one expression.
- Go: a slice is the queue (`queue[0]` to read, `queue = queue[1:]` to pop, `append(queue, node.Left, node.Right)` to push). A nil `*TreeNode` fits in the slice, so the missing children need no special case while serializing.
- Rust: `VecDeque<Option<Rc<RefCell<TreeNode>>>>` holds missing children as `None`. Cloning an `Rc` into the queue only bumps a counter. While deserializing, the queue holds only real nodes, so `root.iter().cloned().collect()` seeds it from an `Option` and `left.iter().chain(right.iter()).cloned()` enqueues whichever children exist. The node is mutably borrowed only after the queue is extended.
