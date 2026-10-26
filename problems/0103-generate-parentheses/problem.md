# Generate Parentheses

## Statement

You get a positive integer `n`. List every string made of exactly `n` opening brackets `(` and `n` closing brackets `)` that is correctly nested: reading from left to right, every `)` closes an earlier `(` that is still open, and nothing is left open at the end.

Reference: this is our own wording of LeetCode problem 22, [Generate Parentheses](https://leetcode.com/problems/generate-parentheses/).

## Input

- `n`: the number of bracket pairs

## Output

A list of every correctly nested string with `n` pairs, each exactly once. The strings may come in any order.

## Examples

### Example 1

<!-- case: ex1 -->

With three pairs there are five shapes: three brackets nested inside each other, three side by side, and the three mixtures of a nested pair with a single pair.

### Example 2

<!-- case: ex2 -->

One pair can only be written one way.

## Constraints

- `1 <= n <= 10`

## Follow-ups

- How would you test whether a given bracket string is correctly nested, using a counter instead of a stack?
- Can you build only valid strings, so that no candidate ever has to be rejected?
- The number of answers is the n-th Catalan number. How fast does it grow compared with 4^n?

## Hints

### Hint 1

A string is correctly nested exactly when no prefix contains more `)` than `(`, and the totals are equal at the end.

### Hint 2

Build the string one character at a time. You may add `(` while fewer than `n` have been used.

### Hint 3

You may add `)` only while it closes something, that is, while more `(` than `)` have been written. With both rules, every complete string is valid.
