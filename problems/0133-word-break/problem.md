# Word Break

## Statement

You get a string `s` with no spaces and a list of dictionary words `wordDict`. Decide whether spaces can be inserted into `s` so that every resulting piece is a word from the dictionary.

A dictionary word may be used any number of times, and some words may not be used at all. Every character of `s` must belong to exactly one piece.

Reference: this is our own wording of LeetCode problem 139, [Word Break](https://leetcode.com/problems/word-break/).

## Input

- `s`: the text to segment
- `wordDict`: the allowed words, all distinct

## Output

`true` if `s` can be split into a sequence of dictionary words, otherwise `false`.

## Examples

### Example 1

<!-- case: ex1 -->

The text splits as "sun flower field", and also as "sunflower field". One valid split is enough.

### Example 2

<!-- case: ex2 -->

"rain bow" and "rainbow" both cover the start, but the remaining "tie" is not a word ("ties" is), so no split covers the whole text.

### Example 3

<!-- case: ex3 -->

The same word can be used repeatedly: "ab ab".

## Constraints

- `1 <= s.length <= 2000`
- `1 <= wordDict.length <= 1000`
- `1 <= wordDict[i].length <= 20`
- `s` and every word contain only lowercase English letters.
- The words in `wordDict` are distinct.

## Follow-ups

- Why does trying every split recursively blow up on a text like `"aaaa...ab"` with the words `"a"`, `"aa"` and `"aaa"`?
- Words are at most 20 letters long. How does that bound help a bottom-up solution?
- How would you return every possible segmentation instead of a yes or no answer?

## Hints

### Hint 1

If a valid split exists, its first word is one of the dictionary words that `s` starts with. What is left to check after choosing it?

### Hint 2

Whether the rest of the text can be split depends only on where the rest starts. Remember the answer for each starting position.

### Hint 3

Let `ok[i]` say whether the first `i` characters can be split. `ok[0]` is true, and `ok[i]` is true when some `ok[j]` is true and `s[j..i)` is a word; only `j` within 20 positions of `i` can work.
