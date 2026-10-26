# Word Dictionary With Wildcards: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| scan-words | brute | O(L) addWord, O(S) search | O(S) | few stored words, or patterns rarely contain dots |
| trie-dfs | optimal | O(L) addWord, O(26^k * L) search | O(26 * S) | default answer |

`L` is the length of the argument, `S` the total length of the stored words and `k` the number of dots in the pattern (at most 3 here).

## Approach: scan-words (Compare the pattern with every stored word of its length)

### Intuition

A pattern can only match words of its own length, and a match is a simple position-by-position comparison. Keep the stored words grouped by length, answer dot-free patterns by a set lookup, and compare a dotted pattern with every word of its length.

### Algorithm

1. Keep a map from length to the set of stored words of that length.
2. `addWord` adds the word to the set of its length.
3. `search`: take the set for the pattern's length. Without dots, test membership. With dots, return true if some word in the set agrees with the pattern at every non-dot position.

### Correctness

A stored word matches exactly when it has the pattern's length and agrees at every position where the pattern has a letter. The set for that length holds exactly the candidates, and the comparison tests the condition directly; a dot-free pattern matches only the identical word.

### Complexity

- Time: O(L) addWord, O(S) search — adding hashes the word; a dotted search may compare with every stored word of its length, up to the total stored length. Over a generated sequence of `n` calls that is about n^2 character comparisons.
- Space: O(S) — the stored words.

### Trade-offs

It is short and has no recursion. Grouping by length and the dot-free shortcut help, but a dotted search still scans every word of its length, which grows with the dictionary. The trie confines the work to the paths the pattern can follow.

### Pitfalls and edge cases

- Words of other lengths must never match; comparing with `zip` alone would accept a longer word whose first letters agree.
- A pattern made only of dots matches any word of its length.
- No stored word of the pattern's length: return false without error.

### Language notes

- Python: `defaultdict(set)` creates a bucket on first access, and `all(wanted in (".", letter) ...)` checks one pair of characters per step.
- TypeScript: a `Map<number, Set<string>>`; `includes(".")` picks the fast path.
- Java: `computeIfAbsent` builds buckets and `getOrDefault(..., Set.of())` avoids null checks.
- Kotlin: `getOrPut` builds buckets, and `?: return false` handles a missing length.

## Approach: trie-dfs (Trie searched depth-first with a branch at every dot)

### Intuition

Store the words in a trie. A letter in the pattern follows one edge, exactly as in a plain trie. A dot can be any letter, so it follows every existing edge: search the rest of the pattern from each child and succeed if any branch does. Only the paths that the pattern allows are explored.

### Algorithm

1. `addWord` inserts the word into a trie with 26 child slots per node and an end-of-word flag.
2. `search(pattern)` calls `matchesFrom(root, 0)`.
3. `matchesFrom(node, position)` walks the pattern from `position`: for a letter, move to that child or return false if it is missing; for a dot, return whether `matchesFrom(child, at + 1)` succeeds for some existing child. At the end of the pattern, return the node's end-of-word flag.

### Correctness

By induction on the remaining pattern length: `matchesFrom(node, i)` is true exactly when some stored word, whose prefix spells the path to `node`, continues so that its remaining letters match `pattern[i:]` and it ends there. At the end of the pattern that means the node itself ends a word, which is the flag. A letter forces the single matching child. A dot allows any letter, and the existing children are exactly the letters with which some stored word continues, so trying each of them and taking the disjunction is exact.

### Complexity

- Time: O(L) addWord, O(26^k * L) search — a letter costs one step, and each dot multiplies the number of explored paths by at most 26; with at most 3 dots that is a constant bound, and the search also never visits more nodes than the trie has.
- Space: O(26 * S) — at most one node per stored letter, each with 26 slots, plus O(L) recursion.

### Trade-offs

Searches cost only the paths the pattern allows, independent of how many words of other shapes are stored. Patterns with many leading dots are the worst case, which is why the constraints limit the dots. Memory per node is the same trade-off as in a plain trie: arrays are fast, maps are compact.

### Pitfalls and edge cases

- At the end of the pattern, check the end-of-word flag, not just that the path exists: `ca.` must not match a stored `cats`.
- A dot must branch over existing children only; recursing into missing children throws or wastes time.
- Return as soon as one branch succeeds; exploring the rest changes nothing.

### Language notes

- Python: the nested function closes over the pattern; `any(...)` stops at the first successful branch.
- TypeScript: `children.some(...)` stops at the first success; `??=` creates missing children while inserting.
- Java: a static helper receives the pattern and walks children with an enhanced `for` loop.
- Kotlin: `children.any { ... }` short-circuits, and `?: return false` ends the walk when a letter has no child.
