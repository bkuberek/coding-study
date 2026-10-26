# Evaluate Reverse Polish Notation

## Statement

In reverse Polish notation (postfix notation), every operator comes after its two operands instead of between them, so no parentheses are needed: `3 4 + 2 *` means `(3 + 4) * 2`. Reading left to right, an operator applies to the two values produced most recently that have not been used yet; the earlier of the two is the left operand.

You get such an expression as a list of tokens. Each token is an integer or one of the operators `+`, `-`, `*` and `/`. Evaluate the expression and return its value.

Division between integers truncates toward zero: `7 / -2` is `-3`, not `-4`. The expression is always valid, never divides by zero, and every intermediate value fits in a 32-bit signed integer.

Reference: this is our own wording of LeetCode problem 150, [Evaluate Reverse Polish Notation](https://leetcode.com/problems/evaluate-reverse-polish-notation/).

## Input

- `tokens`: the expression in postfix order; each token is `+`, `-`, `*`, `/` or an integer such as `17` or `-3`

## Output

The integer value of the expression.

## Examples

### Example 1

<!-- case: ex1 -->

The `+` adds 3 and 8 into 11, and the `*` multiplies that result by 2, which gives 22. In ordinary notation this is `(3 + 8) * 2`.

### Example 2

<!-- case: ex2 -->

First `20 / -6` is about -3.33, which truncates toward zero to -3. Then `-3 - 1` gives -4. Note that the token `-6` is a negative number, while the last token `-` is the subtraction operator.

## Constraints

- `1 <= tokens.length <= 10^4`
- Each token is `+`, `-`, `*`, `/` or an integer between -200 and 200.
- The tokens form a valid expression.
- No division by zero occurs, and the result and every intermediate value fit in a 32-bit signed integer.

## Follow-ups

- Can you evaluate the expression in a single left-to-right pass?
- How would you convert an ordinary infix expression with parentheses into postfix order?
- How would you also check that the tokens form a valid expression, and report the first token where they do not?

## Hints

### Hint 1

When you read an operator, its operands are the two most recent values that no operator has consumed yet.

### Hint 2

"Most recent first" is the access pattern of a stack. Push numbers; on an operator, pop two values, apply it and push the result.

### Hint 3

The first value popped is the right operand. For `-` and `/` the order matters.
