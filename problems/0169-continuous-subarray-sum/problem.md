# Continuous Subarray Sum

## Statement

You get an array `nums` of non-negative integers and a positive integer `k`. Decide whether some run of at least two consecutive values adds up to a multiple of `k`.

A multiple of `k` is `t * k` for some integer `t >= 0`, so a run that adds up to 0 counts as well. A run of a single value never counts, whatever it holds.

Reference: this is our own wording of LeetCode problem 523, [Continuous Subarray Sum](https://leetcode.com/problems/continuous-subarray-sum/).

## Input

- `nums`: the non-negative values
- `k`: the divisor

## Output

`true` if there are positions `i < j` with `nums[i] + ... + nums[j]` divisible by `k`, otherwise `false`.

## Examples

### Example 1

<!-- case: ex1 -->

The run `[4, 8]` at positions 2 and 3 adds up to 12, which is `2 * 6`. It is the only qualifying run: every other run adds up to a number that leaves a remainder when divided by 6.

### Example 2

<!-- case: ex2 -->

No run of two or more values adds up to a multiple of 7: the runs add up to 9, 10, 6, 12, 13 and 15. The single value 7 at position 1 is a multiple of 7, but runs of one value do not count.

## Constraints

- `1 <= nums.length <= 10^5`
- `0 <= nums[i] <= 10^9`
- `1 <= k <= 2^31 - 1`
- The sum of the whole array can reach `10^14`, more than a 32-bit `int` holds.

## Follow-ups

- Checking every run is O(n^2). Can you decide it in one pass?
- Which property of remainders lets you ignore the actual sums?
- How would you count the qualifying runs instead of only detecting one? What changes when they must have length at least two?

## Hints

### Hint 1

A run `nums[i..j]` adds up to `prefix[j + 1] - prefix[i]`. When is a difference of two numbers divisible by `k`?

### Hint 2

The difference is divisible by `k` exactly when both prefixes leave the same remainder modulo `k`.

### Hint 3

Remember the first position at which each remainder appeared (the empty prefix has remainder 0 at position -1). A repeat at least two positions later is a valid run.
