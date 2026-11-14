# Partition Equal Subset Sum

## Statement

You get an array `nums` of positive integers. Decide whether its elements can be split into two groups with equal sums. Every element goes into exactly one of the two groups, and a group may hold any number of elements, but both groups must exist, so a single element can never be split.

Reference: this is our own wording of LeetCode problem 416, [Partition Equal Subset Sum](https://leetcode.com/problems/partition-equal-subset-sum/).

## Input

- `nums`: the positive integers to split

## Output

`true` if the elements can be divided into two groups whose sums are equal, otherwise `false`.

## Examples

### Example 1

<!-- case: ex1 -->

The total is 12. The groups 4 + 2 and 3 + 1 + 2 both sum to 6.

### Example 2

<!-- case: ex2 -->

The total 12 is even, but no group reaches 6: the possible group sums are 2, 3, 5, 7, 9, 10 and 12.

## Constraints

- `1 <= nums.length <= 200`
- `1 <= nums[i] <= 100`

## Follow-ups

- Trying all 2^n ways to split the array is far too slow for 200 elements. What single number does a split really depend on?
- Can you solve it with memory proportional to the target sum instead of the number of elements times the target?
- How would you report the two groups themselves?

## Hints

### Hint 1

If the total is odd, the answer is `false`. Otherwise you only need to find one group that sums to half of the total; the remaining elements form the other group.

### Hint 2

For each element, either it is in the group or it is not. Track which sums are reachable using the elements seen so far.

### Hint 3

A boolean array indexed by sum, from 0 to the target, is enough. Update it from the largest sum down so that each element is used at most once.
