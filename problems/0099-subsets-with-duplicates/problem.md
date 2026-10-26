# Subsets With Duplicates

## Statement

You get an array `nums` of integers that may contain repeated values. List every distinct sub-collection of its values: choose, for each value, how many of its copies to keep, from none up to all of them.

Two subsets are the same when they contain every value the same number of times, regardless of which copies or which positions they came from. So with `nums = [4, 4]` there are exactly three subsets, `[]`, `[4]` and `[4, 4]`, and each must appear once.

Reference: this is our own wording of LeetCode problem 90, [Subsets II](https://leetcode.com/problems/subsets-ii/).

## Input

- `nums`: the values to choose from, possibly with repeats

## Output

A list holding every distinct subset exactly once. The subsets may come in any order, and so may the values inside each subset.

## Examples

### Example 1

<!-- case: ex1 -->

The two 3s are interchangeable, so choosing either one alone gives the same subset `[3]`. The distinct subsets are `[]`, `[1]`, `[3]`, `[1, 3]`, `[3, 3]` and `[1, 3, 3]`.

### Example 2

<!-- case: ex2 -->

Only how many zeros you keep matters: none, one or both.

## Constraints

- `1 <= nums.length <= 10`
- `-10 <= nums[i] <= 10`

## Follow-ups

- Can you avoid generating a duplicate at all, instead of generating it and discarding it later?
- If a value occurs `k` times, how many choices does it contribute? What does that say about the size of the answer?

## Hints

### Hint 1

Sorting puts equal values next to each other, so a subset can be written in one canonical sorted form.

### Hint 2

Build subsets by picking the next value from the positions after the last one used. At one level of that recursion, picking the first copy of a value and picking the second copy lead to identical subtrees.

### Hint 3

So at each level, skip a value that equals the previous value considered at the same level. Deeper levels may still take the next copy.
