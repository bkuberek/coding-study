# Course Schedule II: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| repeated-scan | brute | O(V * (V + E)) | O(V + E) | the graph is tiny, or as a correctness oracle |
| kahn | optimal | O(V + E) | O(V + E) | default answer, or when levels (terms) matter |
| dfs-postorder | optimal | O(V + E) | O(V + E) | a stack-based or recursive search fits better, or a cycle must be reported |

Several orders can be valid, so the tests use a checker: any order that lists each course once with every prerequisite first is accepted, and `[]` is accepted only when a cycle exists.

## Approach: repeated-scan (Repeatedly take the first course whose prerequisites are all done)

### Intuition

A course can be taken once all its prerequisites are taken. So keep taking one such course, any one, until all courses are taken or none is available.

### Algorithm

1. Build the list of prerequisites of each course.
2. Repeat `V` times: scan the courses in number order for the first untaken course whose prerequisites are all taken. Take it and append it to the order.
3. If a scan finds no such course, return `[]`.
4. Return the order.

### Correctness

Each course is appended only when all its prerequisites are already in the order, so the order respects every pair. A scan that finds nothing means every remaining course waits for another remaining course. Following those waits from any remaining course must eventually repeat a course, which is a cycle, and then no order exists.

### Complexity

- Time: O(V * (V + E)) — up to `V` rounds, and each round looks at every course and at their prerequisite lists.
- Space: O(V + E) — the prerequisite lists, the taken flags and the order.

### Trade-offs

Very simple and a faithful oracle, but quadratic: with long prerequisite chains only one course is free at a time, so each of the `V` rounds scans most of the courses. Kahn's method avoids the repeated scans by remembering which courses become ready.

### Pitfalls and edge cases

- Return `[]`, not the partial order, when a scan finds nothing.
- Courses with no prerequisites at all are valid in any position.

### Language notes

- Python: a `for ... else` returns `[]` when the inner scan never breaks.
- TypeScript: `findIndex` with an `every` check scans for the next course.
- Java: a helper `allTaken` checks a prerequisite list; the result is an `int[]` (`new int[0]` when there is no order).
- Kotlin: `firstOrNull { ... } ?: return IntArray(0)` returns early when nothing is available.

## Approach: kahn (Queue the courses whose remaining prerequisite count drops to zero)

### Intuition

Count how many prerequisites each course still waits for. Courses at zero can be taken right away. Taking one lowers the count of every course it unlocks, and any course that reaches zero joins the queue.

### Algorithm

1. For each pair `[course, before]`, add `course` to the unlock list of `before` and increase the waiting count of `course`.
2. Queue every course whose count is zero.
3. Pop a course, append it to the order, and decrease the count of each course it unlocks; queue those that reach zero.
4. Return the order if it holds all `V` courses, otherwise `[]`.

### Correctness

A course is appended only after its count reached zero, which means all its prerequisites were appended before: the order is valid. Courses on a cycle, or behind one, never reach zero because some prerequisite on the cycle is never taken. So the order is short exactly when a cycle exists, and then the empty answer is right.

### Complexity

- Time: O(V + E) — each course is queued once and each pair is looked at once.
- Space: O(V + E) — the unlock lists, the counts, the queue and the order.

### Trade-offs

Iterative, with no recursion depth to worry about, and processing the queue by rounds gives the levels of the follow-up for free. The order depends on the queue discipline, which is why the problem accepts any valid order.

### Pitfalls and edge cases

- The edge direction is `before -> course`: taking `before` unlocks `course`.
- The queue starts with all zero-count courses, not just course 0.

### Language notes

- Python: `collections.deque` as the queue.
- TypeScript: an array with a head index is the queue, because `shift()` is O(n) per call.
- Java: `ArrayDeque<Integer>` and a `List<List<Integer>>` adjacency; the order is built in an `int[]` and `new int[0]` is returned when it is short.
- Kotlin: Kotlin's own `ArrayDeque<Int>` with `removeFirst`, and `IntArray(numCourses)` for the order.

## Approach: dfs-postorder (Depth-first search that lists a course after its prerequisites)

### Intuition

Walk from a course to its prerequisites and append the course only when all of them are already listed. That post-order is a valid schedule. Meeting a course that is still on the current path means the prerequisites loop back on themselves.

### Algorithm

1. Build the prerequisite list of each course and mark every course unseen.
2. For each unseen course, start a depth-first search with an explicit stack and a cursor per course. Mark a course active when it is pushed.
3. When the cursor of the course on top has passed its last prerequisite, pop it, mark it done and append it to the order.
4. For the next prerequisite: if it is active, return `[]` (a cycle); if it is unseen, mark it active and push it; if it is done, skip it.
5. Return the order.

### Correctness

A course is appended after the search has finished all its prerequisites, so each prerequisite is listed before it: post-order along the "requires" edges lists prerequisites first, and no reversal is needed. An edge to an active course closes a path that leads back to a course still being explored, which is a cycle. A done course is not a cycle: it was fully explored and its subtree is already in the order.

### Complexity

- Time: O(V + E) — each course is pushed once and each pair is followed once.
- Space: O(V + E) — the prerequisite lists, the state and cursor arrays, and the stack.

### Trade-offs

No separate counting pass and, because the edges point from a course to its prerequisites, no final reversal. Recursion would also work here (the depth is at most 2000), but the explicit stack avoids stack limits in general. It reports a cycle at the point of discovery, which is handy for the follow-up.

### Pitfalls and edge cases

- Distinguish active from done: treating every visited course as a cycle rejects a diamond of prerequisites.
- Mark the root active before pushing it, or a prerequisite chain that returns to the root is missed.

### Language notes

- Python: the stack holds `(course, next prerequisite index)` tuples.
- TypeScript, Java and Kotlin: a `cursor` array indexed by course replaces the tuple, which works because a course appears at most once on the stack.
- Java: `ArrayDeque<Integer>` used with `push`, `peek` and `pop`.
- Kotlin: Kotlin's `ArrayDeque` with `addLast`, `last` and `removeLast`.
