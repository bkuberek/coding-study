# Longest Substring Without Repeats

## Statement

You get a string `s`. Find the longest substring of `s` in which no character occurs twice, and return its length.

A substring is a contiguous run of characters of `s`. Every character counts, including spaces, digits and punctuation, and uppercase and lowercase letters are different characters.

Reference: this is our own wording of LeetCode problem 3, [Longest Substring Without Repeating Characters](https://leetcode.com/problems/longest-substring-without-repeating-characters/).

## Input

- `s`: the string to search; it may be empty

## Output

The length of the longest substring of `s` whose characters are all distinct, or 0 for an empty string.

## Examples

### Example 1

<!-- case: ex1 -->

`na split` has 8 distinct characters, one of them the space. Any longer substring would contain a second `a`, `n` or space.

### Example 2

<!-- case: ex2 -->

Every substring longer than one character repeats `z`, so the answer is 1.

### Example 3

<!-- case: ex3 -->

`cbdea` is the longest run without a repeat. It starts right after the first `b`, because `bcb` already repeats `b`.

## Constraints

- `0 <= s.length <= 5 * 10^4`
- Every character of `s` has an ASCII code from 32 (space) to 126 (`~`).

## Follow-ups

- Growing a window from every start position rescans characters many times. Can you do it in one pass?
- When the window meets a repeated character, can you move its left edge directly to the right place instead of one step at a time?
- How does the answer change if a character may occur at most twice?

## Hints

### Hint 1

Fix the start of the substring and extend it to the right until a character repeats. How long can such a run be at most?

### Hint 2

When `s[right]` repeats a character inside the current window, every window that starts at or before that earlier occurrence and reaches `right` is invalid. Where must the next valid window start?

### Hint 3

Remember, for each character, the last position where you saw it. On a repeat inside the window, move the left edge just past that position; never move it backwards.
