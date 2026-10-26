# Burst Balloons

## Statement

A row of balloons floats in front of you; balloon `i` shows the number `nums[i]`. You burst all of them, one at a time, in any order you choose. Bursting a balloon earns the product of its number and the numbers of its current neighbors: the nearest balloons still intact on its left and on its right. Where a neighbor is missing (the balloon is at an end of what remains), use 1 instead.

Return the largest total number of coins you can earn by bursting every balloon.

Reference: this is our own wording of LeetCode problem 312, [Burst Balloons](https://leetcode.com/problems/burst-balloons/).

## Input

- `nums`: the numbers on the balloons, from left to right

## Output

The maximum total of coins over all bursting orders.

## Examples

### Example 1

<!-- case: ex1 -->

Burst the 2 first: it earns 4 * 2 * 5 = 40. Now 4 and 5 are neighbors; burst the 4 for 1 * 4 * 5 = 20, then the 5 for 1 * 5 * 1 = 5. The total of 65 is the best of the six orders.

### Example 2

<!-- case: ex2 -->

A single balloon has no neighbors, so it earns 1 * 7 * 1 = 7.

## Constraints

- `1 <= nums.length <= 300`
- `0 <= nums[i] <= 100`

## Follow-ups

- There are `n!` bursting orders. Why does splitting at the first balloon you burst not give independent subproblems?
- Which balloon of an interval should you decide on instead, so that the left and right parts no longer interact?
- In which order must the intervals be computed bottom-up?

## Hints

### Hint 1

Think about the balloon that is burst last in a range. While the others in the range are being burst, it separates them into a left part and a right part that never touch each other.

### Hint 2

Pad the row with a virtual balloon of value 1 at each end. Let `B(l, r)` be the most coins from bursting all balloons strictly between `l` and `r` while `l` and `r` stay. If `k` goes last, it earns `v[l] * v[k] * v[r]`.

### Hint 3

`B(l, r) = max over l < k < r of B(l, k) + v[l] * v[k] * v[r] + B(k, r)`. Compute short intervals before long ones.
