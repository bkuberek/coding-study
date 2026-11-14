# Word Search

## Statement

You get a rectangular grid `board` of letters and a string `word`. Decide whether you can spell `word` by walking through the grid: start on any cell holding the first letter, and step each time to a cell directly above, below, left or right of the current one that holds the next letter. Diagonal steps are not allowed, and a cell may be used at most once in the same walk.

Reference: this is our own wording of LeetCode problem 79, [Word Search](https://leetcode.com/problems/word-search/).

## Input

- `board`: the grid of letters, as rows of single-character strings
- `word`: the string to spell

## Output

`true` if some walk spells `word`, otherwise `false`.

## Examples

### Example 1

<!-- case: ex1 -->

Start on the `s` in the top-left corner, step right to `n`, down to `a`, then right twice through `r` and `e`.

### Example 2

<!-- case: ex2 -->

The walk `a`, `b`, `d`, `c` follows neighbors around the square, but the final `a` would need the top-left cell a second time, which is not allowed.

## Constraints

- `1 <= board.length, board[i].length <= 6`
- All rows of `board` have the same length.
- `1 <= word.length <= 15`
- `board` and `word` consist of lowercase English letters.

## Follow-ups

- Before searching, can you rule out some words just by counting letters?
- Does it matter whether you search for the word or for its reverse? When would starting from the last letter be faster?
- Can you mark cells as used without a separate visited grid?

## Hints

### Hint 1

Try every cell as a starting point. From a cell that matches the current letter, the rest of the word must be found starting at one of its four neighbors.

### Hint 2

Mark a cell as used before exploring its neighbors and unmark it when you come back, so that other walks may still pass through it.

### Hint 3

If the grid holds fewer copies of some letter than the word needs, the answer is `false` without any search. And if the word's last letter is rarer on the grid than its first, search for the reversed word: far fewer starting cells survive the first step.
