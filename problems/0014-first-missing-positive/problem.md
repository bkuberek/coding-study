# First Missing Positive

## Statement

You get an unsorted integer array `nums`. Find the smallest positive integer (1, 2, 3, ...) that does not occur in it. Zero and negative numbers are never the answer, and they do not need to be present for anything.

The challenge is to do this in time linear in the length of the array while using only a constant amount of extra memory. You may rearrange or overwrite `nums` in place.

Reference: this is our own wording of LeetCode problem 41, [First Missing Positive](https://leetcode.com/problems/first-missing-positive/).

## Input

- `nums`: the integers to inspect, in any order; may contain zeros, negative values, values larger than its length, and repeats

## Output

The smallest integer `x >= 1` that does not occur in `nums`.

## Examples

### Example 1

<!-- case: ex1 -->

The values 1 and 2 are present, 3 is not, so the answer is 3. The 4 does not matter, and neither does the 0.

### Example 2

<!-- case: ex2 -->

Every integer from 1 to 3 is present, and the array has only three positions, so the first gap is right after them: 4.

## Constraints

- `1 <= nums.length <= 10^5`
- `-2^31 <= nums[i] <= 2^31 - 1`

## Follow-ups

- Why is the answer always between 1 and `n + 1`, where `n` is the length of the array?
- A hash set gives O(n) time with O(n) memory. Can you use the array itself as the hash table?
- What changes if you are not allowed to modify `nums`?

## Hints

### Hint 1

An array of length `n` can hold at most `n` distinct positive values. Which range must the answer fall in?

### Hint 2

Only the values from 1 to `n` can affect the answer. Everything else can be ignored.

### Hint 3

Try to move every value `v` with `1 <= v <= n` to index `v - 1`. Afterwards, the first index `i` that does not hold `i + 1` gives the answer.

### Hint 4

Each swap puts at least one value into its final position, so the total number of swaps is at most `n`, even though the loop looks nested.
