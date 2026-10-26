# Distinct Subsequences

## Statement

You get two strings, `s` and `t`. Count the ways to pick characters of `s`, keeping their order, that spell out exactly `t`. Two ways are different if they use a different set of positions in `s`, even when the spelled string is the same.

In other words, count the occurrences of `t` as a subsequence of `s`. If `t` is longer than `s`, or some letter of `t` cannot be matched in order, the answer is 0.

Reference: this is our own wording of LeetCode problem 115, [Distinct Subsequences](https://leetcode.com/problems/distinct-subsequences/).

## Input

- `s`: the string to pick characters from
- `t`: the string to spell

## Output

The number of sets of positions in `s` whose characters, in order, spell `t`.

## Examples

### Example 1

<!-- case: ex1 -->

`"bananas"` has `a` at positions 1, 3 and 5 and `n` at positions 2 and 4. An occurrence of `"ana"` picks an `a`, a later `n` and a later `a`: positions (1, 2, 3), (1, 2, 5), (1, 4, 5) and (3, 4, 5), four ways.

### Example 2

<!-- case: ex2 -->

`"ca"` needs an `a` after a `c`, but the only `a` of `"abc"` comes before its `c`.

## Constraints

- `1 <= s.length, t.length <= 1000`
- Both strings contain only English letters; upper and lower case letters are different.
- The answer fits in a signed 32-bit integer, and so does the count for every pair of prefixes of `s` and `t` and for every pair of suffixes, so no DP table overflows.

## Follow-ups

- Listing all subsequences of `s` is exponential. What smaller question remains after you decide whether the first character of `s` is used?
- Can you count with a single array as long as `t`?
- How does the answer change if the same set of letters in different positions should count only once?

## Hints

### Hint 1

Look at the first character of `s`. Every occurrence either skips it, or uses it to match the first character of `t`, which is only possible when the two are equal.

### Hint 2

Let `W(i, j)` be the number of occurrences of `t[j:]` in `s[i:]`. Then `W(i, j) = W(i + 1, j) + (W(i + 1, j + 1) if s[i] == t[j])`, with `W(i, len(t)) = 1` and `W(len(s), j) = 0` for `j < len(t)`.

### Hint 3

With prefixes instead, keep one array `ways[j]` for "occurrences of `t[:j]` so far" and, for each character of `s`, update `j` from right to left so each character is used at most once per occurrence.
