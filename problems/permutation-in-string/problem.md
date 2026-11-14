# Permutation in String

## Statement

You get two strings of lowercase English letters, `pattern` and `text`. Decide whether some rearrangement of all the letters of `pattern` appears in `text` as a contiguous block.

In other words, look for a substring of `text` that has exactly the same letters as `pattern`, each the same number of times, in any order.

Reference: this is our own wording of LeetCode problem 567, [Permutation in String](https://leetcode.com/problems/permutation-in-string/).

## Input

- `pattern`: the letters to look for, in any order
- `text`: the string to search

## Output

`true` when some substring of `text` of length `pattern.length` is a rearrangement of `pattern`, otherwise `false`.

## Examples

### Example 1

<!-- case: ex1 -->

The substring `art`, at positions 2 to 4 of `smartly`, uses the letters `r`, `a` and `t` once each, just like `rat`.

### Example 2

<!-- case: ex2 -->

`goodness` contains `g`, `o` and `d`, but no three consecutive letters are exactly one `d`, one `o` and one `g`: `goo` has two `o`s and no `d`, and `ood` has no `g`.

## Constraints

- `1 <= pattern.length <= 10^5`
- `1 <= text.length <= 10^5`
- Both strings contain only the lowercase letters `a` to `z`.

## Follow-ups

- Sorting every window of the text is slow. Which property of a window can you update in O(1) when it slides by one position?
- Comparing two arrays of 26 counts at every step is cheap but not free. Can you know in O(1) whether the counts match?
- How would you return every starting position of a match instead of a yes or no?

## Hints

### Hint 1

Two strings are rearrangements of each other exactly when they have the same letter counts.

### Hint 2

Every candidate substring has the same length as `pattern`. Slide a window of that length across `text`; each step adds one letter on the right and removes one on the left.

### Hint 3

Keep, for each of the 26 letters, the difference between its count in the window and in the pattern, and count how many letters have a difference of zero. The window matches when all 26 do.
