# Parentheses With Wildcards

## Statement

You get a string `s` made of the characters `(`, `)` and `*`. Each `*` is a wildcard that you may replace by `(`, by `)`, or by nothing, independently of the other wildcards. Decide whether some choice of replacements turns `s` into a balanced parenthesis string.

A string is balanced when every `(` has a matching `)` somewhere after it, every `)` has a matching `(` somewhere before it, and the matched pairs nest properly. The empty string is balanced.

Reference: this is our own wording of LeetCode problem 678, [Valid Parenthesis String](https://leetcode.com/problems/valid-parenthesis-string/).

## Input

- `s`: the characters `(`, `)` and `*`

## Output

`true` if the wildcards can be replaced so that the result is balanced, otherwise `false`.

## Examples

### Example 1

<!-- case: ex1 -->

Replace the `*` by `)` to get "(())".

### Example 2

<!-- case: ex2 -->

Replace the first `*` by `(` and the second by `)` to get "()()". A wildcard can help on either side.

### Example 3

<!-- case: ex3 -->

The final `(` has nothing after it that could close it, whatever the `*` becomes.

## Constraints

- `1 <= s.length <= 10^4`
- `s[i]` is `(`, `)` or `*`.

## Follow-ups

- Trying all three choices for every wildcard takes exponential time. What single number describes a prefix of a string without wildcards?
- With wildcards, that number becomes a set of possibilities. What shape does that set always have?
- Can you solve it in one pass with O(1) extra memory?

## Hints

### Hint 1

Without wildcards, scan left to right counting open parentheses: the count must never go negative and must end at zero.

### Hint 2

With wildcards, the open count after a prefix can take several values. Track all of them.

### Hint 3

The possible open counts always form a contiguous range, so the lowest and highest values describe it completely.
