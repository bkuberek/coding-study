# Implement a Trie: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| word-set | brute | O(L) insert and search, O(S) startsWith | O(S) | prefix queries are rare |
| array-trie | optimal | O(L) per operation | O(26 * S) | default answer; prefix queries are frequent |

`L` is the length of the argument of one call and `S` the total length of the stored words.

## Approach: word-set (A set of words scanned for prefixes)

### Intuition

A hash set already answers "was this exact word stored?" in time proportional to the word's length. For "does any stored word start with this prefix?", the set has no structure to exploit, so check every stored word.

### Algorithm

1. Keep a set of the stored words.
2. `insert` adds the word; `search` tests membership.
3. `startsWith` returns true as soon as some stored word starts with the prefix, and false after checking all of them.

### Correctness

The set holds exactly the stored words, so membership answers `search`. `startsWith` checks the definition directly against every stored word.

### Complexity

- Time: O(L) insert and search, O(S) startsWith — hashing and comparing a word costs its length; a prefix test may compare against every stored word. Over a generated sequence of `n` calls that makes about n^2 word comparisons.
- Space: O(S) — the stored words.

### Trade-offs

It is the smallest correct answer and fine when prefix questions are rare. It does not scale: every `startsWith` touches the whole collection. The trie trades memory for prefix queries that cost only the prefix's length.

### Pitfalls and edge cases

- A word counts as a prefix of itself.
- Duplicate inserts are harmless with a set.
- Queries on an empty collection return false.

### Language notes

- Python: `any(word.startswith(prefix) for word in self.words)` stops at the first match.
- TypeScript: `String.prototype.startsWith`; a `for...of` loop over the `Set` allows the early return.
- Java and Kotlin: `HashSet<String>` and `String.startsWith`; Kotlin's `any` also stops at the first match.

## Approach: array-trie (Trie with one child slot per letter)

### Intuition

Store words as paths from a root, one edge per letter, so all words that start with the same letters share the path of those letters. A flag on each node marks where a stored word ends. Both questions then only follow the letters of the argument: `search` asks whether the path exists and ends at a flagged node, `startsWith` only whether the path exists.

### Algorithm

1. Each node has 26 child slots, one per letter, and an `isWord` flag; the trie starts with an empty root.
2. `insert(word)`: from the root, for each letter move to the child for that letter, creating it when missing; set `isWord` on the last node.
3. `walk(text)`: from the root, follow the child for each letter; return null as soon as one is missing, otherwise the node reached.
4. `search(word)` is `walk(word)` exists and has `isWord`; `startsWith(prefix)` is `walk(prefix)` exists.

### Correctness

Invariant: a path from the root spelled by a string exists exactly when that string is a prefix of some stored word, and its last node is flagged exactly when the string itself was stored. Inserting a word creates the path of every prefix of the word and flags only the word's own node, which preserves the invariant. `walk` follows exactly the path of its argument, so the two queries read the invariant directly.

### Complexity

- Time: O(L) per operation — one array access (and at most one node creation) per letter.
- Space: O(26 * S) — at most one node per stored letter, each with 26 slots; shared prefixes reduce the count.

### Trade-offs

Every operation costs only the length of its argument, independent of how many words are stored, which is what tries are for. The fixed array per node wastes memory on sparse alphabets and does not extend to large alphabets; a hash map of children uses memory only for existing edges at a constant-factor time cost.

### Pitfalls and edge cases

- Setting `isWord` on every node of the path makes every prefix count as a stored word.
- `search` must check the flag; `startsWith` must not.
- A query longer than every stored word runs off the end of a path and must return false, not throw.

### Language notes

- Python: a small node class with `__slots__` keeps the many nodes compact; `ord(letter) - ord("a")` maps a letter to its slot.
- TypeScript: `node.children[index] ??= new TrieNode()` creates a missing child and moves to it in one expression; `charCodeAt` avoids creating one-letter strings.
- Java: a nested `Node` with a `Node[26]` array; `word.charAt(i) - 'a'` is the slot.
- Kotlin: `arrayOfNulls<Node>(26)`, `letter - 'a'` (a `Char` minus a `Char` is an `Int`), and `?: return null` exits the walk as soon as the path breaks off.
