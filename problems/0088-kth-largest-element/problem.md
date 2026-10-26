# Kth Largest Element

## Statement

You get an integer array `nums` and an integer `k`. Return the value that would sit at position `k` if the array were sorted from largest to smallest, counting from 1.

Equal values count separately: in `[5, 3, 5, 1, 5]`, the three 5s occupy ranks 1, 2 and 3, so the 3rd largest element is 5, not 1. You do not have to sort the array; you only need the one value at rank `k`.

Reference: this is our own wording of LeetCode problem 215, [Kth Largest Element in an Array](https://leetcode.com/problems/kth-largest-element-in-an-array/).

## Input

- `nums`: the values, in any order.
- `k`: the rank to report, where rank 1 is the largest value.

## Output

The `k`-th largest value of `nums`, counting duplicates.

## Examples

### Example 1

<!-- case: ex1 -->

From largest to smallest the values are 9, 7, 4, 2, 1, so rank 2 is 7.

### Example 2

<!-- case: ex2 -->

The order from largest to smallest is 5, 5, 5, 3, 1. The three copies of 5 take ranks 1 to 3.

## Constraints

- `1 <= k <= nums.length <= 10^5`
- `-10^4 <= nums[i] <= 10^4`

## Follow-ups

- Sorting takes O(n log n). Can you do better when `k` is small?
- Can you find the answer in O(n) time on average, without sorting?
- What input makes a naive quickselect quadratic, and how do you defend against it?

## Hints

### Hint 1

The `k` largest values are all you need. Can you keep just those while scanning the array once?

### Hint 2

A min-heap of size `k` holds the `k` largest values seen so far, with the smallest of them at the root. A new value either beats the root and replaces it, or is not among the `k` largest.

### Hint 3

Quicksort's partition step puts a pivot at its final sorted position. Afterwards you only need to continue in the one side that contains rank `k`. Pick the pivot at random, and group values equal to the pivot together so that repeated values cannot slow you down.
