# Word Dictionary With Wildcards

## Statement

Build a `WordDictionary` that stores words of lowercase English letters and answers pattern queries. A pattern is made of letters and dots: a letter must match itself, and a dot matches exactly one letter, whatever it is. A pattern matches a stored word when both have the same length and every position matches.

`search(pattern)` reports whether at least one stored word matches. Dots never match an empty position, so a pattern can only match words of exactly its length.

Reference: this is our own wording of LeetCode problem 211, [Design Add and Search Words Data Structure](https://leetcode.com/problems/design-add-and-search-words-data-structure/).

## Input

- `WordDictionary()`: creates an empty dictionary.
- `addWord(word)`: stores `word`; storing it again changes nothing.
- `search(word)`: asks whether some stored word matches the pattern `word`, in which each `.` stands for any single letter.

Each test case is a sequence of operations: the first creates the dictionary, and the following ones call its methods.

## Output

For each operation, its return value: `null` for the constructor and for `addWord`, and `true` or `false` for `search`.

## Examples

### Example 1

<!-- case: ex1 -->

`map` and `mop` are stored. The pattern `m.p` matches both, `.ap` matches `map`, and `m..` matches any stored three-letter word starting with `m`. `ma` matches nothing because no stored word has two letters.

### Example 2

<!-- case: ex2 -->

A pattern of only dots matches any stored word of that length. `...` finds `sun`, `....` finds nothing until `suns` is stored, and `s.n.` then matches it.

## Constraints

- `1 <= word.length <= 20` for both methods.
- Words given to `addWord` consist of lowercase English letters.
- Patterns given to `search` consist of lowercase English letters and at most `3` dots.
- At most `10^4` calls to `addWord` and `search` in total.

## Follow-ups

- How does the cost of a search grow with the number of dots, and what bounds it?
- If patterns could also contain `*` (any sequence of letters, possibly empty), how would the search change?

## Hints

### Hint 1

Without dots this is the trie's `search`. What should happen at a node when the next pattern character is a dot?

### Hint 2

A dot can stand for any child of the current node, so try them all: search the rest of the pattern from every child, and succeed if any of those searches succeeds.

### Hint 3

That is a depth-first search over the trie, indexed by position in the pattern. It stops at the first success, and at the end of the pattern it checks the "word ends here" flag.
