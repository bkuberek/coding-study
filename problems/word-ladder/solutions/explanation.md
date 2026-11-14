# Word Ladder: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| bfs-scan-list | brute | O(N^2·L) | O(N·L) | tiny dictionaries; or very long words over a huge alphabet, where generating changes is costlier than comparing |
| bfs-letter-swaps | optimal | O(N·L^2·26) | O(N·L) | default answer |
| bidirectional-bfs | optimal | O(N·L^2·26) | O(N·L) | large dictionaries with many words per level; usually the fastest |

The words are nodes of a graph, with an edge between two words that differ in exactly one position, and every edge costs one rung. The shortest ladder is a breadth-first shortest path from `beginWord` to `endWord`, plus one because the answer counts words. N is the dictionary size and L the word length. The three approaches differ in how they find a word's neighbors and in how much of the graph they explore.

## Approach: bfs-scan-list (Breadth-first search that compares against every unvisited word)

### Intuition

Run a breadth-first search from `beginWord`. To find the neighbors of the current word, compare it with every dictionary word that has not been reached yet and keep those that differ in exactly one letter. Removing reached words from the list keeps the scans shrinking.

### Algorithm

1. If `endWord` is not in the dictionary, return 0.
2. Let `unvisited` be the dictionary without `beginWord`, and start a queue with `(beginWord, 1)`.
3. While the queue is not empty, take `(word, count)`; if `word` is `endWord`, return `count`. Otherwise split `unvisited` into words one letter away from `word` (enqueue each with `count + 1`) and the rest (the new `unvisited`).
4. Return 0.

### Correctness

This is breadth-first search on the word graph: a word is enqueued exactly once, when it is first found one letter away from a word of the previous level, so `count` is its shortest ladder length. Removing it from `unvisited` at that moment plays the role of a visited set. The search reaches `endWord` exactly when some ladder exists.

### Complexity

- Time: O(N^2·L) — each dequeued word is compared with up to N unvisited words, and a comparison reads up to L letters.
- Space: O(N·L) — the unvisited list and the queue hold words of length L.

### Trade-offs

Needs no alphabet assumptions and no string building, but it compares every pair of words in a dense dictionary. With 5000 words that is millions of comparisons, against about 5000·L·26 hash lookups for the letter-swap search. It becomes competitive only when L is large and the dictionary small.

### Pitfalls and edge cases

- Return 0 right away when `endWord` is missing; otherwise the search would explore everything for nothing.
- Exclude `beginWord` from the list, or it can be reached again through a neighbor and confuse counts in variants that return paths.
- The answer counts words, so a single change gives 2.

### Language notes

- Python: the one-letter test exits early after the second difference, which matters in the inner loop.
- TypeScript: one level is processed at a time; `if (first[i] !== second[i] && ++differences > 1)` counts and tests in one expression.
- Java: an `ArrayDeque` queue with an explicit level size; comparisons use `charAt` rather than building arrays.
- Kotlin: `partition` splits the unvisited words into neighbors and the rest in one call.
- Go: `slices.Contains` (Go 1.21 and newer) is the linear `end_word in word_list` test, and `oneApart` compares the strings byte by byte, which is exact for the lowercase ASCII words. The unvisited list is rebuilt into a fresh slice on every dequeue, like the Python `remaining` list.
- Rust: `one_apart` zips `first.bytes()` with `second.bytes()` and stops at the second difference. `for candidate in unvisited` consumes the list, so each word moves either into the queue or into `remaining`, and `unvisited = remaining` hands the survivors to the next round without cloning a string.

## Approach: bfs-letter-swaps (Breadth-first search that tries every one-letter change)

### Intuition

A word of length L has at most 25·L possible one-letter changes. Generate each change and look it up in a hash set of the dictionary: that finds all neighbors in O(26·L) lookups, independent of the dictionary size. Deleting a word from the set when it is reached makes the set double as the visited set.

### Algorithm

1. Put the dictionary in a set `available`. If `endWord` is not in it, return 0. Remove `beginWord`.
2. Breadth-first search from `beginWord`, level by level, counting words from 1.
3. For each word taken from the queue: if it is `endWord`, return the count. Otherwise, for every position and every letter `a` to `z`, build the changed word; if it is in `available`, remove it and enqueue it for the next level.
4. Return 0.

### Correctness

The changes generated for a word are exactly the strings one letter away from it (changing a letter to itself gives the word again, which is no longer available). Those present in `available` are its unvisited dictionary neighbors, so this is breadth-first search on the word graph, and the level of `endWord` is the shortest ladder length.

### Complexity

- Time: O(N·L^2·26) — each of at most N words generates 26·L candidate strings, and building and hashing each candidate costs O(L).
- Space: O(N·L) — the set and the queue.

### Trade-offs

The standard answer: the cost per word no longer depends on N. It assumes a small alphabet; for huge alphabets, an index from patterns such as `c*ld` to the words matching them gives the same neighbor lists without enumerating letters. Bidirectional search cuts the explored part further.

### Pitfalls and edge cases

- Remove words from the set when they are enqueued, not when dequeued, or the same word is enqueued from several parents.
- Restore the changed letter before moving to the next position.
- `beginWord` may or may not be in the dictionary; removing it covers both cases.

### Language notes

- Python: candidates are built as `prefix + letter + suffix` with the slices computed once per position.
- TypeScript: `Set.delete` returns whether the word was present, which tests and removes in one call.
- Java: a `char[]` is changed in place and copied into a new `String` for each lookup; `HashSet.remove` returns a `boolean`.
- Kotlin: `for (letter in 'a'..'z')` walks the alphabet; `repeat(queue.size)` processes one level, and `return words` inside it returns from the function because `repeat` is inline.
- Go: strings are immutable, so a `[]byte` copy of the word is changed one position at a time and converted back with `string(letters)` for each lookup; the original byte is restored after the 26 letters. Deleting from the `map[string]bool` while the queue grows is safe because the map is never ranged over.
- Rust: `word.into_bytes()` takes the word's buffer without copying, and `std::str::from_utf8(&letters)` borrows it as a `&str` for each lookup, so a probe that misses allocates nothing. `HashSet::take` removes the word and hands back the owned `String` that goes into the queue, which tests and removes in one call.

## Approach: bidirectional-bfs (Letter-change searches from both ends that meet in the middle)

### Intuition

The number of words within `k` rungs of a word can grow very fast with `k`. Searching from both ends and stopping when the two searches touch explores two neighborhoods of radius about `k/2` instead of one of radius `k`. Always growing the smaller frontier keeps both neighborhoods small. The graph is undirected (a change can be undone), so searching backward from `endWord` is valid.

### Algorithm

1. Build `available` from the dictionary; return 0 if `endWord` is missing. Remove both `beginWord` and `endWord` from it.
2. Start `near = {beginWord}`, `far = {endWord}` and `words = 1`.
3. While both frontiers are non-empty: swap them if `near` is larger; add 1 to `words`; for every one-letter change of every word in `near`, return `words` if the change is in `far`, otherwise move it from `available` into the next frontier when present. Replace `near` with the next frontier.
4. Return 0.

### Correctness

Each frontier holds the words at one distance from its own end, and `words` is the number of words on a ladder that goes from `beginWord` through the expanded levels of both searches to `endWord`. A word removed from `available` belongs to exactly one search. The first time a change from one frontier lands in the other, the two partial ladders join into a real ladder of `words` words; no shorter ladder exists, because a shorter one would have joined the two searches at an earlier expansion. If a frontier empties, the words reachable from its end are exhausted without meeting the other search, so there is no ladder.

### Complexity

- Time: O(N·L^2·26) — in the worst case every word is expanded once, as in the one-sided search; typically far fewer words are expanded.
- Space: O(N·L) — the set of available words and the two frontiers.

### Trade-offs

Usually several times faster than the one-sided search on large dictionaries, for a little more code. It needs `endWord` known in advance and reversible moves, both true here. For returning all shortest ladders, the one-sided level-by-level version is easier to extend.

### Pitfalls and edge cases

- Remove `endWord` from `available` too, so the backward search does not re-add it.
- Check membership in `far` before the `available` check: words in `far` were already removed from `available`.
- Expand whole levels and increment `words` once per level.

### Language notes

- Python: frontiers are sets swapped with tuple assignment; the smaller one is expanded.
- TypeScript: `[near, far] = [far, near]` swaps the frontiers; `available.delete` reports whether a candidate was available.
- Java: `HashSet` frontiers swapped through a temporary variable; candidates come from an in-place `char[]`.
- Kotlin: `near = far.also { far = near }` swaps the frontiers in one statement.
- Go: the frontiers are `map[string]bool` sets swapped with `near, far = far, near`, and each lookup converts the changed `[]byte` back to a string. Deleting `endWord` and `beginWord` from `available` up front keeps the frontier words from being found as new candidates.
- Rust: `std::mem::swap` exchanges the two frontier sets. Because `near` is borrowed while it is iterated, each word is cloned into a byte buffer first, and the next level is collected in a separate set and moved into `near` after the loop. `far.contains(candidate)` and `available.take(candidate)` both accept the borrowed `&str` directly.
