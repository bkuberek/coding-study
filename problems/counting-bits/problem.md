# Counting Bits

## Statement

You get a non-negative integer `n`. Return an array `bits` of length `n + 1` in which `bits[i]` is the number of 1s in the binary representation of `i`, for every `i` from 0 to `n`.

Counting the bits of each number on its own works, but the counts of different numbers are closely related. Aim for a single pass that spends constant time per number.

Reference: this is our own wording of LeetCode problem 338, [Counting Bits](https://leetcode.com/problems/counting-bits/).

## Input

- `n`: the largest number to describe

## Output

An array of `n + 1` counts, where entry `i` is the number of set bits of `i`.

## Examples

### Example 1

<!-- case: ex1 -->

In binary, 0 to 6 are `0`, `1`, `10`, `11`, `100`, `101` and `110`, which have 0, 1, 1, 2, 1, 2 and 2 set bits.

### Example 2

<!-- case: ex2 -->

For `n = 0` the array has one entry: 0 has no set bits.

## Constraints

- `0 <= n <= 10^6`

## Follow-ups

- Counting each number separately costs O(log n) per number. Can every entry cost O(1)?
- Can you do it without any built-in popcount function?
- Which other relation between `i` and a smaller number gives the same kind of recurrence?

## Hints

### Hint 1

Compare the binary forms of `i` and `i / 2` (integer division). What does shifting right by one do to the bits?

### Hint 2

`i >> 1` has the same bits as `i` except for the lowest one, which is dropped.

### Hint 3

`bits[i] = bits[i >> 1] + (i & 1)`, and `i >> 1` is smaller than `i`, so it is already known when you fill the array in increasing order.
