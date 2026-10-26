# Longest Consecutive Run

## Statement

You get an unsorted integer array `nums`. A consecutive run is a set of values `x, x + 1, x + 2, ..., x + L - 1` that all occur somewhere in `nums`, in any positions and any order. Its length is `L`, the number of distinct values it covers.

Return the length of the longest consecutive run. Repeated values count once: a run is about which values are present, not how often. An empty array has no run, so its answer is 0.

Reference: this is our own wording of LeetCode problem 128, [Longest Consecutive Sequence](https://leetcode.com/problems/longest-consecutive-sequence/).

## Input

- `nums`: the integers to inspect, in no particular order; may be empty and may contain repeats

## Output

The number of values in the longest run of consecutive integers that all occur in `nums`, or 0 when `nums` is empty.

## Examples

### Example 1

<!-- case: ex1 -->

The values 2, 3, 4 and 5 all occur, scattered through the array, which gives a run of length 4. The values 12, 13 and 14 form a shorter run of length 3, and 30 stands alone.

### Example 2

<!-- case: ex2 -->

The value 8 occurs twice, but repeats do not lengthen a run: 8 and 9 give length 2. The value 6 cannot join them because 7 is missing.

## Constraints

- `0 <= nums.length <= 10^5`
- `-10^9 <= nums[i] <= 10^9`

## Follow-ups

- Sorting solves it in O(n log n). Can you solve it in O(n) time?
- How would you also return the run itself, for example as its first and last value?
- If values arrive one at a time, how would you keep the longest run up to date after every arrival?

## Hints

### Hint 1

After sorting, a run is a stretch of values that increase by exactly 1 at each step. What should happen when two neighbors are equal?

### Hint 2

Without sorting, you need to answer "is the value `x + 1` present?" quickly. Which structure does that in O(1)?

### Hint 3

Counting a run from every one of its values repeats work. Only start counting at a value `x` whose predecessor `x - 1` is absent.
