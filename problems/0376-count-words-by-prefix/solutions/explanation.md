# Count Words by Prefix: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| scan-words | brute | O(P * W * L) | O(1) | there are only a few words or a few prefixes |
| counting-trie | optimal | O((W + P) * L) | O(26 * W * L) | default answer; many prefixes are asked about the same words |

`W` is the number of words, `P` the number of prefixes and `L` the length of the longest word or prefix. Over a generated input with `n` words and `n` prefixes, the scan makes about n^2 comparisons and the trie reads about n * L letters.

## Approach: scan-words (Compare every prefix with every word)

### Intuition

The definition can be applied directly: for one prefix, look at every word and count the ones that begin with it. Doing that once for each prefix answers every question.

### Algorithm

1. For each prefix, in order, start a counter at 0.
2. For each word, add 1 to the counter if the word begins with the prefix.
3. The counter is that prefix's answer.

### Correctness

Step 2 applies the definition of "begins with" to every entry of `words`, repeats included, so the counter equals the number of entries that begin with the prefix. The answers are produced in the order of `prefixes`.

### Complexity

- Time: O(P * W * L) — each of the P prefixes is compared with each of the W words, and one comparison reads at most L letters.
- Space: O(1) — only a counter, apart from the answer itself.

### Trade-offs

It is the shortest correct solution and the right one when either list is short. Its cost grows with the product of the two lists, and it re-reads the same first letters of the words for every prefix. The trie reads each word once, whatever the number of prefixes.

### Pitfalls and edge cases

- A word counts as beginning with itself, so `"tea"` counts for the prefix `"tea"`.
- A prefix longer than a word never matches that word; the library's prefix test returns false there rather than failing.
- Repeated words are counted once per appearance. Collecting the words into a set first gives wrong answers.

### Language notes

- Python: `str.startswith` and a generator inside `sum`, since `True` adds as 1.
- TypeScript: `String.prototype.startsWith`.
- Java and Kotlin: `String.startsWith`; Kotlin's `count { ... }` on the array is the counter.
- Go: `strings.HasPrefix(word, prefix)`.
- Rust: `str::starts_with`; the closure borrows the prefix as `&str` with `as_str()`.

## Approach: counting-trie (A trie that counts the words passing through each node)

### Intuition

Words that begin alike share their first letters, and a prefix question only depends on those first letters. A trie stores each shared beginning once, as a path of nodes from a root. If every node also keeps the number of words that went through it, then the number of words beginning with a prefix is simply the counter of the node at the end of the prefix's path. The structure is described in Edward Fredkin's "Trie Memory" (Communications of the ACM 3(9):490-499, 1960, doi 10.1145/367390.367400), and the name comes from the word "retrieval".

### Algorithm

1. Create a root node. A node has one child slot per letter `a` to `z` and a counter `passing`, both empty at the start.
2. For each word, start at the root. For each letter, move to the child for that letter, creating the child if it is missing, and add 1 to that child's `passing`.
3. For each prefix, start at the root and move to the child for each letter. If a child is missing, the answer is 0. Otherwise the answer is the `passing` of the node where the prefix ends.

### Correctness

Invariant: after the words are inserted, the node reached from the root by the path of a string `s` exists exactly when some word begins with `s`, and its `passing` equals the number of entries of `words` that begin with `s`. Inserting a word adds 1 to the node of each of its prefixes, and to no other node, which keeps the invariant. A query follows the path of its prefix and reads the invariant at the end, or finds the path missing, which means that no word begins with the prefix.

### Complexity

- Time: O((W + P) * L) — each word is inserted in at most L steps and each prefix is walked in at most L steps.
- Space: O(26 * W * L) — at most one node per letter of every word, each with 26 slots; shared beginnings use fewer.

### Trade-offs

It spends memory on the tree to make each question cost only the length of the prefix, which pays off as soon as there are many prefixes. The 26-slot array per node is simple and fast for lowercase letters but wasteful for sparse data; a small map of children trades some speed for memory and also handles larger alphabets. Sorting the words and using binary search to find the range of words that begin with a prefix reaches a similar result without building a tree.

### Pitfalls and edge cases

- Add to the counter of each node on the path, not only of the last one; counting only where a word ends gives the number of words equal to the prefix.
- Querying must not create nodes: a missing child ends the walk with 0.
- A prefix longer than every word runs off the end of a path and must give 0, not an error.
- Repeated words add to the counters again, which is what the problem asks for.

### Language notes

- Python: `__slots__` keeps the many small nodes compact; the `for ... else` in the query loop runs its `else` only when no child was missing.
- TypeScript: `??=` creates the missing child and moves to it in one expression; `charCodeAt` avoids creating one-letter strings.
- Java: a nested `Node` class with a `Node[26]` array; `word.charAt(i) - 'a'` is the slot.
- Kotlin: `arrayOfNulls<Node>(26)`, and `node?.children?.get(...)` keeps the walk going as `null` once the path breaks off.
- Go: `children [26]*node` is an array of pointers, so a new node starts with all slots `nil`; `for _, letter := range word` yields runes and `letter - 'a'` is the slot.
- Rust: `#[derive(Default)]` on a node with `[Option<Box<Node>>; 26]` gives all-`None` slots, `get_or_insert_with(Box::default)` creates a missing child and returns it, and `as_deref()` reads a child without taking it.
