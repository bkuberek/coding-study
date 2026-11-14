# Word Break: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| memoization | intermediate | O(n * m * L) | O(n) | you reason from the first word; the dictionary is small |
| tabulation | optimal | O(n * L^2) | O(n + D) | default answer |
| trie | optimal | O(n * L + D) | O(n + D) | the dictionary is large or words are long |

Here `n` is the length of `s`, `m` the number of words, `L` the length of the longest word and `D` the total number of letters in the dictionary. The question "can `s[i..]` be split?" depends only on `i`: whatever words covered `s[0..i)`, the rest must be split on its own. So there are only `n + 1` subproblems, one per position.

The naive recursion tries every dictionary word that matches at the current position and recurses on the rest, without remembering failures. On `"aaa...ab"` with the words `"a"`, `"aa"` and `"aaa"`, every one of the exponentially many ways to split the run of `a`s ends at the `b` and fails; with 30 `a`s that is tens of millions of calls. It is the first step of the progression and is not a separate reference here.

## Approach: memoization (Top-down try every word at each position)

### Intuition

Let `canSplitFrom(i)` mean "the suffix starting at `i` can be split". If some word `w` matches `s` at `i` and `canSplitFrom(i + |w|)` holds, the answer is yes. The naive recursion asks about the same `i` along many paths; remembering both successes and failures per position makes each one cost a single pass over the dictionary.

### Algorithm

1. `canSplitFrom(n)` is true: the empty suffix needs no words.
2. Otherwise return the cached answer for `i` if there is one.
3. For each word `w`: if `s` starts with `w` at `i` and `canSplitFrom(i + |w|)`, cache and return true.
4. Cache and return false.
5. Return `canSplitFrom(0)`.

### Correctness

By induction from the end of `s`. A split of `s[i..]` starts with some word `w` that matches at `i`, followed by a split of `s[i + |w|..]`; the loop tries every candidate first word and, by the induction hypothesis, gets the right answer for each remainder. If no candidate works, no split exists. Caching cannot change answers because they depend only on `i`.

### Complexity

- Time: O(n * m * L) — each of the `n` positions is evaluated once; it compares up to `m` words, each match costing up to `L` character checks.
- Space: O(n) — the cache and a recursion up to `n` frames deep (one frame per word in the split being explored).

### Trade-offs

The most natural derivation. Its cost grows with the dictionary size `m`, which can be 1000 here; when the dictionary is large, looking up substrings in a hash set (tabulation) or walking a trie is cheaper than testing every word at every position.

### Pitfalls and edge cases

- Cache failures, not only successes; the exponential cases are exactly the ones that fail.
- `s.startsWith(word, i)` avoids building substrings; slicing `s[i:i + len(word)]` for every word allocates `m` strings per position.
- Python: write the loop explicitly instead of `any(...)` over a generator. With `any`, every level of recursion also nests C-level calls, and CPython limits C recursion separately from `sys.setrecursionlimit`; a 2000-deep recursion, such as the text of 2000 `a`s, then raises `RecursionError`.

### Language notes

- Python: `functools.cache` on the nested function; `str.startswith(word, start)` compares in place.
- TypeScript: a `Uint8Array` stores unknown, yes and no; `String.prototype.startsWith(word, start)` takes a position.
- Java: a `Boolean[]` uses `null` for "not computed"; `String.startsWith(prefix, offset)` compares in place.
- Kotlin: `arrayOfNulls<Boolean>(n)` plus `memo[start]?.let { return it }` returns a cached answer; `any` short-circuits over the words.
- Go: `strings.HasPrefix(s[start:], word)` compares in place, since slicing a string shares its bytes, and the memo is a `[]int8` with three `iota` states (unknown, splittable, unsplittable), like the TypeScript and Java versions. The recursive closure is declared with `var canSplitFrom func(start int) bool` first.
- Rust: `s[start..].starts_with(word.as_str())` compares in place, which is exact because the input is lowercase ASCII (slicing a `String` at a non-boundary byte would panic). The memo is `Vec<Option<bool>>`, where `None` is "not decided yet", and `Iterator::any` short-circuits over the words like Python's loop.

## Approach: tabulation (Bottom-up reachable prefixes with a word set)

### Intuition

Flip the direction: `ok[i]` says whether the first `i` characters can be split. The last word of such a split is `s[j..i)` for some `j`, and the part before it must be splittable, so `ok[i]` is true when some `ok[j]` is true and `s[j..i)` is a word. Since no word is longer than `L`, only `j >= i - L` can work, which caps the work per position no matter how big the dictionary is.

### Algorithm

1. Put the words in a hash set and compute `L`, the longest word length.
2. Set `ok[0] = true` and every other entry false.
3. For each `end` from 1 to `n`, for each `start` from `max(0, end - L)` to `end - 1`: if `ok[start]` and `s[start..end)` is in the set, set `ok[end] = true` and stop.
4. Return `ok[n]`.

### Correctness

Invariant: when `end` is processed, `ok[k]` is final for every `k < end`. A split of the first `end` characters has a last word `s[start..end)` with `end - start <= L` and a split of the first `start` characters; step 3 tests exactly those `start` values against final `ok` entries. Starting from `ok[0] = true` (the empty prefix), the invariant gives the right `ok[n]`.

### Complexity

- Time: O(n * L^2) — `n` end positions, at most `L` start positions each, and building and hashing a substring of length up to `L` for each.
- Space: O(n + D) — the `ok` array and the word set.

### Trade-offs

Independent of the dictionary size per position, iterative, and short: the standard interview answer and the oracle. The substring allocations are its main constant cost; the trie removes them.

### Pitfalls and edge cases

- Bound the inner loop by the longest word; scanning all `start < end` makes it O(n^2 * L) for no benefit.
- Break as soon as `ok[end]` becomes true.
- `ok[0]` must be true, or nothing can ever be reached.

### Language notes

- Python: `set(word_dict)` and slicing; `s[start:end] in words` hashes the slice.
- TypeScript: `new Set(wordDict)` and `s.slice(start, end)`; `Math.max(...lengths)` is fine for 1000 words.
- Java: a `HashSet<String>` and `substring`, which copies the characters in modern JDKs.
- Kotlin: `toHashSet()`, `maxOf { it.length }`, and `any` over the bounded range of starts.
- Go: the dictionary is a `map[string]bool` and `words[s[start:end]]` looks up a substring that shares `s`'s bytes, so the probe allocates nothing. The built-in `max` clamps the window start at 0.
- Rust: `HashSet<&str>` borrows the words from `word_dict`, and `words.contains(&s[start..end])` probes with a borrowed slice, so no `String` is built per lookup. `end.saturating_sub(longest)` is the unsigned form of `max(0, end - longest)`.

## Approach: trie (Walk a trie of the words from each reachable position)

### Intuition

From a reachable position `start`, walk down a trie of the dictionary along the characters of `s`. Every node marked as the end of a word gives a new reachable position, and the walk stops as soon as no word continues with the next character. One walk replaces up to `L` separate substring lookups, and it never builds a substring.

### Algorithm

1. Insert every word into a trie; mark the node where each word ends.
2. Set `reachable[0] = true`.
3. For each `start` in increasing order with `reachable[start]`: walk the trie from the root along `s[start], s[start + 1], ...`; at each node that ends a word, set `reachable[position + 1] = true`; stop when the next child is missing.
4. Return `reachable[n]`.

### Correctness

`reachable[i]` becomes true exactly when some reachable `start < i` has a dictionary word equal to `s[start..i)`: the walk from `start` visits the trie node for every prefix of `s[start..]` that is a prefix of some word, and the end markers identify the full words. Processing `start` in increasing order means every reachable position is known before its walk is needed, so this computes the same set as the tabulation, and `reachable[n]` is the answer.

### Complexity

- Time: O(n * L + D) — building the trie touches each dictionary letter once, and each of the `n` walks follows at most `L` edges.
- Space: O(n + D) — the reachability array and at most `D` trie nodes.

### Trade-offs

The fastest when the dictionary is large or its words are long, and the walk naturally finds all words starting at a position at once (useful for listing every segmentation). It needs a trie class, which is more code in an interview; mention it as the follow-up to the hash-set version.

### Pitfalls and edge cases

- Keep walking after finding a word: a longer word may also match (`"dog"` and `"dogs"`), and either can lead to a full split.
- Skip unreachable starts; walking from them would mark positions that no split reaches.

### Language notes

- Python: nested dictionaries with an end marker key; `dict.setdefault` builds the path.
- TypeScript: a node type with a `Map<string, TrieNode>` of children, built by a small factory function instead of a class with parameter properties.
- Java: a nested static class with a `TrieNode[26]` array of children, indexed by `letter - 'a'`.
- Kotlin: a private class with `arrayOfNulls<TrieNode>(26)`; the elvis operator `?: break` ends a walk when no child exists.
- Go: the trie is a struct with a `[26]*trieNode` array and an `endsWord` flag, indexed by `letter - 'a'` as in the Java version; a nil child pointer means no word continues that way, which ends the walk.
- Rust: `TrieNode` derives `Default` (arrays of up to 32 elements do), and `children: [Option<Box<TrieNode>>; 26]` is the owned tree. The insert loop reborrows `node` as `&mut` at each step through `get_or_insert_with(Box::default)`, and the lookup walks with a shared `&TrieNode` and `match`, leaving the loop on a missing child.
