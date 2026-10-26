# Decode String

## Statement

A compact text format writes repetition as `k[content]`, meaning `content` repeated exactly `k` times. Groups can be nested, and letters can appear outside of groups: `2[ab3[c]]d` expands to `abcccabcccd`.

You get a string `s` in this format. Expand every group and return the decoded string.

The input is always well-formed: every `[` is preceded by a positive repeat count and closed by a matching `]`, digits appear only in repeat counts, and everything else is a lowercase letter. A group's content may be empty, in which case the group expands to nothing.

Reference: this is our own wording of LeetCode problem 394, [Decode String](https://leetcode.com/problems/decode-string/).

## Input

- `s`: the encoded string, made of lowercase letters, digits, `[` and `]`

## Output

The decoded string, with every group replaced by its repeated content.

## Examples

### Example 1

<!-- case: ex1 -->

The group `2[xy]` expands to `xyxy`, and the trailing `z` is copied as it is.

### Example 2

<!-- case: ex2 -->

The inner group `2[m]` expands first, to `mm`, so the outer group repeats `kmm` three times.

## Constraints

- `1 <= s.length <= 10^5`
- `s` contains only lowercase English letters, digits and the characters `[` and `]`.
- Every repeat count is an integer between 1 and 300.
- Groups are nested at most 20 levels deep.
- The decoded string has at most `10^5` characters.

## Follow-ups

- Can you decode in a single left-to-right pass over `s`?
- Write both a recursive and an iterative version. What does each one keep on its stack?
- Repeat counts can have several digits. Where does your parser read them?

## Hints

### Hint 1

The innermost groups contain no brackets inside them, so they can be expanded directly. What happens if you repeat that?

### Hint 2

When a `]` arrives, you need the text collected since the matching `[` and the count written in front of that `[`. Which data structure gives you the most recent unfinished group?

### Hint 3

On `[`, push the current count and the text built so far, then start a fresh text. On `]`, pop them and append the fresh text, repeated, to the text you popped.
