# Employee Importance

## Statement

A company describes its people as records. A record is a list `[id, importance, s1, s2, ...]`: the employee's id, their importance score, and the ids of their direct subordinates (none, one or several).

The total importance of an employee is their own importance plus the importance of everyone below them: their direct subordinates, those subordinates' subordinates, and so on. Given `employeeId`, return that employee's total importance.

Reference: this is our own wording of LeetCode problem 690, [Employee Importance](https://leetcode.com/problems/employee-importance/).

## Input

- `employees`: the records, in any order; a record may come before or after its leader's
- `employeeId`: the employee to total

## Output

The total importance of `employeeId` and everyone below them.

## Examples

### Example 1

<!-- case: ex1 -->

Employee 4 leads 7 and 9, and 9 leads 12, so the total is 6 + 2 + (-1) + 5 = 12.

### Example 2

<!-- case: ex2 -->

In the same company, employee 9's group is 9 and 12, so the total is -1 + 5 = 4. Employee 4 is above 9 and does not count.

## Constraints

- `1 <= employees.length <= 10^4`
- `employees[i].length >= 2`; `employees[i][0]` is the id and `employees[i][1]` the importance
- Ids are distinct and `1 <= id <= 10^5`
- `-100 <= importance <= 100`
- Every subordinate id is the id of a record, and every employee has at most one direct leader
- Nobody is above themselves, and at most 1000 leaders are above any employee
- `employeeId` is the id of a record

## Follow-ups

- How would you answer many queries on the same company quickly, for example the totals of every employee in one pass?

## Hints

### Hint 1

You will look up employees by id again and again. Which structure makes each lookup O(1)?

### Hint 2

From the queried employee, visit the whole group with a stack, a queue or recursion, adding up the importance.
