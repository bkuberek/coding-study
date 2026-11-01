# Pair Sums

## Statement

You get an integer array `nums`. Return the sum of every two neighbouring values, from left to right.

## Input

- `nums`: the integers to add up

## Output

An array with `nums.length - 1` sums, or an empty array when `nums` holds fewer than two values.

## Examples

### Example 1

<!-- case: ex1 -->

The neighbours are 1 and 2, then 2 and 3, then 3 and 4.

### Example 2

<!-- case: ex2 -->

One value has no neighbour.

## Constraints

- `0 <= nums.length <= 10^5`

## Hints

### Hint 1

Which values does each sum use?

### Hint 2

Slide a window of two over the array.
