# Course Schedule

## Statement

A program offers `numCourses` courses, numbered from `0` to `numCourses - 1`. Some courses have prerequisites: a pair `[course, required]` in `prerequisites` means you must have completed `required` before you can take `course`. You take one course at a time and may take a course as soon as all of its prerequisites are complete.

Decide whether you can complete every course.

Reference: this is our own wording of LeetCode problem 207, [Course Schedule](https://leetcode.com/problems/course-schedule/).

## Input

- `numCourses`: the number of courses
- `prerequisites`: pairs `[course, required]`, each meaning `required` must come before `course`

## Output

`true` if some order of the courses respects every prerequisite, otherwise `false`.

## Examples

### Example 1

<!-- case: ex1 -->

Course 0 has no prerequisites. Take it first; that unlocks courses 1 and 2, and course 2 unlocks course 3. One valid order is 0, 1, 2, 3.

### Example 2

<!-- case: ex2 -->

Course 0 needs course 1, course 1 needs course 2, and course 2 needs course 0. None of the three can ever be taken first.

## Constraints

- `1 <= numCourses <= 2000`
- `0 <= prerequisites.length <= 5000`
- `prerequisites[i].length == 2`
- `0 <= course, required < numCourses` and `course != required`
- No pair appears twice.

## Follow-ups

- Can you also produce one valid order of the courses? (See Parallel Courses for the number of rounds it takes when courses can run side by side.)
- How does depth-first search notice that a prerequisite chain loops back on itself?

## Hints

### Hint 1

Draw an arrow from each required course to the course that needs it. Every course can be completed exactly when these arrows contain no cycle.

### Hint 2

A course with no unfinished prerequisites can always be taken now. Taking it may free other courses. If you get stuck before taking everything, the remaining courses wait on each other in a cycle.

### Hint 3

Count, for each course, the prerequisites it still waits for. Start a queue with the courses whose count is 0; each time you take one, decrement the counts of the courses it unlocks and enqueue those that reach 0. All courses can be taken exactly when the queue processes all of them.
