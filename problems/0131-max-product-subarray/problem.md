# Maximum Product Subarray

## Statement

You get an integer array `nums`. A subarray is a non-empty run of consecutive elements. Multiply the elements of each subarray and return the largest product you can get.

The values may be negative or zero, so a long run is not always better: one negative factor flips the sign, two of them flip it back, and a zero wipes the product out.

Reference: this is our own wording of LeetCode problem 152, [Maximum Product Subarray](https://leetcode.com/problems/maximum-product-subarray/).

## Input

- `nums`: the values, in order

## Output

The maximum product over all non-empty subarrays of `nums`.

## Examples

### Example 1

<!-- case: ex1 -->

The two negative values cancel out, so the whole array has the largest product: 2 * (-5) * 3 * 4 * (-1) = 120.

### Example 2

<!-- case: ex2 -->

The zero splits the array. On its left, (-2) * 6 * (-3) = 36 beats 6 alone; on its right, the best is 7.

### Example 3

<!-- case: ex3 -->

A subarray cannot be empty, so the only choice is the single negative value.

## Constraints

- `1 <= nums.length <= 2 * 10^4`
- `-10 <= nums[i] <= 10`
- The product of every subarray fits in a 32-bit signed integer.

## Follow-ups

- Kadane's algorithm keeps only the best sum ending at each position. Why is the best product ending here not enough, and what else do you need?
- Can you solve it in one pass with constant extra memory?
- Can you argue the answer from prefix and suffix products alone, splitting the array at its zeros?

## Hints

### Hint 1

Checking every subarray works in O(n^2): fix the start and extend the product one element at a time.

### Hint 2

A very negative product ending at `i - 1` turns into a very large one when multiplied by a negative `nums[i]`. Keep both the largest and the smallest product of a subarray that ends at each position.

### Hint 3

The product ending at `i` is either `nums[i]` alone, or the largest or smallest product ending at `i - 1` times `nums[i]`.
