# Parallel Courses

## Statement

There are `n` courses, labelled from `1` to `n`. Each pair `[before, after]` in `relations` says that course `before` must be completed in an earlier semester than course `after`.

In one semester you may take any number of courses, as long as every prerequisite of each of them was completed in a previous semester. Return the smallest number of semesters needed to complete all `n` courses, or `-1` if it is impossible to complete them all.

Reference: this is our own wording of LeetCode problem 1136, [Parallel Courses](https://leetcode.com/problems/parallel-courses/).

## Input

- `n`: the number of courses, labelled `1` to `n`
- `relations`: pairs `[before, after]`, each meaning `before` must be done in an earlier semester than `after`

## Output

The minimum number of semesters, or `-1` when the prerequisites form a cycle.

## Examples

### Example 1

<!-- case: ex1 -->

Course 1 comes first. Courses 2 and 3 both depend only on it, so they share the second semester. Course 4 needs 3 and course 5 needs both 2 and 4, so the plan is {1}, {2, 3}, {4}, {5}: four semesters. No plan is shorter, because the chain 1, 3, 4, 5 needs a separate semester for each course.

### Example 2

<!-- case: ex2 -->

Each of the three courses waits for another one in a loop, so none of them can ever be taken.

## Constraints

- `1 <= n <= 3000`
- `0 <= relations.length <= 5000`
- `relations[i].length == 2`
- `1 <= before, after <= n` and `before != after`
- No pair appears twice.

## Follow-ups

- Why is taking every available course as early as possible always optimal here?
- How does the answer relate to the longest chain of prerequisites?
- What changes if at most `k` courses fit into one semester? (That variant is much harder.)

## Hints

### Hint 1

Nothing limits how many courses you take at once, so there is no reason to postpone a course: take every course whose prerequisites are done.

### Hint 2

Run the queue-based topological sort one level at a time: the courses with no prerequisites form semester 1, the courses they free form semester 2, and so on. Count the levels.

### Hint 3

If some courses are never freed, they wait on a cycle and the answer is `-1`. Equivalently, the answer is the number of courses on the longest prerequisite chain, when no cycle exists.
