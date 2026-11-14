# Sliding Window Maximum

## Statement

You get an integer array `nums` and a window width `k`. A window of width `k` starts at position 0 and moves one position to the right at a time until its right edge reaches the last element, so there are `nums.length - k + 1` windows.

Return the largest value inside each window, in the order the windows occur.

Reference: this is our own wording of LeetCode problem 239, [Sliding Window Maximum](https://leetcode.com/problems/sliding-window-maximum/).

## Input

- `nums`: the values
- `k`: the width of every window

## Output

An array of `nums.length - k + 1` values, where entry `i` is the maximum of `nums[i .. i + k - 1]`.

## Examples

### Example 1

<!-- case: ex1 -->

The windows are `[4, -2, 5]`, `[-2, 5, 3]`, `[5, 3, 1]`, `[3, 1, 6]` and `[1, 6, 0]`. The 5 stays the maximum for three windows; once it leaves, the 6 takes over.

### Example 2

<!-- case: ex2 -->

With falling values, the first element of each window is its maximum: 8 for `[8, 6]` and 6 for `[6, 4]`.

## Constraints

- `1 <= nums.length <= 10^5`
- `-10^4 <= nums[i] <= 10^4`
- `1 <= k <= nums.length`

## Follow-ups

- Scanning each window costs O(k). Can a heap bring the total down to O(n log n)?
- Can you reach O(n) by keeping only the elements that could still become a maximum?
- How would you compute the minimum of every window at the same time?

## Hints

### Hint 1

Consecutive windows share `k - 1` elements. Which structure tells you the largest of a changing set of values quickly?

### Hint 2

An element that has a larger element to its right, inside the window, can never be the maximum of this or any later window. You can forget it.

### Hint 3

Keep the positions of the remaining candidates in a double-ended queue, with values decreasing from front to back. Push new positions at the back after removing smaller values, drop the front when it leaves the window, and read the maximum at the front.
