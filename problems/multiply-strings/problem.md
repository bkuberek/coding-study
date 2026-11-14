# Multiply Strings

## Statement

Two non-negative integers are given as decimal strings, `num1` and `num2`, possibly with thousands of digits, far beyond any built-in integer type. Return their product, also as a decimal string.

Work digit by digit: do not convert the inputs to a big-integer type (Python `int`, Java `BigInteger`, JavaScript `BigInt`) and do not multiply them as whole numbers. The tests cannot detect a conversion, but the exercise is the digit arithmetic.

Reference: this is our own wording of LeetCode problem 43, [Multiply Strings](https://leetcode.com/problems/multiply-strings/).

## Input

- `num1`, `num2`: the factors, made of the digits `0` to `9`, without leading zeros unless the number is `"0"` itself

## Output

The product as a decimal string without leading zeros (`"0"` when the product is zero).

## Examples

### Example 1

<!-- case: ex1 -->

`46 * 7 = 322`: the units give `6 * 7 = 42`, write 2 and carry 4; then `4 * 7 + 4 = 32`.

### Example 2

<!-- case: ex2 -->

`999 * 12 = 11988`, which has `3 + 2 = 5` digits: a product never has more digits than the two factors together.

## Constraints

- `1 <= num1.length, num2.length <= 2000`
- `num1` and `num2` consist of digits only.
- Neither has leading zeros, except the number `"0"` itself.

## Follow-ups

- How many digits can the product have at most, and why does that let you allocate the result once?
- Can you avoid building and adding a separate string for every digit of `num2`?
- Karatsuba multiplication needs about `n^1.585` digit operations instead of `n^2`. How does it split the numbers?

## Hints

### Hint 1

Long multiplication from school works: multiply `num1` by each digit of `num2`, shift, and add the rows.

### Hint 2

The product of digit `i` of `num1` and digit `j` of `num2` (counted from the left) contributes to position `i + j + 1` of an array of `m + n` result digits.

### Hint 3

Add each digit product into its position and push the carry one position to the left as you go. Skip leading zeros when you build the final string.
