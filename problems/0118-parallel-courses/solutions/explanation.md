# Parallel Courses: Explanation

## Overview

V is the number of courses and E the number of relations. With unlimited courses per semester, taking every available course as early as possible is optimal, so the answer is the number of courses on the longest prerequisite chain, or -1 when the relations contain a cycle.

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| semester-scan | brute | O(V * (V + E)) | O(V + E) | a direct simulation of the rules |
| kahn-levels | optimal | O(V + E) | O(V + E) | default answer: the topological sort, one level per semester |
| longest-chain-dfs | optimal | O(V + E) | O(V + E) | you think of it as a longest-path problem on a DAG |

## Approach: semester-scan (Each semester scan every course and take all that are free)

### Intuition

Play the semesters out. In each one, look at every course not taken yet and take it if all its prerequisites were finished in earlier semesters. If a semester frees nothing while courses remain, the remaining courses wait on each other forever.

### Algorithm

1. Build `required[course]` and an array `finishedIn`, 0 for courses not taken.
2. While some course is not taken:
   1. Start the next semester.
   2. Collect every untaken course whose prerequisites all have `0 < finishedIn < semester`.
   3. If the list is empty, return -1; otherwise record the semester for each course in it.
3. Return the number of semesters.

### Correctness

By induction on the semester `s`: the courses taken in semester `s` are exactly those whose longest prerequisite chain has `s` courses. A course with no prerequisites is taken in semester 1. A course whose prerequisites all finish by semester `s - 1`, and at least one exactly then, becomes free in semester `s` and not before. Postponing a course never helps, because taking it early only frees its dependants earlier, so this greedy schedule is optimal and its length is the longest chain. If a semester frees nothing, every remaining course has a remaining prerequisite, which forces a cycle among them, and no schedule exists.

### Complexity

- Time: O(V * (V + E)) — the number of semesters is at most V, and each one scans every course and its prerequisite list.
- Space: O(V + E) — the prerequisite lists and the semester array.

### Trade-offs

Follows the statement word for word and is easy to trust, which makes it the oracle. Long chains make it quadratic, because every semester rescans courses whose status could not have changed. The level-by-level topological sort visits each course and each relation only once.

### Pitfalls and edge cases

- Decide all of a semester's courses before marking any of them, or a course could be taken in the same semester as its prerequisite.
- Courses that appear in no relation are taken in semester 1.

### Language notes

- Python: `0 < finished_in[before] < semester` reads as a range check thanks to chained comparison.
- TypeScript: `every` is `true` for a course without prerequisites, which makes it free.
- Java: a small `finishedBefore` helper keeps the inner loop readable.
- Kotlin: `finishedIn[it] in 1 until current` is the range check; `current` is a `val` copy of the semester so the lambda does not capture a changing `var`.

## Approach: kahn-levels (Run the topological sort one level per semester)

### Intuition

Kahn's algorithm keeps, for every course, the number of prerequisites it still waits for. Process it in levels: the courses with a count of 0 are semester 1; taking them all decrements the counts of the courses they unlock, and those that reach 0 form semester 2; and so on. The number of levels is the answer, provided every course got taken.

### Algorithm

1. Build `unlocks[before]` and `waiting[after]` from the relations.
2. Let the first semester be every course with `waiting == 0`.
3. While the current semester is not empty: count it, and for each of its courses decrement `waiting` of every course it unlocks; those that reach 0 form the next semester.
4. Return the number of semesters if all V courses were taken, else -1.

### Correctness

A course reaches a count of 0 exactly in the level after its last prerequisite was taken, so it is taken in the same semester as in the greedy schedule above, which is optimal. If the levels run out before all courses are taken, the untaken courses each keep an untaken prerequisite, and following those links must revisit a course: a cycle, so the answer is -1.

### Complexity

- Time: O(V + E) — each course joins one level, and each relation causes one decrement.
- Space: O(V + E) — adjacency lists, counters and two level lists.

### Trade-offs

Linear, iterative and the same code as Course Schedule plus a level counter, which makes it the default. It produces the actual semester plan for free. It does not generalize to a cap of `k` courses per semester: with a cap, choosing which free courses to take first matters, and that variant needs a search over subsets.

### Pitfalls and edge cases

- Count levels, not dequeued courses: a semester may hold many courses.
- Check that all V courses were taken before returning the level count.

### Language notes

- Python: two plain lists per level make the levels explicit; a `deque` with a level-size loop works too.
- TypeScript: building `nextSemester` arrays avoids queue `shift` costs entirely.
- Java: `--waiting[unlocked] == 0` decrements and tests in one expression.
- Kotlin: `(1..n).filter { waiting[it] == 0 }` builds the first semester.

## Approach: longest-chain-dfs (Memoized depth-first search for the longest prerequisite chain)

### Intuition

The semester of a course is one more than the latest semester among its prerequisites, and 1 when it has none. That recurrence is the length of the longest chain ending at the course, and memoizing it computes every value once. A course met again while its own value is still being computed means its prerequisites loop back to it.

### Algorithm

1. Build `required[after]` and an array `chain`, 0 meaning "not computed".
2. `chainLength(course)`: return -1 if the course is marked `ON_PATH`; return `chain[course]` if it is known; otherwise mark it `ON_PATH`, take the maximum of `chainLength` over its prerequisites (returning -1 if any of them returns -1), store that maximum plus 1, and return it.
3. Return the maximum of `chainLength` over all courses, or -1 if any call returned -1.

### Correctness

In an acyclic graph, `chainLength(course)` equals 1 plus the largest value among its prerequisites, which by induction on the longest chain is the number of courses on the longest chain ending at `course`; the maximum over all courses is the length of the longest chain, which is the answer shown above. Memoized values are final, so reusing them is safe. The `ON_PATH` marks are exactly the courses on the current recursion stack, so meeting one closes a cycle; and if a cycle exists, the first of its courses entered by the search reaches the rest of the cycle while it is still on the path, so the cycle is reported.

### Complexity

- Time: O(V + E) — each course is computed once and each relation is followed once, from its later course.
- Space: O(V + E) — the prerequisite lists, the memo array and a recursion depth of at most V.

### Trade-offs

Linear like Kahn's algorithm and closer to the "longest path in a DAG" view. The recursion is as deep as the longest chain, up to 3000 calls under the constraints, which is fine in all four runtimes here but is a real risk in larger variants; Kahn's version has no such limit.

### Pitfalls and edge cases

- Use a separate `ON_PATH` marker; with only "computed" and "not computed", a cycle recurses forever.
- Shortcut relations (1 before 3 next to 1 before 2 before 3) do not shorten anything: the maximum over prerequisites handles them.

### Language notes

- Python: the runner raises the recursion limit for deep chains; a plain script would need `sys.setrecursionlimit`.
- TypeScript: Node's default stack holds a few thousand frames of this size; chains in the tests stay well below that.
- Java: the JVM runner gives cases a large thread stack, so deep chains are safe.
- Kotlin: a local `fun` recursion with `maxOf` mirrors the recurrence.
