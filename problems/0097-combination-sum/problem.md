# Combination Sum

## Statement

You get an array `candidates` of distinct positive integers and a positive integer `target`. Find every combination of candidates whose values add up to exactly `target`. A candidate may be used any number of times in the same combination, including not at all.

Two combinations count as the same when they use every value the same number of times, so `[2, 2, 3]` and `[3, 2, 2]` are one combination and must be reported once.

Reference: this is our own wording of LeetCode problem 39, [Combination Sum](https://leetcode.com/problems/combination-sum/).

## Input

- `candidates`: the distinct values available, each usable without limit
- `target`: the sum every combination must reach

## Output

A list of all distinct combinations, each a list of values summing to `target`. The combinations may come in any order, and so may the values inside each one. Return an empty list when no combination exists.

## Examples

### Example 1

<!-- case: ex1 -->

`3 + 3 + 4` and `3 + 7` both reach 10. No combination uses 4 twice, because 10 - 8 = 2 cannot be made from the candidates.

### Example 2

<!-- case: ex2 -->

The only way to reach 9 with 2s and 5s uses two 2s and one 5: an odd total needs an odd number of 5s, and two 5s already exceed 9.

## Constraints

- `1 <= candidates.length <= 30`
- `2 <= candidates[i] <= 40`
- All values in `candidates` are distinct.
- `1 <= target <= 40`
- The inputs are chosen so that the answer holds at most 150 combinations.

## Follow-ups

- Sorting the candidates lets you stop a loop early. At which point exactly can you stop?
- How do you avoid listing `[2, 3]` and `[3, 2]` as two answers without deduplicating at the end?
- If you only needed the number of combinations, could you avoid listing them? (Think of filling a table of ways per sum.)

## Hints

### Hint 1

Fix an order on the candidates and only ever add values in that order: a combination then has exactly one way of being built, so duplicates never arise.

### Hint 2

At each step you either use the current candidate once more (staying on it, since it may repeat) or move on to the next candidate for good.

### Hint 3

With the candidates sorted ascending, once a candidate exceeds the remaining sum, every later candidate does too, so the loop can stop there.
