# Time to Inform All Employees

## Statement

A company has `n` employees with ids `0` to `n - 1`, and `headID` is the head of the company. `manager[i]` is the direct manager of employee `i`, and `manager[headID] == -1`.

The head learns some urgent news at minute 0. An employee who has heard the news needs `informTime[i]` minutes to tell all their direct reports. The reports all hear it at the end of those minutes and then pass it on the same way. Return the number of minutes until every employee has heard the news.

Reference: this is our own wording of LeetCode problem 1376, [Time Needed to Inform All Employees](https://leetcode.com/problems/time-needed-to-inform-all-employees/).

## Input

- `n`: the number of employees
- `headID`: the id of the head of the company
- `manager`: each employee's direct manager, with `-1` for the head
- `informTime`: the minutes each employee needs to inform their direct reports, 0 for employees without reports

## Output

The minute at which the last employee hears the news, which is 0 when the head is alone.

## Examples

### Example 1

<!-- case: ex1 -->

Head 3 needs 2 minutes to tell employees 0 and 1. Employee 1 then needs 4 more minutes to tell 2 and 4, who hear the news at minute 6. Employee 0 has no reports.

### Example 2

<!-- case: ex2 -->

The news moves down a single line: 3 minutes to reach employee 1, 5 more to reach employee 2 and 1 more to reach employee 3, so 9 minutes in total.

## Constraints

- `1 <= n <= 10^5`
- `0 <= headID < n`
- `manager.length == n` and `informTime.length == n`
- `manager[headID] == -1`; for every other employee `0 <= manager[i] < n`, and following managers from any employee reaches the head
- At most 2000 managers are above any employee
- `0 <= informTime[i] <= 1000`, and `informTime[i] == 0` when employee `i` has no direct reports

## Follow-ups

- Which employee hears the news last, and through which chain of managers?
- What changes if each report is told one at a time, each taking its own minutes?

## Hints

### Hint 1

The minute at which an employee hears the news is the sum of `informTime` over all the managers above them.

### Hint 2

Walking up from every employee repeats the same sums over and over. Go down from the head instead, carrying the elapsed time.

### Hint 3

Build each manager's list of direct reports first.
