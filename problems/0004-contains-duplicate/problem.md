# Contains Duplicate

## Statement

You get an integer array `nums`. Decide whether some value occurs in it more than once.

Return `true` as soon as any value appears at two or more positions, and `false` when every position holds a different value. The positions of the repeated value do not matter, and neither does how many times it repeats.

Reference: this is our own wording of LeetCode problem 217, [Contains Duplicate](https://leetcode.com/problems/contains-duplicate/).

## Input

- `nums`: the integers to inspect, in the order given

## Output

`true` if at least one value occurs two or more times in `nums`, otherwise `false`.

## Examples

### Example 1

<!-- case: ex1 -->

The value 8 sits at positions 1 and 3, so the array contains a duplicate. The other values each appear once, which does not change the answer.

### Example 2

<!-- case: ex2 -->

All four values are different. Note that -2 and 2 would be different values; only equal values count as duplicates.

## Constraints

- `1 <= nums.length <= 10^5`
- `-10^9 <= nums[i] <= 10^9`

## Follow-ups

- Comparing every pair of positions is quadratic. Can you answer in O(n log n) time? In O(n)?
- If you may not use more than O(1) extra memory and may not modify `nums`, what is the best time you can achieve?
- How would you change the solution to report whether two equal values sit at most `k` positions apart?

## Hints

### Hint 1

A duplicate is a pair of positions holding equal values. What is the simplest way to look at every pair?

### Hint 2

If the values were sorted, where would equal values end up relative to each other?

### Hint 3

Walk the array once and remember every value you have already seen. Which structure tells you in constant time whether a value is in that collection?
