# Course Schedule II

## Statement

There are `numCourses` courses, numbered from `0` to `numCourses - 1`. A pair `[course, before]` in `prerequisites` means that `before` must be completed before `course` can be taken.

Return an order in which to take all the courses that respects every pair. If no such order exists, return an empty array.

Reference: this is our own wording of LeetCode problem 210, [Course Schedule II](https://leetcode.com/problems/course-schedule-ii/).

## Input

- `numCourses`: the number of courses
- `prerequisites`: the `[course, before]` pairs

## Output

Any order of all the courses that respects every pair, listing each course exactly once, or `[]` when no such order exists. Any valid order is accepted.

## Examples

### Example 1

<!-- case: ex1 -->

Course 2 needs both 0 and 1, which need nothing, so 0 and 1 come first in either order and 2 comes last. `[1, 0, 2]` is accepted as well.

### Example 2

<!-- case: ex2 -->

Course 0 needs 1, course 1 needs 2 and course 2 needs 0, so each one waits on another in a circle and no order exists.

## Constraints

- `1 <= numCourses <= 2000`
- `0 <= prerequisites.length <= 5000`
- `prerequisites[i].length == 2`
- `0 <= prerequisites[i][0], prerequisites[i][1] < numCourses`
- `prerequisites[i][0] != prerequisites[i][1]`
- All the pairs are distinct.

## Follow-ups

- Which courses could be taken in the same term? Group the order into levels.
- How would you report one cycle when there is no order?

## Hints

### Hint 1

Which courses can be taken first?

### Hint 2

Take a course whose prerequisites are all done, then lower the count of unfinished prerequisites of the courses it unlocks; a queue keeps the ready ones (Kahn's method). If some courses never become ready, there is a cycle.

### Hint 3

Alternatively, go depth-first and list a course after all its prerequisites are listed. Reaching a course that is still on the current path means a cycle.
