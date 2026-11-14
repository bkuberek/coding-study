# Valid Palindrome

## Statement

You get a line of text `s`. Decide whether it is a palindrome under two relaxations: only ASCII letters and digits count, and a letter matches the same letter in the other case. Everything else, such as spaces, punctuation and symbols, is skipped as if it were not there.

Put differently, keep the letters and digits of `s` in their original order, lowercase every letter, and check whether that sequence reads the same from both ends. A line with no letters or digits at all leaves an empty sequence, which counts as a palindrome.

Reference: this is our own wording of LeetCode problem 125, [Valid Palindrome](https://leetcode.com/problems/valid-palindrome/).

## Input

- `s`: the text to check, made of printable ASCII characters

## Output

`true` when the letters and digits of `s` read the same forwards and backwards (ignoring letter case), otherwise `false`.

## Examples

### Example 1

<!-- case: ex1 -->

The letters, lowercased, spell `wasitacaroracatisaw`, which is the same in reverse. The spaces and the question mark are skipped.

### Example 2

<!-- case: ex2 -->

Digits count. Without the `1` the letters would form a palindrome, but `neveroddoreven1` starts with `n` and ends with `1`.

### Example 3

<!-- case: ex3 -->

Nothing in this line is a letter or a digit, so the cleaned sequence is empty, and an empty sequence is a palindrome.

## Constraints

- `1 <= s.length <= 2 * 10^5`
- Every character of `s` has an ASCII code from 32 (space) to 126 (`~`).

## Follow-ups

- Building a cleaned copy is easy but uses O(n) memory. Can you decide with O(1) extra memory?
- What would change if `s` could contain any Unicode text, where lowercasing can change the length of a string and some letters are written with combining marks?
- If you may delete one character before checking, can you still answer in linear time? That is the next problem in this pattern, Palindrome With One Deletion.

## Hints

### Hint 1

The comparison ignores some characters and letter case. What would the string look like if you removed everything that does not count first?

### Hint 2

A palindrome check compares the first kept character with the last, the second with the second to last, and so on. You do not need a copy to find those characters.

### Hint 3

Keep one index at each end. Move an index inward past any character that does not count, compare the two characters it lands on, and stop when the indices meet.
