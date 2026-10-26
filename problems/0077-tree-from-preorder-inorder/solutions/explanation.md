# Tree From Preorder and Inorder: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| linear-search | brute | O(n * h) | O(h) | a first version that follows the definition |
| index-map | optimal | O(n) | O(n) | default answer |

`n` is the number of nodes and `h` the height of the tree.

## Approach: linear-search (Recursive split with a linear search for each root)

### Intuition

The first pre-order value is the root. In the in-order list, the root separates the left subtree's values (before it) from the right subtree's values (after it), so its position gives the size of the left subtree. In the pre-order list, the left subtree's values come right after the root and the right subtree's after those. Each part is again a pre-order and in-order pair of one subtree, so the same split applies recursively.

### Algorithm

1. Define `build(preStart, inStart, size)` for the subtree whose walks are the `size` values starting at those positions; return null when `size` is 0.
2. The root value is `preorder[preStart]`. Scan the in-order range for it; its offset is `leftSize`.
3. Build the left subtree from `(preStart + 1, inStart, leftSize)` and the right subtree from `(preStart + 1 + leftSize, split + 1, size - leftSize - 1)`.
4. Return the root; the answer is `build(0, 0, n)`.

### Correctness

By induction on `size`. The pre-order walk of a subtree starts with its root, then lists the whole left subtree, then the whole right subtree; the in-order walk lists the left subtree, the root, then the right subtree. Values are distinct, so the scan finds the root's unique position, and the number of values before it is exactly the size of the left subtree. That determines the two sub-ranges in both lists, which are the walks of the two subtrees, so the recursive calls rebuild them correctly. Distinct values also make the tree unique, so this is the tree that was walked.

### Complexity

- Time: O(n * h) — the scan for a node's root covers at most its subtree, and a node lies in the subtrees of its `depth` ancestors. That is O(n log n) for the generator's random trees and O(n^2) for a path.
- Space: O(h) — index arithmetic instead of slicing keeps the extra memory to the recursion stack (plus the output tree).

### Trade-offs

It is the natural first answer and makes the key insight explicit. The linear scans make it quadratic on skewed trees. Slicing the arrays at every call (a common version of this approach) also copies O(n * h) values in total, which is why the references pass index ranges instead.

### Pitfalls and edge cases

- Off-by-one in the right part: it starts at `preStart + 1 + leftSize` in `preorder` and at `split + 1` in `inorder`.
- Empty input returns an empty tree.
- The scan relies on distinct values; with duplicates the walks would not determine one tree.

### Language notes

- Python: `inorder.index(value, start, end)` scans only the subtree's range, in C.
- TypeScript: a nested arrow function closes over both arrays; `new TreeNode(value)` uses the support class constructor.
- Java: the arrays are passed down explicitly to a static helper.
- Kotlin: a local `fun build` closes over the arrays, and `TreeNode(value).apply { left = ...; right = ... }` sets both children while returning the node.

## Approach: index-map (Value-to-position map and a pre-order cursor)

### Intuition

Two changes remove the repeated work. A hash map from each value to its in-order position replaces the scan. And the recursion visits roots in exactly pre-order (root, then the whole left side, then the whole right side), so instead of computing where each part starts in `preorder`, one shared cursor simply takes the next pre-order value whenever a new subtree is built.

### Algorithm

1. Map every value to its index in `inorder`.
2. Keep a cursor `nextRoot = 0` into `preorder`.
3. Define `build(low, high)` for the subtree whose in-order walk is `inorder[low, high)`: return null if the range is empty; otherwise take `value = preorder[nextRoot]`, advance the cursor, look up `split = position[value]`, build the left subtree from `(low, split)` and then the right subtree from `(split + 1, high)`.
4. Return `build(0, n)`.

### Correctness

The recursion calls `build` on subtrees in pre-order: a subtree's root is taken first, then its whole left subtree is built (taking all of its roots), then its whole right subtree. So whenever `build` takes a value from the cursor, that value is the next one in the pre-order walk, which is the root of the subtree being built, the same root the linear-search version finds by position. The map returns the same split position the scan would. The two versions therefore make identical decisions, and the first one is correct.

### Complexity

- Time: O(n) — one map entry per value, and one O(1) expected lookup and node per call.
- Space: O(n) — the position map; the recursion adds O(h).

### Trade-offs

Linear time and the expected answer. The shared cursor is elegant but makes correctness depend on building the left subtree before the right one; an explicit pre-order start index per call is longer but order-independent. An iterative version with a stack also exists and avoids recursion depth.

### Pitfalls and edge cases

- Building the right subtree before the left one consumes the cursor in the wrong order and produces a wrong tree.
- Reset the cursor per call of `buildTree` (the Java reference stores it in a field and resets it).
- The 2000-level hidden paths make the recursion 2000 calls deep.

### Language notes

- Python: `nonlocal next_root` lets the nested function advance the shared cursor.
- TypeScript: a `Map<number, number>` for positions and a closure over `let nextRoot`; `preorder[nextRoot++]` reads and advances.
- Java: there are no mutable closures, so the arrays, map and cursor are fields, set at the start of each call; the map is pre-sized to avoid rehashing.
- Kotlin: a local `fun build` captures and increments `var nextRoot`; `getValue` returns a non-null `Int`.
