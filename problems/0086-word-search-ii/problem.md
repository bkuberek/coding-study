# Word Search II

## Statement

You get a rectangular board of letters and a list of distinct words. A word is on the board when you can spell it by starting at some cell and moving, one letter at a time, to a horizontally or vertically adjacent cell, without using any cell twice within that word. Diagonal moves are not allowed.

Return every word of the list that is on the board, each once, in any order. Different words may use the same cells; the no-reuse rule applies only within a single word.

Reference: this is our own wording of LeetCode problem 212, [Word Search II](https://leetcode.com/problems/word-search-ii/).

## Input

- `board`: the rows of the board, each a list of single lowercase letters; all rows have the same length.
- `words`: the distinct words to look for.

## Output

The words of `words` that can be traced on the board, in any order, each listed once.

## Examples

### Example 1

<!-- case: ex1 -->

`cat` runs along the top row, `core` goes down from `c` to `o` and then right through `r` and `e`, `dog` runs along the bottom row and `rat` goes up from the centre and then right. `code` fails because the only `d` touches no `e`, and `toe` fails because `t` has no neighbouring `o`.

### Example 2

<!-- case: ex2 -->

`abdc` circles the board. `abcd` would need a diagonal step from `b` to `c`, and `aa` would need the single `a` twice.

## Constraints

- `1 <= board.length, board[i].length <= 12`.
- `1 <= words.length <= 10^4`; `1 <= words[i].length <= 10`; the words are distinct.
- The board and the words consist of lowercase English letters.

## Follow-ups

- Searching each word separately repeats the same board walks for words that share a beginning. How can one walk serve all of them at once?
- Once a word has been found, how can you keep the search from looking for it again?

## Hints

### Hint 1

For one word, a depth-first search from every cell answers the question: mark the cell as used, try the four neighbours for the next letter, and unmark it on the way back.

### Hint 2

Put all words in a trie. A walk on the board then follows the trie at the same time, and it can stop as soon as the letters spelled so far are not a prefix of any word.

### Hint 3

Store the complete word at the trie node where it ends. When the walk reaches such a node, record the word and clear it from the node so it is reported once.
