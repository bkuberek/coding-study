# Serialize and Deserialize a Binary Tree

## Statement

A binary tree has to be stored in a file or sent over a network, and only text can travel. Design a format that turns any binary tree into a single string and turns that string back into an identical tree: the same shape and the same value at every position.

Write two helpers and one function that connects them:

- `serialize(root)` turns a tree into a string.
- `deserialize(data)` turns such a string back into a tree, built from new nodes.
- `serializeDeserialize(root)` returns `deserialize(serialize(root))`.

The tests call `serializeDeserialize` and compare the tree it returns with the input. The round trip must really go through your string: `deserialize` may use only the string that `serialize` produced, with no shared variables or other side channels, and the returned tree must consist entirely of new nodes. Returning the input tree, or any node of it, is rejected. The format is up to you; values can be negative and can repeat.

Reference: this is our own wording of LeetCode problem 297, [Serialize and Deserialize Binary Tree](https://leetcode.com/problems/serialize-and-deserialize-binary-tree/).

## Input

- `root`: the root of the tree to send, or null for an empty tree. Trees are written in level order, top to bottom and left to right, with `null` marking a missing child; trailing `null` entries are omitted.

## Output

The root of the tree rebuilt by `deserialize` from the string produced by `serialize`: a tree of new nodes equal to `root`, written in the same level-order form.

## Examples

### Example 1

<!-- case: ex1 -->

The rebuilt tree has the same shape (11 has only a left child, 3 only a right child) and the same values, so it is written exactly like the input. One possible string is `7,3,#,5,#,#,11,9,#,#,#`, a pre-order walk with `#` for each missing child.

### Example 2

<!-- case: ex2 -->

An empty tree must survive the round trip too: its string might be just `#`, and decoding it gives back an empty tree.

## Constraints

- The tree has between `0` and `10^5` nodes.
- `-1000 <= node value <= 1000`; values may repeat.
- The tree has at most `3000` levels.

## Follow-ups

- Which traversals can describe a tree on their own, and what do they need to record about missing children?
- How compact can the string be? Could you avoid writing a marker for every missing child?

## Hints

### Hint 1

A pre-order walk alone does not determine a tree: `[1, 2]` and `[1, null, 2]` both walk to `1, 2`. What extra information removes the ambiguity?

### Hint 2

Write a marker such as `#` for every missing child. A pre-order walk with markers is then unambiguous: while reading it back, you always know whether the next token is a node or the end of a subtree.

### Hint 3

Decode with the same recursion that encoded: read a token; if it is the marker, return null; otherwise create the node, then read its left subtree, then its right subtree. Separate tokens with a delimiter so that multi-digit and negative values can be told apart.
