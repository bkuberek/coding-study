# Partition Labels

## Statement

You get a string `s` of lowercase letters. Cut it into as many consecutive pieces as possible so that every letter appears in at most one piece: all copies of a letter must land in the same piece. Joining the pieces in order gives back `s`.

Return the lengths of the pieces, from left to right.

Reference: this is our own wording of LeetCode problem 763, [Partition Labels](https://leetcode.com/problems/partition-labels/).

## Input

- `s`: the string to cut

## Output

The lengths of the pieces of a partition with the largest number of pieces, in order. That partition is unique.

## Examples

### Example 1

<!-- case: ex1 -->

The pieces are "a", "bcb", "defed", "g" and "h". Both copies of `b` are in "bcb", and the copies of `d` and `e` are all in "defed". Cutting "defed" any further would split a letter.

### Example 2

<!-- case: ex2 -->

The two copies of `x` sit at both ends, so the whole string must stay in one piece.

## Constraints

- `1 <= s.length <= 10^4`
- `s` contains only lowercase English letters.

## Follow-ups

- Searching for the last copy of each letter again and again is O(n^2). What can you precompute once?
- How is this related to merging overlapping intervals?
- Why is it safe to cut as soon as possible, and why does that give the most pieces?

## Hints

### Hint 1

The piece that contains the first letter must reach at least the last occurrence of that letter.

### Hint 2

Record the last index of every letter. Walk through the string extending the current piece's end to the last index of each letter you pass; when your position equals that end, cut.
