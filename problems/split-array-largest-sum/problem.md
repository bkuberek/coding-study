# Split Array Largest Sum

## Statement

You are given an array `nums` of non-negative integers and a number `k`. Cut `nums` into exactly `k` pieces, where each piece is a non-empty run of consecutive elements and every element belongs to exactly one piece. The order of the elements does not change.

The cost of a cut is the largest sum among its pieces. Return the smallest cost any cut into `k` pieces can achieve.

Think of `nums` as a row of jobs with given durations and `k` workers who each take a consecutive stretch of the row: you want the busiest worker to finish as early as possible.

Reference: this is our own wording of LeetCode problem 410, [Split Array Largest Sum](https://leetcode.com/problems/split-array-largest-sum/).

## Input

- `nums`: the non-negative integers to cut, in order
- `k`: the exact number of pieces

## Output

The minimum, over all ways to cut `nums` into `k` non-empty consecutive pieces, of the largest piece sum.

## Examples

### Example 1

<!-- case: ex1 -->

The four possible cuts into two pieces have piece sums `6 | 18`, `8 | 16`, `17 | 7` and `21 | 3`. Their costs are 18, 16, 17 and 21, so the best cut is `[6, 2] | [9, 4, 3]` with cost 16.

### Example 2

<!-- case: ex2 -->

A cost of 8 is impossible: the pieces would have to be `[7, 1]`, `[1, 7]`, `[1, 1]` and `[7]`, one too many. A cost of 9 works, for instance with `[7, 1, 1] | [7, 1, 1] | [7]`.

## Constraints

- `1 <= nums.length <= 1000`
- `0 <= nums[i] <= 10^6`
- `1 <= k <= min(50, nums.length)`

## Follow-ups

- If someone proposes a cost limit, how quickly can you tell whether `k` pieces can respect it?
- Does a cost that works stay possible for every larger cost? What does that let you do?
- How would you also return where to cut?

## Hints

### Hint 1

A dynamic program over "the best cost for the first `i` elements cut into `j` pieces" solves it in polynomial time. Can you do better?

### Hint 2

Turn the question around: given a limit `L`, can `nums` be cut into at most `k` pieces whose sums are all at most `L`? A single left-to-right pass answers that.

### Hint 3

Greedily extend the current piece while its sum stays within `L`, and start a new piece only when it would not. That uses the fewest pieces possible for `L`.

### Hint 4

The answer lies between `max(nums)` and `sum(nums)`, and feasibility only improves as `L` grows. Binary search the smallest feasible `L`.
