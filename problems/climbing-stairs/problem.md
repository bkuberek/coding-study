# Climbing Stairs

## Statement

A staircase has `n` steps and you start on the ground below the first one. Each move takes you up either one step or two steps. Count the distinct sequences of moves that end exactly on the top step.

Two sequences are different when they differ in at least one move, so going 1 then 2 is not the same as going 2 then 1.

Reference: this is our own wording of LeetCode problem 70, [Climbing Stairs](https://leetcode.com/problems/climbing-stairs/).

## Input

- `n`: the number of steps in the staircase

## Output

The number of different move sequences that reach step `n` from the ground.

## Examples

### Example 1

<!-- case: ex1 -->

With 4 steps the sequences are 1+1+1+1, 1+1+2, 1+2+1, 2+1+1 and 2+2: five in total.

### Example 2

<!-- case: ex2 -->

The last move onto step 6 starts from step 5 or from step 4. There are 8 ways to reach step 5 and 5 ways to reach step 4, so there are 8 + 5 = 13 ways to reach step 6.

## Constraints

- `1 <= n <= 45`
- The answer fits in a 32-bit signed integer.

## Follow-ups

- The plain recursion "ways(n) = ways(n - 1) + ways(n - 2)" takes exponential time. Which repeated work makes it slow, and how do you avoid it?
- Can you compute the answer with only a constant amount of extra memory?
- How would the recurrence change if a move could cover 1, 2 or 3 steps?

## Hints

### Hint 1

Think about the very last move. Where can you stand just before you land on step `n`?

### Hint 2

The ways to reach step `n` are the ways to reach step `n - 1` plus the ways to reach step `n - 2`. Store each count once instead of recomputing it.

### Hint 3

Each count depends only on the two counts just below it, so two variables are enough.
