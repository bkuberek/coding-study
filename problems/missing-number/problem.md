# Missing Number

## Statement

An array `nums` of length `n` holds `n` distinct numbers taken from the `n + 1` numbers `0, 1, ..., n`. Exactly one of those numbers is absent. Return it.

The array is in no particular order. Aim for one pass with constant extra memory.

Reference: this is our own wording of LeetCode problem 268, [Missing Number](https://leetcode.com/problems/missing-number/).

## Input

- `nums`: `n` distinct values between `0` and `n`

## Output

The one number from `0` to `n` that does not appear in `nums`.

## Examples

### Example 1

<!-- case: ex1 -->

The array has length 5, so the candidates are 0 to 5. Every one of them appears except 2.

### Example 2

<!-- case: ex2 -->

With `n = 3` the candidates are 0, 1, 2 and 3. All of 0, 1 and 2 are present, so the missing number is `n` itself.

## Constraints

- `1 <= n == nums.length <= 10^5`
- `0 <= nums[i] <= n`
- All values in `nums` are distinct.

## Follow-ups

- Sorting finds the gap in O(n log n). Can you find it in O(n) time and O(1) extra memory?
- The sum `0 + 1 + ... + n` gets large. Which type does it need in Java or Kotlin, and how does an XOR-based answer avoid the question altogether?
- What if two numbers were missing?

## Hints

### Hint 1

You know exactly which numbers should be there. What can you compute about the full set without looking at the array?

### Hint 2

The full set adds up to `n * (n + 1) / 2`; the array adds up to that minus the missing number.

### Hint 3

The same works with XOR instead of addition: XOR all indices `0..n` and all values; every present number appears twice and cancels.
