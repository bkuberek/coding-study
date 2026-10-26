# Subarray Sum Equals K

## Statement

You get an integer array `nums`, which may contain negative values and zeros, and an integer `k`. Count the subarrays whose values add up to exactly `k`.

A subarray is a non-empty run of consecutive positions `nums[i..j]` with `i <= j`. Two subarrays are different when they start or end at different positions, even if they hold the same values.

Reference: this is our own wording of LeetCode problem 560, [Subarray Sum Equals K](https://leetcode.com/problems/subarray-sum-equals-k/).

## Input

- `nums`: the array to search
- `k`: the required sum

## Output

The number of pairs `(i, j)` with `i <= j` and `nums[i] + ... + nums[j] == k`.

## Examples

### Example 1

<!-- case: ex1 -->

Three runs add up to 5: `[2, 3]` at positions 0 to 1, `[3, -1, 3]` at positions 1 to 3, and `[5]` at position 4.

### Example 2

<!-- case: ex2 -->

Zeros let several runs share one sum: `[4]`, `[0, 4]`, `[4, 0]` and `[0, 4, 0]` all add up to 4. They hold different positions, so each one counts.

## Constraints

- `1 <= nums.length <= 2 * 10^4`
- `-1000 <= nums[i] <= 1000`
- `-10^7 <= k <= 10^7`

## Follow-ups

- Trying every start and extending to the right is O(n^2). Can one pass with extra memory do it in O(n)?
- Why does a sliding window fail here, although it works when every value is positive?
- How would you return the longest such subarray instead of the count?

## Hints

### Hint 1

The sum of `nums[i..j]` is `prefix[j + 1] - prefix[i]`, where `prefix[t]` is the sum of the first `t` values.

### Hint 2

Fix the end `j`. You need the number of earlier prefixes equal to `prefix[j + 1] - k`.

### Hint 3

Walk the array once, keeping a hash map from prefix sum to how often it occurred so far. Seed it with the empty prefix: sum 0, seen once.
