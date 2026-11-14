# Remove K Digits

## Statement

You get a non-negative integer written as a string of decimal digits, `num`, and an integer `k`. Delete exactly `k` of its digits; the remaining digits keep their original order. Make the resulting number as small as possible and return it as a string.

Write the result without leading zeros. If no digit remains, or only zeros remain, the result is `"0"`.

Reference: this is our own wording of LeetCode problem 402, [Remove K Digits](https://leetcode.com/problems/remove-k-digits/).

## Input

- `num`: the digits of the number, most significant first
- `k`: how many digits to delete

## Output

The smallest number that can be obtained, as a decimal string without leading zeros (`"0"` for zero).

## Examples

### Example 1

<!-- case: ex1 -->

Of the two-digit numbers that keep the order of `4372` (43, 47, 42, 37, 32 and 72), the smallest is 32: deleting the 4 and the 7, which are both followed by a smaller digit.

### Example 2

<!-- case: ex2 -->

Deleting the leading 3 leaves `0051`, which is written `51`. Deleting any other digit leaves a number that still starts with 3.

## Constraints

- `1 <= num.length <= 10^5`
- `0 <= k <= num.length`
- `num` contains only the digits `0` to `9` and has no leading zeros, except for the number `"0"` itself.

## Follow-ups

- Rescanning from the start after every deletion costs O(n * k). Can you decide every digit in one left-to-right pass?
- What should happen with the remaining deletions once the digits stop decreasing?
- How would you build the largest number by keeping exactly `m` digits instead?

## Hints

### Hint 1

The leftmost digits matter most. Where should the first deletion go so that the number becomes as small as possible?

### Hint 2

Delete the first digit that is larger than the digit right after it. If the digits never decrease, delete the last one.

### Hint 3

Keep the digits you have decided to keep on a stack. While deletions remain and the top is larger than the next digit, pop it. Afterwards, spend any remaining deletions on the end, then strip leading zeros.
