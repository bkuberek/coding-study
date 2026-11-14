# Fruit Into Baskets

## Statement

An orchard has a single row of trees, and tree `i` grows fruit of type `fruits[i]`. You carry two baskets. Each basket holds as much fruit as you like, but only of one type, and you cannot change a basket's type once it holds fruit.

Pick any tree to start at. From there you walk to the right, picking exactly one fruit from every tree you pass, including the first. You must stop at the first tree whose fruit fits in neither basket (or at the end of the row). Return the largest number of fruits you can collect.

Put differently: find the longest contiguous run of `fruits` that contains at most two distinct values.

Reference: this is our own wording of LeetCode problem 904, [Fruit Into Baskets](https://leetcode.com/problems/fruit-into-baskets/).

## Input

- `fruits`: the fruit type of each tree, from left to right

## Output

The maximum number of fruits you can pick, which is the length of the longest contiguous subarray with at most two distinct values.

## Examples

### Example 1

<!-- case: ex1 -->

Start at position 2 and collect `2, 1, 1, 2, 1`: only types 1 and 2, five fruits. Starting at position 0 gives only `2, 0, 2` before the type 1 tree stops you.

### Example 2

<!-- case: ex2 -->

Every tree grows a different type, so any walk ends after two trees.

## Constraints

- `1 <= fruits.length <= 10^5`
- `0 <= fruits[i] < fruits.length`

## Follow-ups

- Walking from every start is quadratic. Can you do it in one pass?
- With exactly two baskets, do you even need a map of counts?
- How would you solve it with `k` baskets?

## Hints

### Hint 1

The story is a wrapper: you need the longest contiguous run with at most two distinct values.

### Hint 2

Keep a window and a count of each type inside it. When a third type enters, drop trees from the left until only two types remain.

### Hint 3

For exactly two types, it is enough to remember the last type seen, the type before it, and how long the final run of the last type is: a new third type starts a window at the beginning of that run.
