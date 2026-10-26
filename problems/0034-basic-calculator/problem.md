# Basic Calculator

## Statement

You get an arithmetic expression as a string: non-negative integers joined by the operators `+`, `-`, `*` and `/`, with any number of spaces between and around the tokens. Evaluate it and return the result.

Use the usual precedence: `*` and `/` bind tighter than `+` and `-`, and operators of the same precedence apply from left to right. Division between integers truncates toward zero. There are no parentheses and no unary minus, and you may not call a built-in expression evaluator such as `eval`.

The expression is always valid, never divides by zero, and every partial result fits in a 32-bit signed integer.

Reference: this is our own wording of LeetCode problem 227, [Basic Calculator II](https://leetcode.com/problems/basic-calculator-ii/).

## Input

- `s`: the expression; digits, the four operators and spaces only

## Output

The integer value of the expression.

## Examples

### Example 1

<!-- case: ex1 -->

The multiplication happens first: `6 * 2` is 12, and `4 + 12` is 16. Evaluating strictly left to right would give 20 instead.

### Example 2

<!-- case: ex2 -->

`20 / 6` is 3.33, truncated to 3, and `3 * 2` is 6. Then the additive operators apply from left to right: `3 - 6 + 1` is -2. The result can be negative even though every number in the expression is non-negative.

## Constraints

- `1 <= s.length <= 3 * 10^5`
- `s` contains only digits, spaces and the characters `+`, `-`, `*` and `/`.
- Every number is between 0 and `2^31 - 1`.
- The expression is valid, no division by zero occurs, and every partial result of evaluating it fits in a 32-bit signed integer.

## Follow-ups

- Can you evaluate the expression in one pass, without first splitting it into tokens?
- Can you do it with O(1) extra memory?
- How would you extend your solution to support parentheses?

## Hints

### Hint 1

An expression without parentheses is a sum of terms, where each term is a chain of `*` and `/`. For example `2 + 3 * 4 - 5` is `2 + 12 - 5`.

### Hint 2

Read the expression left to right and remember the operator that came before the current number. A `+` or `-` starts a new term; a `*` or `/` changes the current term.

### Hint 3

Keep the finished part of the sum and the term still being built. When a new `+` or `-` arrives, the pending term is complete and can be added to the total.
