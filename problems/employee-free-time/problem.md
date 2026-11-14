# Employee Free Time

## Statement

Each employee's working time is a list of intervals `[start, end]`, where an interval covers the times from `start` up to, but not including, `end`. Within one employee the intervals are sorted by start and separated by gaps.

Find the time during which nobody is working, between the earliest start and the latest end of all the intervals. The unbounded time before everything starts and after everything ends is not reported. Report it as maximal free spans: a span starts where the last busy interval before it ends and ends where the next busy interval starts. An interval ending at time `t` and another one starting at `t` leave no free time between them.

Reference: this is our own wording of LeetCode problem 759, [Employee Free Time](https://leetcode.com/problems/employee-free-time/).

## Input

- `schedule`: `schedule[i]` is the list of employee `i`'s working intervals, sorted by start; the employees come in any order

## Output

The free spans `[start, end]` with `start < end`, sorted by start; an empty list when there is none.

## Examples

### Example 1

<!-- case: ex1 -->

Somebody is working during `[2, 6)` (the first two employees overlap), during `[9, 11)` and during `[12, 15)`. The free spans are the two gaps between these: from 6 to 9 and from 11 to 12.

### Example 2

<!-- case: ex2 -->

Each shift starts exactly when the previous one ends, so from 1 to 10 somebody is always working and there is no free span.

## Constraints

- `1 <= schedule.length <= 1000`
- `1 <= schedule[i].length <= 100`
- At most `10^4` intervals in total
- `schedule[i][j].length == 2`
- `0 <= schedule[i][j][0] < schedule[i][j][1] <= 10^8`
- `schedule[i][j][1] < schedule[i][j + 1][0]` (each employee's intervals are sorted and separated)

## Follow-ups

- The flatten-and-sort answer ignores that every employee's list is already sorted. How can you use that to sort less?
- How would you report only the free spans that last at least `d` time units?

## Hints

### Hint 1

Which employee is working does not matter, only whether anyone is.

### Hint 2

Put all the intervals in one list sorted by start and walk it while remembering the latest end seen so far. A start beyond that end opens a free span.

### Hint 3

Each employee's list is already sorted. A min-heap holding each employee's next interval yields all the intervals in start order while keeping only one entry per employee.
