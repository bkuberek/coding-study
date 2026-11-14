# Minimum Removals to Balance Parentheses

## Statement

You get a string `s` of lowercase letters and the parentheses `(` and `)`. Delete as few parentheses as possible so that the remaining string is balanced, and return it.

A string is balanced when every `(` is closed by a later `)` and every `)` closes an earlier `(`, with pairs properly nested; letters do not matter for balance. Letters must all be kept, in their original order. The empty string is balanced.

Several results can need the same, minimal, number of deletions. Any of them is accepted.

Reference: this is our own wording of LeetCode problem 1249, [Minimum Remove to Make Valid Parentheses](https://leetcode.com/problems/minimum-remove-to-make-valid-parentheses/).

## Input

- `s`: the string to repair, made of lowercase letters, `(` and `)`

## Output

A balanced string obtained from `s` by deleting the fewest possible parentheses. Any such string is accepted.

## Examples

### Example 1

<!-- case: ex1 -->

All parentheses match except the last `)`, which has no `(` left to close. Deleting it is the only single deletion that balances the string.

### Example 2

<!-- case: ex2 -->

The first `)` comes before any `(`, and both `(` are never closed, so all three parentheses must go, leaving only the letter.

## Constraints

- `1 <= s.length <= 10^5`
- `s` contains only lowercase English letters, `(` and `)`.

## Follow-ups

- How many parentheses must be deleted at minimum, and can you count them in one pass?
- Can you build the result in two linear passes without a stack of positions?
- Which of the possible answers does your approach return, and why is it as short as any other?

## Hints

### Hint 1

Scanning left to right with a counter of open parentheses, a `)` that arrives while the counter is zero can never be matched. It must be deleted.

### Hint 2

After that, some `(` may still be open at the end of the string. Exactly that many `(` must be deleted as well.

### Hint 3

Record the positions of unmatched `(` on a stack while scanning; a `)` that finds the stack non-empty matches the most recent one. Whatever remains on the stack at the end is deleted.
