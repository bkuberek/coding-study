# Regular Expression Matching

## Statement

Implement a tiny regular-expression matcher. A pattern `p` is made of three kinds of items:

- a lowercase letter, which matches exactly that letter;
- `.`, which matches any single letter;
- an item followed by `*`, which matches zero or more repetitions of that item (`a*` matches `""`, `"a"`, `"aa"`, ...; `.*` matches any string).

Return whether the pattern matches the whole string `s`, not just a part of it.

Reference: this is our own wording of LeetCode problem 10, [Regular Expression Matching](https://leetcode.com/problems/regular-expression-matching/).

## Input

- `s`: the string to match
- `p`: the pattern

## Output

`true` if `p` matches all of `s`, otherwise `false`.

## Examples

### Example 1

<!-- case: ex1 -->

`b` matches the first letter, `a*` matches the three a's, and `d` matches the last letter.

### Example 2

<!-- case: ex2 -->

`.` matches `c` and `a` matches `a`, but nothing in the pattern is left for the final `b`. A match must cover the whole string.

## Constraints

- `0 <= s.length <= 1000`
- `1 <= p.length <= 1000`
- `s` contains only lowercase English letters.
- `p` contains only lowercase English letters, `.` and `*`, and every `*` directly follows a letter or a `.` (never at the start, never after another `*`).

## Follow-ups

- Trying every way a starred item can match backtracks exponentially on patterns such as `a*a*a*...b`. Which partial results repeat?
- Can you decide the match with two rows of the table, O(len(p)) extra space?
- How would you add `+` (one or more repetitions)?

## Hints

### Hint 1

Describe the progress by two positions: how much of `s` and how much of `p` is consumed. The answer for the rest depends only on those two numbers.

### Hint 2

If the next pattern item is starred, either skip it entirely (it matches nothing), or, when it matches the next letter of `s`, consume that letter and stay on the same starred item.

### Hint 3

Let `M(i, j)` be whether `s[:i]` matches `p[:j]`. Initialize the empty string against prefixes such as `a*b*`, then fill row by row.
