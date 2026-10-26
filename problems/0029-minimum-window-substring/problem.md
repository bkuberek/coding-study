# Minimum Window Substring

## Statement

You get two strings of English letters, `s` and `t`. Find the shortest substring of `s` that contains every letter of `t`, counting repeats: if `t` has a letter three times, the substring must contain it at least three times. Other letters may appear in the substring as well.

If several substrings share the shortest length, return the one that starts furthest to the left. If no substring of `s` covers `t`, return the empty string.

Uppercase and lowercase letters are different letters.

Reference: this is our own wording of LeetCode problem 76, [Minimum Window Substring](https://leetcode.com/problems/minimum-window-substring/).

## Input

- `s`: the string to search
- `t`: the letters, with multiplicities, that the window must contain

## Output

The shortest substring of `s` whose letter counts are at least those of `t`, the leftmost one on ties, or `""` when there is none.

## Examples

### Example 1

<!-- case: ex1 -->

`bat`, at positions 8 to 10, contains `t`, `a` and `b`. The earlier window `atingb` covers them too, but it is twice as long.

### Example 2

<!-- case: ex2 -->

`t` needs three `n`s, and `banana` has only two, so no window exists.

### Example 3

<!-- case: ex3 -->

Both `ab` (positions 0 and 1) and `ba` (positions 3 and 4) are shortest windows. The leftmost one is the answer.

## Constraints

- `1 <= s.length <= 10^5`
- `1 <= t.length <= 10^5`
- `s` and `t` contain only the letters `a` to `z` and `A` to `Z`.

## Follow-ups

- Growing a window from every start is quadratic. Can you find the answer in O(n + m)?
- How do you know in O(1) whether the current window covers `t`, without comparing all letter counts?
- If `t` uses only a few letters and `s` is huge, can you skip the letters of `s` that never matter?

## Hints

### Hint 1

For a fixed start, extend the window until it covers `t`. That is the shortest window with this start.

### Hint 2

Slide a window instead: extend the right edge until the window covers `t`, then move the left edge as far as possible while it still covers `t`. Record each such window.

### Hint 3

Keep, per letter, how many more copies the window still needs, and a single counter of the copies still missing overall. The window covers `t` exactly when that counter is 0.
