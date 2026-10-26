# Three Sum

## Statement

You get an integer array `nums`. Find every triple of values that can be taken from three different positions of `nums` and that adds up to exactly zero.

Report each triple of values once. Two triples count as the same when they hold the same three values, whatever positions they came from and in whatever order you list them: `[-1, 0, 1]` and `[1, -1, 0]` are one triple. A value may appear more than once in a triple only if it appears at least that many times in `nums`.

Reference: this is our own wording of LeetCode problem 15, [3Sum](https://leetcode.com/problems/3sum/).

## Input

- `nums`: the values to combine

## Output

A list of triples `[a, b, c]` with `a + b + c == 0`, one per distinct multiset of values. The triples may come in any order, and the three values inside a triple may come in any order. Return an empty list when no triple exists.

## Examples

### Example 1

<!-- case: ex1 -->

Three triples reach zero: -5 + 0 + 5, -5 + 2 + 3 and -2 + 0 + 2. The value -5 takes part in two of them, which is allowed because they are different triples.

### Example 2

<!-- case: ex2 -->

The values 4, 4 and -8 can be picked from several sets of positions, but they form one triple of values, so it is reported once.

### Example 3

<!-- case: ex3 -->

The only triple of positions gives 1 + 2 - 4 = -1, so the answer is empty.

## Constraints

- `3 <= nums.length <= 3000`
- `-10^5 <= nums[i] <= 10^5`

## Follow-ups

- Checking every triple is cubic. Can you reach O(n^2)?
- Can you avoid duplicate triples without storing the triples found so far in a set?
- How would you count the triples with a sum below a target instead of listing those equal to zero?

## Hints

### Hint 1

Fix the first value of a triple. What problem is left for the other two values?

### Hint 2

Sorting the array costs only O(n log n) and makes two things easier: finding a pair with a given sum, and skipping values you have already used as the first, second or third element.

### Hint 3

In a sorted array, a pair with a given sum can be found by one index moving right from the start and one moving left from the end: if the sum is too small, move the left index; if it is too large, move the right one.
