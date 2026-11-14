# Sorted Insertion Cost

## Statement

Insert the values of `instructions` one by one, from left to right, into a container that keeps its values sorted and starts out empty.

Inserting a value `x` costs the smaller of two counts, both taken just before the insertion: the number of values in the container that are strictly less than `x`, and the number that are strictly greater than `x`.

Return the total cost of all the insertions, modulo `10^9 + 7`.

Reference: this is our own wording of LeetCode problem 1649, [Create Sorted Array through Instructions](https://leetcode.com/problems/create-sorted-array-through-instructions/).

## Input

- `instructions`: the values, in insertion order

## Output

The total cost of the insertions, modulo `10^9 + 7`.

## Examples

### Example 1

<!-- case: ex1 -->

The values 3 and 8 cost nothing, because nothing is on one of their sides. When 5 arrives, one value is smaller (3) and one is larger (8), so it costs 1.

### Example 2

<!-- case: ex2 -->

The second 4 has nothing strictly smaller or strictly larger, so it costs 0. The 1 has nothing smaller and the 9 has nothing larger. The third 4 has 1 below and 9 above, which costs 1, and the 2 has one value below (the 1) and four above, which costs 1. The total is 2.

## Constraints

- `1 <= instructions.length <= 10^5`
- `1 <= instructions[i] <= 10^5`

## Follow-ups

- The values are at most 10^5. What would you do if they went up to 10^9? Think of coordinate compression.
- Can a merge sort count the same pairs?

## Hints

### Hint 1

For each new value you need two counts over the earlier values: how many are smaller and how many are larger.

### Hint 2

Counting by value turns both into prefix sums over an array `count[v]` of how many times each value was inserted.

### Hint 3

A Fenwick tree keeps those prefix sums under point updates, each in O(log m), where `m` is the largest value.
