# Palindrome Partitioning

## Statement

You get a string `s`. Cut it into consecutive, non-empty pieces so that every piece reads the same forwards and backwards (a palindrome). List every way of doing so.

A partition is the sequence of pieces from left to right; joined together, the pieces give back `s`. Every single character is a palindrome, so at least one partition always exists.

Reference: this is our own wording of LeetCode problem 131, [Palindrome Partitioning](https://leetcode.com/problems/palindrome-partitioning/).

## Input

- `s`: the string to cut

## Output

A list of every valid partition, each as the list of its pieces in left-to-right order. The partitions may be listed in any order, but the pieces inside a partition keep their order.

## Examples

### Example 1

<!-- case: ex1 -->

Besides cutting after every letter, the middle `oo` can stay together, and the whole word `noon` is itself a palindrome.

### Example 2

<!-- case: ex2 -->

Either every letter is its own piece, or the whole string `xyx` forms one palindrome. `xy` and `yx` are not palindromes, so no other cut works.

## Constraints

- `1 <= s.length <= 12`
- `s` consists of lowercase English letters.

## Follow-ups

- Testing a piece costs time proportional to its length. Can you precompute, for every pair of positions, whether the substring between them is a palindrome?
- If you only needed the fewest cuts that make every piece a palindrome, could you avoid listing partitions altogether?

## Hints

### Hint 1

Decide the first piece: it is some palindromic prefix of `s`. Whatever follows must itself be partitioned, which is the same problem on a shorter string.

### Hint 2

Keep the pieces chosen so far in a list. Try each end position for the next piece, recurse when the piece is a palindrome, and remove it again afterwards.

### Hint 3

`s[i..j]` is a palindrome exactly when `s[i] == s[j]` and `s[i+1..j-1]` is a palindrome (or has at most one character). Filling a table with that rule, from short substrings to long ones, answers every check in constant time.
