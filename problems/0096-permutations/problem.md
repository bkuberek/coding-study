# Permutations

## Statement

You get an array `nums` of distinct integers. List every way to arrange all of its values in a row: every ordering that uses each value exactly once.

Each ordering must appear exactly once. The orderings themselves may be listed in any sequence, but the order of the values inside one ordering is what distinguishes it, so it matters.

Reference: this is our own wording of LeetCode problem 46, [Permutations](https://leetcode.com/problems/permutations/).

## Input

- `nums`: the distinct values to arrange

## Output

A list of all `nums.length!` orderings of `nums`, each as a list of values. The list of orderings may come in any order.

## Examples

### Example 1

<!-- case: ex1 -->

Three distinct values can be arranged in 3! = 6 ways: three choices for the first slot, two for the second and one for the last.

### Example 2

<!-- case: ex2 -->

Two values give exactly two orderings: as given and reversed.

## Constraints

- `1 <= nums.length <= 6`
- `-10 <= nums[i] <= 10`
- All values in `nums` are distinct.

## Follow-ups

- Can you build the orderings by swapping values inside the input array instead of keeping a separate "used" marker?
- How would you skip duplicate orderings if `nums` could contain repeated values?
- How would you produce only the next ordering in lexicographic order, without listing all of them?

## Hints

### Hint 1

Fill the slots from left to right. For the first slot you can pick any of the n values; for the next, any value not picked yet.

### Hint 2

Keep a boolean per value that says whether it is already in the ordering you are building. Set it before going one level deeper and clear it when you come back.

### Hint 3

Alternatively, treat `nums[0..i-1]` as the fixed prefix: swap each candidate from positions `i..n-1` into position `i`, recurse on `i + 1`, then swap it back.
