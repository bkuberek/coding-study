# Product Except Self

## Statement

You get an integer array `nums` of length `n`. Build a new array `answer` of the same length in which `answer[i]` is the product of every element of `nums` except the one at position `i`.

Division is not allowed: you may not compute the product of the whole array and then divide by `nums[i]`. Aim for a solution whose running time grows linearly with `n`.

Reference: this is our own wording of LeetCode problem 238, [Product of Array Except Self](https://leetcode.com/problems/product-of-array-except-self/).

## Input

- `nums`: the integers to multiply; zeros and negative values may occur

## Output

An array `answer` of length `n` where `answer[i]` equals the product of `nums[j]` over all positions `j != i`.

## Examples

### Example 1

<!-- case: ex1 -->

Leaving out position 0 multiplies 3, 1 and 5, which gives 15. Leaving out position 2 multiplies 2, 3 and 5, which gives 30, and so on for the other positions.

### Example 2

<!-- case: ex2 -->

The zero at position 1 makes every product that includes it zero. Only `answer[1]`, which leaves the zero out, is non-zero: -2 * 4 * 1 = -8.

## Constraints

- `2 <= nums.length <= 10^5`
- `-30 <= nums[i] <= 30`
- Multiplying together any selection of elements of `nums` gives a value that fits in a 32-bit signed integer.
- Division is not allowed.

## Follow-ups

- Recomputing each product from scratch takes O(n^2) time. Which partial products can you reuse between neighboring positions?
- Can you use only O(1) extra memory, not counting the returned array?
- With division allowed, how would you handle one zero in the input, and two or more zeros?

## Hints

### Hint 1

`answer[i]` splits into two parts: the product of everything to the left of `i`, and the product of everything to the right of `i`.

### Hint 2

The product of everything left of `i + 1` is the product of everything left of `i`, times `nums[i]`. One pass from the left computes all the left products; one pass from the right computes all the right products.

### Hint 3

Store the left products directly in the output array. On the pass from the right, keep the right product in a single variable and multiply it into each position.
