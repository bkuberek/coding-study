# Longest Repeating Replacement

## Statement

You get a string `s` of uppercase English letters and a budget `k`. You may overwrite at most `k` characters of `s`, each with any uppercase letter you like. Afterwards, find the longest substring that consists of a single repeated letter.

Return the length of the longest such substring you can obtain with the best choice of replacements.

Reference: this is our own wording of LeetCode problem 424, [Longest Repeating Character Replacement](https://leetcode.com/problems/longest-repeating-character-replacement/).

## Input

- `s`: the letters, from `A` to `Z`
- `k`: the largest number of characters you may overwrite

## Output

The maximum length of a substring of one repeated letter that at most `k` replacements can produce.

## Examples

### Example 1

<!-- case: ex1 -->

Overwriting the `Y` with an `X` gives `XXXXXZX`, which starts with five `X`s. The `Z` still breaks the run, and with one replacement you cannot fix both the `Y` and the `Z`.

### Example 2

<!-- case: ex2 -->

Any four consecutive letters contain one letter twice, so replacing the other two gives four equal letters, for example `XYZX` becomes `XXXX`. Five letters always need three replacements.

## Constraints

- `1 <= s.length <= 10^5`
- `s` contains only the uppercase letters `A` to `Z`.
- `0 <= k <= s.length`

## Follow-ups

- Checking every substring is quadratic or worse. Can you do it in one pass?
- A window is fixable when its length minus the count of its most common letter is at most `k`. Do you need to recompute that count exactly when the window shrinks?
- How would you also report which letter and which substring achieve the maximum?

## Hints

### Hint 1

For a fixed substring, which letter should all the others be replaced with, and how many replacements does that take?

### Hint 2

A substring works exactly when `length - (count of its most common letter) <= k`. Keep a window with letter counts and slide it across `s`.

### Hint 3

You only care about windows longer than the best one found so far. That lets the window slide by one instead of shrinking, and the most common count never has to decrease.
