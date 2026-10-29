# Word Search II: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| per-word-search | brute | O(W * r * c * 3^L) | O(L) | very few words |
| trie-backtracking | optimal | O(S + r * c * 3^L) | O(26 * S) | default answer; many words |

The board has `r` rows and `c` columns; `W` is the number of words, `L` the length of the longest word and `S` the total length of all words. A walk branches into at most 3 new cells after its first step, which gives the `3^L` factor; it is a loose bound, because walks stop as soon as a letter does not fit.

## Approach: per-word-search (Backtracking search for each word separately)

### Intuition

Deciding whether one word is on the board is a classic backtracking search: start at every cell, and from a cell holding the right letter try the four neighbours for the next letter, marking the cell as used so the same word cannot reuse it. Run that search for every word.

### Algorithm

1. For each word, try every cell as the start of `trace(cell, 0)`.
2. `trace(cell, i)`: fail if the cell does not hold `word[i]`; succeed if `i` is the last position. Otherwise mark the cell as used, try `trace` on each in-bounds neighbour with `i + 1`, restore the cell, and report whether any neighbour succeeded.
3. Return the words for which some start succeeded.

### Correctness

`trace` explores exactly the walks that spell a prefix of the word and use each cell at most once: the used mark excludes the cells already on the current walk, and restoring it on return frees them for other walks. Every valid tracing of the word is one of these walks, so the search finds the word exactly when it is on the board. Each word is tested once, so it is reported once.

### Complexity

- Time: O(W * r * c * 3^L) — each word starts a search at every cell, and each search branches into at most three unused neighbours per letter after the first step.
- Space: O(L) — the recursion depth is at most the word's length; the marks live in the board itself.

### Trade-offs

It reuses the single-word solution unchanged and is easy to trust, but words that share a beginning repeat the same walks, and every word pays for a scan of the whole board. With thousands of words it does far more work than necessary.

### Pitfalls and edge cases

- Restore the cell after exploring it, also when the search succeeds, or later words see a damaged board.
- A word longer than the number of cells, or one that needs a cell twice, is never on the board.
- Single-row and single-column boards: neighbours outside the board must be skipped.

### Language notes

- Python: the board is a list of lists of one-letter strings, so `#` can mark a cell in place; `any(...)` stops at the first success.
- TypeScript: `string[][]` is mutable like the Python board; the loop breaks out on the first success so the cell is restored exactly once.
- Java: `char[][]` cells are compared with `charAt` without boxing.
- Kotlin: `Array<CharArray>` maps to the same JVM `char[][]`; `STEPS.any { (dr, dc) -> ... }` destructures each pair.
- Go: the board is `[][]rune`, so a cell compares with `word[position]` once the word is converted with `[]rune(word)`, and `'#'` marks a visited cell in place. `trace` is a closure declared with `var trace func(...)` first so that it can call itself; `break` after the first success leaves the loop, and the cell is restored on the line after it.
- Rust: the board is a `Vec<Vec<char>>` that the function owns (`mut board`), so marking and restoring cells needs no copy. A step off the board is caught by `checked_add_signed` on the `usize` coordinates, which returns `None` for a negative result instead of wrapping, and `any` stops at the first neighbor that succeeds.

## Approach: trie-backtracking (One backtracking pass guided by a trie of all words)

### Intuition

Put all words into a trie. Then one walk on the board can follow the trie at the same time: each step to a neighbour moves one trie edge down. The walk stops as soon as the letters spelled so far are not a prefix of any word, and every word ending at the current trie node is found at once. Words that share a beginning now share the walk.

### Algorithm

1. Insert every word into a trie, storing the complete word at the node where it ends.
2. From every cell, call `explore(cell, root)`.
3. `explore(cell, parent)`: stop if the cell is used or `parent` has no child for its letter. Otherwise move to that child; if it stores a word, record the word and clear it. Mark the cell as used, explore the four in-bounds neighbours with the child as the new parent, then restore the cell.
4. Return the recorded words.

### Correctness

A call `explore(cell, node)` happens exactly for walks of unused cells whose letters spell the path to `node`, because each step moves one cell and one matching trie edge. A word is on the board exactly when some such walk spells it, and every such walk is explored unless its letters stop being a prefix of some word, in which case no word can be spelled by extending it. When a walk reaches the node of a word, the word is recorded; clearing it guarantees it is recorded only once, even if several walks spell it.

### Complexity

- Time: O(S + r * c * 3^L) — building the trie costs one step per letter of the words; the walks from every cell branch into at most three unused neighbours and never go deeper than the longest word, and in practice stop as soon as the trie has no matching child.
- Space: O(26 * S) — at most one trie node per letter of the words, each with 26 slots; the recursion adds O(L).

### Trade-offs

It explores each board walk once for all words together, which is what makes thousands of words feasible. A further optimization removes trie branches once all their words have been found, so later walks stop even earlier; the references keep the trie intact for clarity, and only clear found words.

### Pitfalls and edge cases

- Record a word without stopping the walk: a longer word may continue from the same node (`oat` and `oath`).
- Clear the word after recording it, or a word traced along two different walks appears twice.
- Restore each cell when backtracking, and check the used mark before reading the trie child, because `#` is not a letter.

### Language notes

- Python: a nested `dict` trie keyed by letter, with `"$"` holding the complete word; `node.pop(WORD, None)` records and clears it in one step.
- TypeScript: a `TrieNode` class with 26 slots and `word: string | null`; `??=` builds missing children.
- Java: a nested static `Node` class; the `#` mark is checked before indexing `children` with `letter - 'a'`.
- Kotlin: `?: return` leaves `explore` when the letter has no child, and a local `fun explore` closes over the board and the result list.
- Go: a node keeps `children [26]*node` and a `word string`, where `""` means "no word here, or already reported" (the words are never empty). `explore` returns on the `'#'` mark before computing `letter - 'a'`, which would be a negative index. The result slice is captured by the recursive closure.
- Rust: `word: Option<String>` plus `node.word.take()` reports a word and clears it in one step, like Python's `pop`. The recursion passes `&mut Node` down while the board is passed as `&mut [Vec<char>]`, and the borrow checker accepts both because they are separate values. The `'#'` check comes first, because `slot('#')` would underflow `u8` and panic.
