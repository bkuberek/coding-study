# Valid Anagram

## Statement

Two strings are anagrams of each other when one can be turned into the other by rearranging its letters: every letter occurs the same number of times in both, and no letter is added or left out.

You get two strings `s` and `t` made of lowercase English letters. Decide whether `t` is an anagram of `s`. A string counts as an anagram of itself.

Reference: this is our own wording of LeetCode problem 242, [Valid Anagram](https://leetcode.com/problems/valid-anagram/).

## Input

- `s`: the original string
- `t`: the string to test against `s`

## Output

`true` if `t` uses exactly the same letters as `s`, each the same number of times, otherwise `false`.

## Examples

### Example 1

<!-- case: ex1 -->

Both strings contain one each of `g`, `h`, `i`, `n` and `t`, only in a different order, so `thing` is an anagram of `night`.

### Example 2

<!-- case: ex2 -->

The strings have the same length and share `a`, `e` and two `p`s, but `paper` has an `r` where `apple` has an `l`. One letter differs, so they are not anagrams.

## Constraints

- `1 <= s.length, t.length <= 5 * 10^4`
- `s` and `t` contain only lowercase English letters (`a` to `z`).
- `s` and `t` may have different lengths.

## Follow-ups

- Can you answer in O(n) time using only a constant amount of extra memory?
- What would change if the strings could contain any Unicode characters, including ones outside the Basic Multilingual Plane?
- How would you check many candidate strings against the same `s` efficiently?

## Hints

### Hint 1

If the lengths differ, can the strings be anagrams?

### Hint 2

Rearranging letters does not change which letters occur or how often. Can you bring both strings into one canonical arrangement and compare those?

### Hint 3

There are only 26 possible letters. Count each letter in `s`, then use `t` to undo the counts. What must the counters look like at the end?
