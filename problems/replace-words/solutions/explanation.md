# Replace Words with Roots: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| scan-roots | brute | O(W * D * L) | O(S) | there are only a few roots, or as a correctness oracle |
| trie | optimal | O(C + S) | O(C + S) | default answer |

Here `W` is the number of words, `D` the number of roots, `L` the length of the longest root, `C` the total number of letters in the roots and `S` the length of the sentence. The generator uses about `W / 4` roots, so the measured class of `scan-roots` on the ladder is `n^2`.

## Approach: scan-roots (Check every root against every word)

### Intuition

For each word, test every root as a prefix and keep the shortest one that matches.

### Algorithm

1. Split the sentence into words.
2. For each word, start with the word itself as the best replacement.
3. For each root, if the root is shorter than the best so far and the word starts with it, make it the best.
4. Join the replacements with single spaces.

### Correctness

Every root is considered for every word, and a root can replace a word only when the word starts with it. Among the matching roots the loop keeps the shortest, since a replacement happens only for a strictly shorter root. If no root matches, the best stays the word itself.

### Complexity

- Time: O(W * D * L) — each of the `W` words is checked against `D` roots, and a prefix test costs up to `L` letters.
- Space: O(S) — the words and the output.

### Trade-offs

No preprocessing and very little code. Sorting the roots by length would allow an early exit at the first match, but the reference scans them all to stay simple. With thousands of words and roots the work grows with their product.

### Pitfalls and edge cases

- Use a prefix test (`startsWith`), not a substring test: "apple" contains "p" but does not start with it.
- Prefer the shorter root when several match; the first root found is not necessarily the shortest.

### Language notes

- Python: `word.startswith(root)` and `" ".join(...)`.
- TypeScript: `String.prototype.startsWith`.
- Java: `sentence.split(" ")` takes a regular expression, and a single space is literal, so it is fine here. The result is built with a `StringBuilder`.
- Kotlin: `split(' ')` returns a `List<String>` and `joinToString(" ")` joins it back.
- Go and Rust: `best` holds a slice of the word or a root (a `string` in Go, a `&str` in Rust), so nothing is copied until the final `strings.Join` or `join(" ")`.

## Approach: trie (Trie of the roots walked once per word)

### Intuition

All the roots that are prefixes of a word lie on one path of the trie, and they appear on it in increasing length. So the first node on that path where a root ends gives the shortest root.

### Algorithm

1. Insert every root into a trie and mark the node where each one ends.
2. For each word, walk the trie letter by letter from the root.
3. Before moving on from a node, if a root ends there, return the part of the word read so far.
4. If the next letter has no child, return the word unchanged. If the word is used up, return it.
5. Join the results with single spaces.

### Correctness

The nodes visited by a word are exactly the trie nodes for its prefixes that are prefixes of some root, in increasing length. A root that is a prefix of the word ends at one of those nodes, so the first end mark seen is the shortest matching root. If the walk leaves the trie before any end mark, no root is a prefix of the word.

### Complexity

- Time: O(C + S) — `C` letters to build the trie, and at most `S` letters walked in total.
- Space: O(C + S) — the trie and the output.

### Trade-offs

The prefix-set alternative (put the roots in a set and test each prefix of a word) costs O(L^2) per word for slicing and hashing, and the trie does it in one pass over the letters. The trie costs memory for its nodes; a 26-slot array per node is fast but wasteful for sparse tries.

### Pitfalls and edge cases

- Check the end mark before moving to the next letter, and the word is returned unchanged when it ends first; a word equal to a root maps to itself.
- A root that extends another one (such as "pre" and "prefix") must never win, which the early return at the first end mark guarantees.

### Language notes

- Python: nested dicts with an end-marker key that is never a letter.
- TypeScript, Java and Kotlin: a node class with a 26-slot child array (`(TrieNode | null)[]`, `TrieNode[]`, `arrayOfNulls<TrieNode>(26)`) and a boolean `end`.
- Java and Kotlin build the result with `StringBuilder` or `joinToString`; the input has single spaces only, so nothing is trimmed or collapsed.
- Go: a node is `struct { children [26]*trieNode; end bool }`, where a nil pointer means "no child"; the words are lowercase ASCII, so indexing the string by byte is safe. `shorten` returns a slice of the word (`word[:length]`), which copies nothing.
- Rust: `children: [Option<Box<TrieNode>>; 26]` derives `Default` (arrays of up to 32 elements do), and `get_or_insert_with(Box::default)` creates the missing child while walking down with a `&mut` cursor. `shorten` returns a `&str` borrowed from the sentence, so no word is copied before the final `join`.
