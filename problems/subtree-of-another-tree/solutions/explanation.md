# Subtree of Another Tree: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| brute-force | brute | O(n * m) | O(h) | trees are small or values rarely repeat; the expected first answer |
| serialize-kmp | optimal | O(n + m) | O(n + m) | worst-case guarantees matter, for example many repeated values |

`n` is the number of nodes in `root`, `m` the number in `subRoot`, and `h` the height of `root`.

## Approach: brute-force (Same-tree check at every node)

### Intuition

`subRoot` is a subtree of `root` exactly when the tree hanging from some node of `root` is the same tree as `subRoot`. Deciding whether two trees are the same is easy, so try it at every node.

### Algorithm

1. If `root` is null, return false: an empty tree has no subtree to match.
2. If the tree at `root` is the same as `subRoot` (same shape and values, checked recursively), return true.
3. Otherwise return whether `subRoot` is a subtree of `root.left` or of `root.right`.

### Correctness

Every node of `root` is either `root` itself or a node of one of its subtrees, so the recursion tries every node as a candidate top. At each candidate the same-tree check answers exactly whether the subtree under it equals `subRoot`, because it compares both trees position by position, including where children are missing. The result is true if and only if some candidate matches.

### Complexity

- Time: O(n * m) — each of the `n` candidates may compare up to `m` nodes. On the generator's inputs most comparisons fail after one or two nodes, so the running time is close to linear; repeated values push it towards the worst case.
- Space: O(h) — the outer recursion and the comparison together never go deeper than the height of `root`: O(log n) for random trees and O(n) for a path.

### Trade-offs

It is short, obviously correct and fast on typical inputs, which makes it the standard interview answer. Its worst case is real, though: a large `root` full of equal values and a `subRoot` that almost matches everywhere makes almost every candidate compare almost all of `subRoot`.

### Pitfalls and edge cases

- Matching only the values near the top: the comparison must also fail when the candidate has extra descendants. Example 2 is that trap.
- Using `same` on the left and right children of the candidate instead of recursing with `isSubtree`: the match can be arbitrarily deep.
- Equal values: the first node with the right value may fail while a later one succeeds, so do not stop at the first value match.

### Language notes

- Python and TypeScript: short-circuiting `or` / `||` stops at the first matching candidate.
- Java: `a == b` in the base case compares references and is only used when one side is null.
- Kotlin: `===` is reference equality for the same null check; `` a.`val` `` needs backticks.
- Rust: both helpers take `&Option<Rc<RefCell<TreeNode>>>`, so `contains(&node.left, sub_root)` descends without cloning, and `same(root, sub_root)` reuses the borrowed `sub_root` for every candidate.

## Approach: serialize-kmp (Pre-order tokens matched with KMP)

### Intuition

Write each tree as its pre-order walk with an explicit marker for every missing child. That sequence describes the tree uniquely, and the walk of any subtree is one contiguous block of the walk of the whole tree. So `subRoot` is a subtree of `root` exactly when its token sequence occurs inside `root`'s token sequence, a pattern-matching question that KMP answers in linear time.

### Algorithm

1. Serialize both trees in pre-order: emit a node's value, then its left subtree, then its right subtree, and emit a marker for each missing child. The references use an explicit stack (push right, then left).
2. Build the KMP border table of the `subRoot` tokens: `border[i]` is the length of the longest proper prefix of `pattern[0..i]` that is also its suffix.
3. Scan the `root` tokens, extending the current match on equal tokens and falling back through the border table on a mismatch. Return true when the match reaches the full pattern length.
4. Return false after the scan.

### Correctness

A node's pre-order block is that node's value, the block of its left subtree and the block of its right subtree, so every subtree occupies a contiguous block that starts at the node's own token. If the subtree at node `x` equals `subRoot`, its block equals the pattern and the pattern occurs. Conversely, suppose the pattern occurs starting at position `i`. The first pattern token is a value, so position `i` is some node `x`, and `x`'s block also starts at `i`. A complete serialization is never a proper prefix of another complete serialization (reading tokens left to right, the walk knows exactly when the tree is finished), and both blocks are prefixes of the text from position `i`, so one is a prefix of the other and they are equal. Hence the subtree at `x` equals `subRoot`. KMP reports an occurrence if and only if one exists.

### Complexity

- Time: O(n + m) — each serialization visits every node and every missing child once (2n + 1 and 2m + 1 tokens), and KMP is linear in the pattern plus the text.
- Space: O(n + m) — both token sequences and the border table are stored.

### Trade-offs

It is linear in the worst case, including inputs full of repeated values, at the cost of linear extra memory and noticeably more code. It is a strong follow-up answer. Hashing each subtree bottom-up (a Merkle-style hash) is another linear approach, but it needs collision handling to be exact.

### Pitfalls and edge cases

- Leaving out the null markers breaks uniqueness: `[1, 2]` and `[1, null, 2]` both walk to `1, 2`.
- Matching characters of a text serialization without delimiters lets the value 2 match the end of 12. Comparing whole tokens (as the references do) or adding a delimiter before every value avoids it.
- The marker must not collide with a real value; the values are bounded, so a number outside the range works.
- Recursion is not needed: the explicit stack keeps even a path-shaped tree safe.

### Language notes

- Python: `None` is a natural marker in a list of tokens, and `==` compares `None` and integers safely.
- TypeScript: a numeric marker outside the value range keeps the array homogeneous; avoid `NaN`, which is not equal to itself.
- Java: `ArrayDeque` rejects null, so missing children are pushed as a shared placeholder node and recognized by reference. Tokens are converted to `int[]` so the matching loop compares primitives, never boxed `Integer` objects with `==`.
- Kotlin: `ArrayDeque<TreeNode?>` accepts nulls directly, and `toIntArray()` gives a primitive array for the scan; the marker lives in a `companion object` as a `const val`.
- Go: there is no optional integer, so a token is a small `token{val, missing}` struct. Structs of comparable fields compare with `==`, which is all the KMP loops need.
- Rust: `Vec<Option<i32>>` holds the tokens, with `None` for a missing child; `Option<i32>` implements `PartialEq`, so `pattern[i] != pattern[length]` compares markers and values alike.
