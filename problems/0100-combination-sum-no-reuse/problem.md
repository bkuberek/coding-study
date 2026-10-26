# Combination Sum Without Reuse

## Statement

You get an array `candidates` of positive integers, which may contain repeated values, and a positive integer `target`. Find every distinct combination of entries that adds up to exactly `target`, where each entry of the array can be used at most once. A value that appears twice in `candidates` can therefore appear up to twice in a combination.

Two combinations are the same when they contain every value the same number of times, no matter which positions the values were taken from. Report each distinct combination once.

Reference: this is our own wording of LeetCode problem 40, [Combination Sum II](https://leetcode.com/problems/combination-sum-ii/).

## Input

- `candidates`: the available entries, each usable at most once
- `target`: the sum every combination must reach

## Output

A list of all distinct combinations, each a list of values summing to `target`. The combinations may come in any order, and so may the values inside each one. Return an empty list when no combination exists.

## Examples

### Example 1

<!-- case: ex1 -->

Sorted, the entries are 1, 1, 2, 3, 4. Three distinct combinations reach 5: `1 + 4`, `2 + 3` and `1 + 1 + 3`. Taking the first 1 with the 4 or the second 1 with the 4 is the same combination, so it is listed once.

### Example 2

<!-- case: ex2 -->

There are three 6s, and any two of them reach 12. All such choices are the same combination.

## Constraints

- `1 <= candidates.length <= 15`
- `1 <= candidates[i] <= 30`
- `1 <= target <= 30`

## Follow-ups

- Can you avoid generating the same combination twice, rather than removing duplicates at the end?
- How does the rule for skipping repeated values differ from the one in Subsets With Duplicates, now that a target sum also prunes the search?

## Hints

### Hint 1

Sort the candidates. Equal values become neighbors, and every combination has a single sorted form.

### Hint 2

Build combinations by choosing the next entry from the positions after the last one used, so no entry is reused. Stop the loop as soon as an entry exceeds the remaining sum: all later ones are at least as large.

### Hint 3

At the same level of the recursion, choosing the second copy of a value after the first one has been tried rebuilds exactly the same combinations. Skip it; deeper levels can still take it.
