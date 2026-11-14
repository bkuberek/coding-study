# Edit Distance

## Statement

You may change a word one character at a time with three operations, each costing 1:

- insert any character at any position,
- delete any character,
- replace any character with a different one.

Given two words `word1` and `word2`, return the smallest number of operations that turns `word1` into `word2`. This number is also known as the Levenshtein distance. Either word may be empty.

Reference: this is our own wording of LeetCode problem 72, [Edit Distance](https://leetcode.com/problems/edit-distance/).

## Input

- `word1`: the word to change
- `word2`: the word to obtain

## Output

The minimum number of insertions, deletions and replacements that turn `word1` into `word2`.

## Examples

### Example 1

<!-- case: ex1 -->

Delete the `e` of `planet` to get `plant`, then insert `s` at the end. One operation is not enough, because the words differ in two places that no single edit can fix together.

### Example 2

<!-- case: ex2 -->

Starting from an empty word, every character of `abc` must be inserted.

## Constraints

- `0 <= word1.length, word2.length <= 500`
- Both words contain only lowercase English letters.

## Follow-ups

- Trying every sequence of operations is hopeless. What smaller question remains after you decide what happens to the first character of each word?
- Can you compute the distance with only two rows of the table, or one?
- How would you also return the list of operations?

## Hints

### Hint 1

Look at the first characters of both words. If they are equal, they can be kept for free. If not, the first operation that touches them is a deletion, an insertion or a replacement.

### Hint 2

Let `D(i, j)` be the distance between the suffixes starting at `i` and `j`. On a mismatch, `D(i, j) = 1 + min(D(i + 1, j), D(i, j + 1), D(i + 1, j + 1))`.

### Hint 3

When one suffix is empty, the distance is the length of the other one. Fill the table from those borders inwards.
