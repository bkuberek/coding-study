# Subsets

## Statement

You get an array `nums` of distinct integers. Build its power set: every collection you can form by keeping some of the values and dropping the rest, including keeping none of them and keeping all of them.

Each subset must appear exactly once. Neither the order of the subsets nor the order of the values inside a subset matters.

Reference: this is our own wording of LeetCode problem 78, [Subsets](https://leetcode.com/problems/subsets/).

## Input

- `nums`: the distinct values to choose from

## Output

A list holding every subset of `nums` exactly once, as lists of values. The subsets may come in any order, and so may the values inside each subset.

## Examples

### Example 1

<!-- case: ex1 -->

Three values give 2^3 = 8 subsets: the empty one, three singletons, three pairs and the full set.

### Example 2

<!-- case: ex2 -->

A single value has two subsets: the empty subset and the value on its own.

## Constraints

- `1 <= nums.length <= 10`
- `-10 <= nums[i] <= 10`
- All values in `nums` are distinct.

## Follow-ups

- Every value is either in a subset or out of it. How does that two-way choice map onto the bits of a counter?
- Can you produce the subsets without recursion, growing the answer one value at a time?
- What changes when `nums` may contain repeated values and duplicate subsets must not appear? (See Subsets With Duplicates.)

## Hints

### Hint 1

There are exactly 2^n subsets, so any correct answer takes at least that long. Focus on generating each one once rather than on speed.

### Hint 2

Walk through the values in order. For each one, branch twice: once with the value added to the current subset and once without it. A complete path through all n values is one subset.

### Hint 3

The integers from 0 to 2^n - 1 written in binary list every in-or-out pattern exactly once: bit `i` says whether `nums[i]` is in.
