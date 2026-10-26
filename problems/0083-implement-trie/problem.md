# Implement a Trie

## Statement

Build a `Trie`, a prefix tree that stores words and answers two kinds of questions quickly: whether a word was stored, and whether any stored word begins with a given prefix. Words consist of lowercase English letters.

A trie stores words letter by letter along paths from a root, so words that share a beginning share the same path for as long as their letters agree. That is what makes prefix questions cheap: they only follow the letters of the prefix.

Reference: this is our own wording of LeetCode problem 208, [Implement Trie (Prefix Tree)](https://leetcode.com/problems/implement-trie-prefix-tree/).

## Input

- `Trie()`: creates an empty trie.
- `insert(word)`: stores `word`. Storing a word that is already stored changes nothing.
- `search(word)`: asks whether `word` itself was stored; a stored longer word that merely starts with `word` does not count.
- `startsWith(prefix)`: asks whether at least one stored word starts with `prefix`. A stored word counts as starting with itself.

Each test case is a sequence of operations: the first creates the trie, and the following ones call its methods.

## Output

For each operation, its return value: `null` for the constructor and for `insert`, and `true` or `false` for `search` and `startsWith`.

## Examples

### Example 1

<!-- case: ex1 -->

After storing `cat`, the word `cat` is found but `ca` is not, because only a longer word starts with it; `startsWith("ca")` is true for the same reason. Once `ca` is stored as well, searching for it succeeds.

### Example 2

<!-- case: ex2 -->

With only `dog` stored, `do` is a prefix of a stored word and `dot` is not. `dogs` is longer than every stored word, so it is neither a stored word nor a prefix of one.

## Constraints

- `1 <= word.length, prefix.length <= 20`.
- `word` and `prefix` consist of lowercase English letters `a` to `z`.
- At most `10^4` calls to `insert`, `search` and `startsWith` in total.

## Follow-ups

- How would the design change if the alphabet were all of Unicode instead of 26 letters?
- Could you also count how many stored words start with a prefix, without walking the words below it?

## Hints

### Hint 1

A set of words answers `search` directly. What does `startsWith` cost with only a set?

### Hint 2

Give every node one child per letter and a flag that says "a word ends here". Inserting a word walks (and creates) the path of its letters, then sets the flag.

### Hint 3

`search` and `startsWith` walk the same path; they only differ in what they check at the end: the flag, or merely that the path exists.
