# Alien Dictionary

## Statement

An alien language writes with some of the lowercase English letters, but orders them differently from English. You get a list `words` that is claimed to be sorted in that language's dictionary order. Recover a letter order that explains it.

Dictionary order compares two words at their first position where the letters differ: the word whose letter comes first in the alphabet comes first. If one word is a prefix of the other, the shorter word comes first, so `ab` may not appear after `abc`.

Return a string that contains every letter appearing in `words` exactly once, ordered so that `words` is sorted under that alphabet. If no such order exists, return the empty string. When several orders work, any of them is accepted.

Reference: this is our own wording of LeetCode problem 269, [Alien Dictionary](https://leetcode.com/problems/alien-dictionary/).

## Input

- `words`: the words, in the claimed sorted order

## Output

A string with each letter of `words` exactly once, in an order under which `words` is sorted, or `""` when no order works.

## Examples

### Example 1

<!-- case: ex1 -->

`tea` before `tab` first differ at `e` and `a`, so `e` comes before `a`. `tab` before `eat` puts `t` before `e`, and `eat` before `bat` puts `e` before `b`. Both `teab` and `teba` satisfy all three rules; either is accepted.

### Example 2

<!-- case: ex2 -->

`ca` before `ab` needs `c` before `a`, but `ab` before `cb` needs `a` before `c`. No alphabet can do both.

## Constraints

- `1 <= words.length <= 1000`
- `1 <= words[i].length <= 20`
- `words[i]` consists of lowercase English letters.

## Follow-ups

- Why do only adjacent words matter? Would comparing every pair of words tell you anything new?
- Which letters can go anywhere in the answer?
- How do you detect the case where a longer word comes right before its own prefix?

## Hints

### Hint 1

Two neighboring words give at most one rule: at their first differing position, the first word's letter comes before the second word's letter. Letters after that position tell you nothing.

### Hint 2

The rules form a directed graph on the letters. A valid alphabet is an order of the letters that respects every arrow: a topological order. A cycle means there is none.

### Hint 3

Watch for a pair where the second word is a proper prefix of the first, such as `abc` followed by `ab`: no alphabet can sort that, so the answer is `""`. And remember to include letters that take part in no rule.
