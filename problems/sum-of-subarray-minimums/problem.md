# Sum of Subarray Minimums

## Statement

You get an array of positive integers `arr`. Look at every contiguous, non-empty subarray `arr[i..j]` (with `i <= j`), take the smallest value inside it, and add all those minimums together. An array of length `n` has `n * (n + 1) / 2` such subarrays, and each one counts once, even when two subarrays hold the same values.

The total can be large, so return it modulo `10^9 + 7`.

Reference: this is our own wording of LeetCode problem 907, [Sum of Subarray Minimums](https://leetcode.com/problems/sum-of-subarray-minimums/).

## Input

- `arr`: the array whose subarrays are summed

## Output

The sum of the minimums of all contiguous subarrays, modulo `10^9 + 7`.

## Examples

### Example 1

<!-- case: ex1 -->

The six subarrays are `[4]`, `[2]`, `[5]`, `[4, 2]`, `[2, 5]` and `[4, 2, 5]`, with minimums 4, 2, 5, 2, 2 and 2. Their sum is 17. The value 2 is the minimum of four of them.

### Example 2

<!-- case: ex2 -->

The two equal values at positions 0 and 1 are separate subarrays `[3]` and `[3]`, plus `[3, 3]`, each with minimum 3. Every subarray that reaches the last position has minimum 1. The total is 3 + 3 + 3 + 1 + 1 + 1 = 12.

## Constraints

- `1 <= arr.length <= 3 * 10^4`
- `1 <= arr[i] <= 3 * 10^4`

## Follow-ups

- Enumerating every subarray costs O(n^2). Can you instead count, for each element, how many subarrays it is the minimum of?
- When the same value appears several times, which copy should count as the minimum, so that no subarray is counted twice or skipped?
- How would you compute the sum of subarray maximums, or of maximum minus minimum?

## Hints

### Hint 1

`arr[i]` is the minimum of exactly the subarrays that contain position `i` and no smaller value. Their start lies between the previous smaller element and `i`; their end between `i` and the next smaller element.

### Hint 2

With `left` choices for the start and `right` choices for the end, `arr[i]` contributes `arr[i] * left * right`. A monotonic stack finds the previous and next smaller elements for every position in linear time.

### Hint 3

Break ties on one side only: stop at a strictly smaller value on the left but at a smaller or equal value on the right. Then each subarray with a repeated minimum is attributed to exactly one of the copies.
