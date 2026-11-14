# Interleaving String

## Statement

Two strings are interleaved by merging their characters into one string while keeping the order of each: you repeatedly take the next unused character of either `s1` or `s2`, in any pattern you like, until both are used up. For example, `"dcoagt"` interleaves `"dog"` and `"cat"`.

Given `s1`, `s2` and `s3`, decide whether `s3` can be obtained by interleaving `s1` and `s2`. Every character of `s1` and `s2` must be used exactly once, so the lengths have to add up.

Reference: this is our own wording of LeetCode problem 97, [Interleaving String](https://leetcode.com/problems/interleaving-string/).

## Input

- `s1`: the first source string
- `s2`: the second source string
- `s3`: the string to explain as an interleaving

## Output

`true` if `s3` is an interleaving of `s1` and `s2`, otherwise `false`.

## Examples

### Example 1

<!-- case: ex1 -->

Take `d` from `"dog"`, `c` from `"cat"`, then `o`, `a`, `g` and `t` alternately: the result is `"dcoagt"`.

### Example 2

<!-- case: ex2 -->

`"bac"` has the right letters, but it puts the `b` of `"ab"` before its `a`. Interleaving never reorders the characters of one source.

## Constraints

- `0 <= s1.length, s2.length <= 1000`
- `0 <= s3.length <= 2000`
- All strings contain only lowercase English letters.

## Follow-ups

- When the next character of `s3` matches the next character of both sources, a greedy choice can go wrong. How do you avoid exploring the same situation twice?
- Can you decide it with one row of booleans, O(min(m, n)) extra space?
- How would you return which source each character of `s3` came from?

## Hints

### Hint 1

After matching a prefix of `s3`, all that matters is how many characters of `s1` (say `i`) and of `s2` (say `j`) were used; then exactly `i + j` characters of `s3` are matched.

### Hint 2

Let `R(i, j)` say whether `s1[:i]` and `s2[:j]` interleave to `s3[:i + j]`. It is true if `R(i - 1, j)` holds and `s1[i - 1] == s3[i + j - 1]`, or if `R(i, j - 1)` holds and `s2[j - 1] == s3[i + j - 1]`.

### Hint 3

Check the lengths first. Then fill the table row by row; each row depends only on the previous one.
