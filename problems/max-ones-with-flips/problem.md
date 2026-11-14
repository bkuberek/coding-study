# Max Consecutive Ones With K Flips

## Statement

You get an array `nums` that holds only `0`s and `1`s, and a budget `k`. You may turn at most `k` of the `0`s into `1`s. Return the length of the longest run of consecutive `1`s you can obtain.

Equivalently, find the longest contiguous subarray of `nums` that contains at most `k` zeros.

Reference: this is our own wording of LeetCode problem 1004, [Max Consecutive Ones III](https://leetcode.com/problems/max-consecutive-ones-iii/).

## Input

- `nums`: the bits, each `0` or `1`
- `k`: the largest number of zeros you may flip

## Output

The maximum length of a contiguous subarray with at most `k` zeros.

## Examples

### Example 1

<!-- case: ex1 -->

Flipping the zeros at positions 4 and 5 turns positions 2 to 8 into seven consecutive `1`s. No window of eight positions contains only two zeros.

### Example 2

<!-- case: ex2 -->

With no flips allowed, the answer is the longest existing run of `1`s, which is a single `1`.

## Constraints

- `1 <= nums.length <= 10^5`
- `nums[i]` is `0` or `1`.
- `0 <= k <= nums.length`

## Follow-ups

- Extending a run from every start is quadratic. Can you do it in one pass?
- Once you have found a window of length `L`, do you ever need to look at a shorter one again?
- What if the bits arrive as a stream that is too long to store?

## Hints

### Hint 1

Flipping zeros only helps inside the final run, so the question is about windows that contain at most `k` zeros.

### Hint 2

Slide a window over the array and count the zeros inside it. When the count exceeds `k`, move the left edge until it is back within budget.

### Hint 3

You can even keep the window from shrinking: when it has one zero too many, move both edges right by one. Its length then always equals the best answer so far.
