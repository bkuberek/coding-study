# Single Number

## Statement

You get a non-empty array of integers in which every value occurs exactly twice, except for one value that occurs exactly once. Return that lonely value.

Aim for a single pass that uses only a constant amount of extra memory.

Reference: this is our own wording of LeetCode problem 136, [Single Number](https://leetcode.com/problems/single-number/).

## Input

- `nums`: the values, in any order

## Output

The value that occurs exactly once.

## Examples

### Example 1

<!-- case: ex1 -->

The values 8 and -2 occur twice each, while 5 occurs once.

### Example 2

<!-- case: ex2 -->

An array of one element holds the answer itself.

## Constraints

- `1 <= nums.length <= 3 * 10^5`, and the length is odd.
- `-2^31 <= nums[i] <= 2^31 - 1`
- Exactly one value occurs once; every other value occurs exactly twice.

## Follow-ups

- A hash map of counts solves it in O(n) time and O(n) memory. Can you use O(1) memory?
- What if every other value occurred three times instead of twice?
- What if two values occurred once, and you had to return both?

## Hints

### Hint 1

Is there an operation under which a value combined with itself vanishes, and that does not care about order?

### Hint 2

Exclusive or: `a ^ a = 0`, `a ^ 0 = a`, and `^` is commutative and associative.

### Hint 3

XOR all the values. The pairs cancel, whatever their order, and only the lonely value remains.
