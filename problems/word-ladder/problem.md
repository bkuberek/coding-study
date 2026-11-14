# Word Ladder

## Statement

A word ladder turns one word into another one letter at a time. You get a start word `beginWord`, a goal word `endWord` and a dictionary `wordList`, all made of lowercase letters and all of the same length. Each rung of the ladder changes exactly one letter of the previous word, in place, and the result must be a word of the dictionary. The start word does not have to be in the dictionary, but every other word on the ladder, including `endWord`, must be.

Return the number of words on the shortest ladder from `beginWord` to `endWord`, counting both ends. Return `0` if no ladder exists.

Reference: this is our own wording of LeetCode problem 127, [Word Ladder](https://leetcode.com/problems/word-ladder/).

## Input

- `beginWord`: the word the ladder starts from.
- `endWord`: the word the ladder must reach.
- `wordList`: the dictionary of allowed words, without repeats.

## Output

The number of words on a shortest ladder, `beginWord` and `endWord` included, or `0` when `endWord` cannot be reached (for example because it is not in the dictionary).

## Examples

### Example 1

<!-- case: ex1 -->

One shortest ladder is `cold`, `cord`, `card`, `ward`, `warm`: five words. Others of the same length exist, such as `cold`, `wold`, `word`, `worm`, `warm`, but none is shorter, since `cold` and `warm` differ in four letters and each rung changes only one.

### Example 2

<!-- case: ex2 -->

`gold` is not in the dictionary, so no ladder can end there.

## Constraints

- `1 <= beginWord.length <= 10`; `endWord` and every dictionary word have the same length.
- `1 <= wordList.length <= 5000`
- All words consist of lowercase English letters.
- The dictionary words are distinct, and `beginWord != endWord`.

## Follow-ups

- Return one shortest ladder, or all shortest ladders, instead of the length.
- Comparing every pair of words is quadratic in the dictionary size. How can you find a word's neighbors without looking at every other word?
- Why does searching from both ends at once usually help a lot here?

## Hints

### Hint 1

Treat each dictionary word as a node, with an edge between words that differ in exactly one position. The answer is a shortest path, and every edge costs one.

### Hint 2

Breadth-first search from `beginWord` finds it. The expensive part is listing a word's neighbors: try changing each position to each of the 26 letters and look the result up in a hash set.

### Hint 3

Remove words from the set as soon as they are reached, so no word is enqueued twice, and count words, not steps: a one-rung ladder has two words.
