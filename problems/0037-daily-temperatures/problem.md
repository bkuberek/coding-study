# Daily Temperatures

## Statement

A weather log holds one temperature reading per day, in order: `temperatures[i]` is the reading of day `i`. For every day, work out how long you would have to wait after it until a day that is strictly warmer arrives.

Return an array `waits` of the same length, where `waits[i]` is the number of days from day `i` to the first later day whose temperature is strictly higher than `temperatures[i]`. When no later day is warmer, `waits[i]` is 0.

Reference: this is our own wording of LeetCode problem 739, [Daily Temperatures](https://leetcode.com/problems/daily-temperatures/).

## Input

- `temperatures`: the daily readings in degrees, oldest first

## Output

An array of the same length as `temperatures`: for each day, how many days later the next strictly warmer day comes, or 0 when none does.

## Examples

### Example 1

<!-- case: ex1 -->

Day 0 (12 degrees) is followed at once by a warmer day, so its wait is 1. Day 2 (10 degrees) waits until day 5 (14 degrees), 3 days later: day 4 repeats 10 degrees, which is not warmer. Day 5 holds the highest reading of the log, so nothing later is warmer and its wait is 0; the last day gets 0 as well.

### Example 2

<!-- case: ex2 -->

Equal readings do not count as warmer. Each of the three days at -3 waits for day 3, which is the first day above -3.

## Constraints

- `1 <= temperatures.length <= 10^5`
- `-50 <= temperatures[i] <= 50`

## Follow-ups

- Checking every later day for each day costs O(n^2) in a long cold spell. Can you answer every day in one pass?
- Can you solve it scanning from the last day to the first instead?
- How would you report, for each day, the most recent earlier day that was warmer?

## Hints

### Hint 1

A day that is still waiting for a warmer day can be answered by the first later reading that beats it. Which days are still waiting when you reach day `i`?

### Hint 2

The waiting days, from the oldest to the newest, never get warmer: a newer day that was warmer would already have answered an older, colder one.

### Hint 3

Keep the waiting days on a stack. Each new reading pops and answers every waiting day colder than itself, then waits on top of the stack.
