# Group Anagrams

## Statement

Two words are anagrams of each other when they contain the same letters with the same counts, possibly in a different order. Being anagrams is an all-or-nothing relation: if `a` is an anagram of `b` and `b` of `c`, then `a` is an anagram of `c`.

You get a list of lowercase words `strs`. Split it into groups so that two words land in the same group exactly when they are anagrams of each other. Every word, including repeated words and the empty word, belongs to exactly one group.

Reference: this is our own wording of LeetCode problem 49, [Group Anagrams](https://leetcode.com/problems/group-anagrams/).

## Input

- `strs`: the words to group; a word may be empty and may appear more than once

## Output

A list of groups, each group a list of words. Every position of `strs` appears in exactly one group, so a word that occurs twice in `strs` appears twice in its group. The groups may come in any order, and the words inside a group may come in any order.

## Examples

### Example 1

<!-- case: ex1 -->

`night` and `thing` use the letters `g h i n t`; `elbow`, `below` and `bowel` use `b e l o w`; `study` and `dusty` use `d s t u y`. That gives three groups.

### Example 2

<!-- case: ex2 -->

The two empty words are anagrams of each other (both have no letters), so they share a group. `b` forms a group on its own.

## Constraints

- `1 <= strs.length <= 10^4`
- `0 <= strs[i].length <= 100`
- Every word contains only lowercase English letters (`a` to `z`).

## Follow-ups

- Comparing each word with every group is quadratic in the number of words. Which single value could identify a group, so that a hash map finds it directly?
- Sorting each word costs O(k log k). Can you build a group key in O(k)?
- How would you return the groups ordered by size, largest first?

## Hints

### Hint 1

Two words are anagrams exactly when they look identical after you rearrange their letters into one fixed order. Which order?

### Hint 2

Use that rearranged form as a key. Words with the same key belong together.

### Hint 3

A hash map from key to the list of words seen so far groups everything in one pass.

### Hint 4

Instead of sorting, count the 26 letters of a word. The tuple of counts is also a key that all anagrams share.
