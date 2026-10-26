# Candy Distribution

## Statement

Children stand in a line, and `ratings[i]` is the score of child `i`. You hand out candies under two rules:

- every child gets at least one candy;
- a child with a strictly higher score than a neighbor (the child directly to the left or right) gets strictly more candies than that neighbor.

Neighbors with equal scores have no constraint between them. Return the smallest total number of candies that satisfies both rules.

Reference: this is our own wording of LeetCode problem 135, [Candy](https://leetcode.com/problems/candy/).

## Input

- `ratings`: the score of each child, in line order

## Output

The minimum total number of candies.

## Examples

### Example 1

<!-- case: ex1 -->

The middle child outscores both neighbors, so the line gets 1, 2, 1 candies: 4 in total.

### Example 2

<!-- case: ex2 -->

All scores are equal, so no child needs more than a neighbor, and one candy each is enough.

### Example 3

<!-- case: ex3 -->

Scores rise to a peak and fall again: 1, 2, 3, 2, 1 candies, 9 in total. The peak needs 3 because of its left side; its right side alone would require only 3 as well.

## Constraints

- `1 <= ratings.length <= 2 * 10^4`
- `0 <= ratings[i] <= 2 * 10^4`

## Follow-ups

- Fixing violations one at a time until nothing changes works, but how many rounds can it take?
- Can you satisfy the left neighbors in one pass and the right neighbors in another, and why does combining them with a maximum not break the first pass?
- Can you do it in one pass with O(1) extra memory?

## Hints

### Hint 1

Consider only the rule for left neighbors. One left-to-right pass gives the smallest counts that satisfy it.

### Hint 2

Do the same from right to left for right neighbors. Each child needs at least the larger of the two values.

### Hint 3

For one pass with constant memory, look at the line as rising and falling runs. A peak must be large enough for the longer of its two slopes.
