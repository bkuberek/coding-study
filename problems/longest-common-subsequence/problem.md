# Longest Common Subsequence

## Statement

A subsequence of a string is what remains after deleting any number of its characters (possibly none) without changing the order of the others: `"rbr"` is a subsequence of `"harbor"`, but `"rab"` is not.

You get two strings, `text1` and `text2`. Return the length of the longest string that is a subsequence of both. If they have no character in common, the answer is 0.

Reference: this is our own wording of LeetCode problem 1143, [Longest Common Subsequence](https://leetcode.com/problems/longest-common-subsequence/).

## Input

- `text1`: the first string
- `text2`: the second string

## Output

The length of a longest common subsequence of `text1` and `text2`.

## Examples

### Example 1

<!-- case: ex1 -->

`"arbr"` is a subsequence of both words: in `"harbor"` it skips the `h` and the `o`, in `"arbiter"` it skips `i`, `t` and `e`. No common subsequence of length 5 exists, since `"harbor"` has an `o` and `"arbiter"` does not.

### Example 2

<!-- case: ex2 -->

The two strings share no character, so the only common subsequence is the empty string.

## Constraints

- `1 <= text1.length, text2.length <= 1000`
- Both strings contain only lowercase English letters.

## Follow-ups

- Trying all subsequences of one string is exponential. What smaller question does the answer depend on when you look at the first characters of both strings?
- The table reads only the previous row. Can you solve it in O(min(m, n)) extra space?
- How would you return one longest common subsequence instead of its length?

## Hints

### Hint 1

Compare the first characters. If they are equal, some longest common subsequence starts with that character. If not, at least one of the two can be dropped.

### Hint 2

Let `L(i, j)` be the answer for the suffixes starting at `i` and `j`. Then `L(i, j) = 1 + L(i + 1, j + 1)` on a match, and `max(L(i + 1, j), L(i, j + 1))` otherwise.

### Hint 3

Fill the table from the ends of the strings backwards (or the mirror image over prefixes); each entry needs only its right, lower and diagonal neighbors.
