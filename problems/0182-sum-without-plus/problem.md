# Sum Without Arithmetic Operators

## Statement

Return the sum of two 32-bit signed integers `a` and `b` without using the arithmetic operators `+` and `-` on them (nor `+=`, `-=`, `sum` or similar library calls). Only bitwise operations are allowed for the addition itself: AND, OR, XOR, NOT and shifts. Loop counters may be incremented as usual.

Negative numbers use the usual two's complement representation. The inputs are chosen so that the true sum fits in a 32-bit signed integer.

Reference: this is our own wording of LeetCode problem 371, [Sum of Two Integers](https://leetcode.com/problems/sum-of-two-integers/).

## Input

- `a`, `b`: the two 32-bit signed integers to add

## Output

The value `a + b`.

## Examples

### Example 1

<!-- case: ex1 -->

In binary, `5 = 101` and `6 = 110`. The two lowest columns hold a single 1 each and add up without a carry. The third column holds two 1s, which gives 0 there and a carry into the fourth column. The result `1011` is 11.

### Example 2

<!-- case: ex2 -->

With a negative operand: `-8 + 3 = -5`. In 32-bit two's complement, `-8` is `11...11000` and adding `00...00011` gives `11...11011`, which is `-5`; no carry ever moves.

## Constraints

- `-2^31 <= a, b <= 2^31 - 1`
- `-2^31 <= a + b <= 2^31 - 1`

## Follow-ups

- How do you add two bits, and what does the carry of a column look like in terms of AND and XOR?
- Can you add all 32 columns at once and only then deal with the carries?
- Python integers have no fixed width. How do you emulate 32-bit wraparound and recover a negative result?

## Hints

### Hint 1

For one column, the sum bit is `x XOR y XOR carry_in`, and a carry goes out when at least two of the three bits are 1.

### Hint 2

`a XOR b` adds every column at once but ignores the carries; `(a AND b) << 1` is exactly the carries, moved to the column they go into.

### Hint 3

Repeat with `a = a XOR b` and `b = (a AND b) << 1` until no carry is left. In Python, mask to 32 bits with `0xFFFFFFFF` at each step and convert a result with the top bit set back to a negative number.
