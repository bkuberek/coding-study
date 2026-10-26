# Palindrome With One Deletion

## Statement

You get a string `s` of lowercase English letters. You may delete at most one character from it, at any position, and keep the rest in order. Decide whether you can end up with a palindrome, a string that reads the same from both ends.

Deleting nothing is allowed, so a string that already is a palindrome qualifies.

Reference: this is our own wording of LeetCode problem 680, [Valid Palindrome II](https://leetcode.com/problems/valid-palindrome-ii/).

## Input

- `s`: the string to check

## Output

`true` when deleting zero or one character of `s` leaves a palindrome, otherwise `false`.

## Examples

### Example 1

<!-- case: ex1 -->

Deleting the final `s` leaves `kayak`, which is a palindrome.

### Example 2

<!-- case: ex2 -->

The outer characters `c` and `u` differ. Deleting the `c` leaves `uppucu`, which is not a palindrome, but deleting the last `u` leaves `cuppuc`, which is. One working choice is enough.

### Example 3

<!-- case: ex3 -->

The outer characters `t` and `m` differ, and whichever of them you delete, the other one still has no partner at the opposite end. One deletion is not enough.

## Constraints

- `1 <= s.length <= 10^5`
- `s` contains only the lowercase letters `a` to `z`.

## Follow-ups

- Trying every deletion is quadratic. Can you decide in one linear pass?
- When the outer characters disagree, you must delete one of them. Why is it enough to test only those two choices?
- How would you generalize to at most `k` deletions, and what would that cost?

## Hints

### Hint 1

Compare characters from both ends, as for an ordinary palindrome. While they agree, no deletion can help, so keep moving inward.

### Hint 2

At the first pair of characters that disagree, one of the two must be the deleted character: no other single deletion makes those two positions match.

### Hint 3

Check whether the inner part is a palindrome after skipping the left character, and separately after skipping the right one. Either success means `true`.
