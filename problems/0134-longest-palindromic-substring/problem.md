# Longest Palindromic Substring

## Statement

You get a string `s`. A palindrome reads the same from left to right and from right to left, and a substring is a run of consecutive characters of `s`. Return a longest substring of `s` that is a palindrome.

When several palindromic substrings share the maximum length, any one of them is accepted. Characters are compared exactly, so `A` and `a` are different.

Reference: this is our own wording of LeetCode problem 5, [Longest Palindromic Substring](https://leetcode.com/problems/longest-palindromic-substring/).

## Input

- `s`: the string to search

## Output

A palindromic substring of `s` whose length is the largest possible. Any one of the longest ones is accepted.

## Examples

### Example 1

<!-- case: ex1 -->

"abacaba" reads the same both ways and has seven characters; no longer substring is a palindrome.

### Example 2

<!-- case: ex2 -->

A palindrome can have even length, with no single middle character: "noon" is the longest here.

### Example 3

<!-- case: ex3 -->

No two characters match, so the longest palindromes are the single characters. Any of them, for example "c", is accepted.

## Constraints

- `1 <= s.length <= 1000`
- `s` contains only English letters (upper and lower case) and digits.

## Follow-ups

- Checking every substring separately takes O(n^3) time. Which checks can reuse the result of a shorter one?
- Can you get O(n^2) time with only O(1) extra memory?
- Is there a linear-time algorithm?

## Hints

### Hint 1

A substring `s[i..j]` of length at least 3 is a palindrome exactly when `s[i] == s[j]` and `s[i + 1..j - 1]` is a palindrome.

### Hint 2

Every palindrome has a center: a character (odd length) or the gap between two characters (even length). There are only `2n - 1` centers.

### Hint 3

From each center, grow outwards while the two ends match. Remember the longest span you found.
