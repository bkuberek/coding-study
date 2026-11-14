# Fast Power

## Statement

Compute `x` raised to the integer power `n`, written `x^n`, without calling a built-in power function. The exponent can be negative, in which case `x^n = 1 / x^(-n)`, and it can be as large as about two billion in either direction, so multiplying `x` by itself `|n|` times is far too slow.

By convention `x^0 = 1` for every `x`.

Reference: this is our own wording of LeetCode problem 50, [Pow(x, n)](https://leetcode.com/problems/powx-n/).

## Input

- `x`: the base, a floating-point number
- `n`: the exponent, a 32-bit signed integer

## Output

The value of `x^n`. Answers within a relative error of `10^-6` (absolute, for results smaller than 1) are accepted.

## Examples

### Example 1

<!-- case: ex1 -->

`1.5^4 = 1.5 * 1.5 * 1.5 * 1.5 = 5.0625`. With squaring, two multiplications are enough: `1.5^2 = 2.25`, then `2.25^2 = 5.0625`.

### Example 2

<!-- case: ex2 -->

A negative exponent inverts the result: `4^-3 = 1 / 4^3 = 1 / 64 = 0.015625`.

## Constraints

- `-100.0 < x < 100.0`
- `-2^31 <= n <= 2^31 - 1`
- `x` is not 0 when `n` is 0 or negative.
- `-10^4 <= x^n <= 10^4`

## Follow-ups

- Can you do it in O(log |n|) multiplications?
- What goes wrong in Java or Kotlin when you negate `n = -2^31`?
- How would you compute `x^n mod m` for integers, where the intermediate values must stay small?

## Hints

### Hint 1

`x^n = (x^2)^(n/2)` when `n` is even. How many times can you halve `n` before it reaches 0?

### Hint 2

When `n` is odd, set one factor of `x` aside: `x^n = x * (x^2)^((n - 1)/2)`. Reading the bits of `n` from the lowest one tells you which squares to multiply in.

### Hint 3

Handle a negative exponent by replacing `x` with `1 / x` and `n` with `-n`. In Java and Kotlin, `-n` overflows for `n = -2^31`, so move `n` into a 64-bit variable first.
