# Course Schedule: Explanation

## Overview

V is the number of courses and E the number of prerequisite pairs. Model each pair `[course, required]` as an arrow `required -> course`; all courses can be completed exactly when this directed graph has no cycle.

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| repeated-scan | brute | O(V * (V + E)) | O(V + E) | a direct simulation; fine for tiny inputs |
| kahn | optimal | O(V + E) | O(V + E) | default answer; also yields an order, and needs no recursion |
| three-color-dfs | optimal | O(V + E) | O(V + E) | you already think in depth-first search, or need cycle detection elsewhere |

## Approach: repeated-scan (Repeatedly scan for a course whose prerequisites are all done)

### Intuition

Simulate a student: at every step, look through the catalog for any course not taken yet whose prerequisites are all done, and take it. If V steps succeed, everything is done. If at some step no course qualifies, every remaining course waits on another remaining course, and nothing will ever change.

### Algorithm

1. Build `required[course]`, the list of its prerequisites.
2. Repeat V times:
   1. Scan the courses in index order for one that is not taken and whose prerequisites are all taken.
   2. If none exists, return `false`; otherwise mark it taken.
3. Return `true`.

### Correctness

Each step takes a course only when all of its prerequisites are already taken, so the sequence of taken courses respects every pair; if V steps succeed, it is a valid order. If a step finds nothing, every untaken course has an untaken prerequisite. Following "has an untaken prerequisite" from any untaken course must eventually revisit a course, since there are finitely many, so the untaken courses contain a cycle, and no order can take the courses on that cycle.

### Complexity

- Time: O(V * (V + E)) — up to V steps, each scanning up to V courses and their prerequisite lists, O(V + E) in total per step.
- Space: O(V + E) — the prerequisite lists and the `taken` flags.

### Trade-offs

The most literal reading of the statement and a useful oracle, but each step rediscovers from scratch what changed in the previous one. When a long chain of prerequisites lets only one course become free at a time, the cost is quadratic. Kahn's algorithm keeps exactly that information (how many prerequisites each course still waits for) and updates it incrementally.

### Pitfalls and edge cases

- Courses that appear in no pair are free from the start.
- A course listed with several prerequisites must wait for all of them, not any one.

### Language notes

- Python: the `for ... else` clause runs only when the loop did not `break`, which is exactly the "no free course" case.
- TypeScript: `every` checks all prerequisites and is `true` for an empty list.
- Java: a helper `allTaken` keeps the scan readable; lists of `Integer` unbox in the enhanced `for`.
- Kotlin: `firstOrNull { ... } ?: return false` expresses "take the first free course or give up" in one line.
- Go: Python's `for ... else` has no counterpart, so a `found` flag ends the inner loop and the outer one returns `false` when it stays unset. `allTaken` replaces the generator expression passed to `all`.
- Rust: `(0..count).find(|&course| ...)` returns the first course that can be taken as an `Option`, which replaces `for ... else`, and `iter().all(...)` stops at the first prerequisite that is not taken yet. Course numbers arrive as `i32` and are cast to `usize` once, when the lists are built.

## Approach: kahn (Queue the courses whose remaining prerequisite count drops to zero)

### Intuition

Instead of rescanning, remember for each course how many prerequisites it still waits for. A course whose count is zero can be taken now. Taking a course only affects the courses it unlocks, so decrement their counts, and those that reach zero join the queue. If the queue empties before every course was taken, the rest wait on a cycle.

### Algorithm

1. Build `unlocks[required]`, the courses that list `required`, and `waiting[course]`, the number of its prerequisites.
2. Put every course with `waiting == 0` into a queue.
3. While the queue is not empty: take a course, count it, and for each course it unlocks decrement `waiting`; enqueue it when the count reaches 0.
4. Return whether the count equals V.

### Correctness

A course enters the queue only when all of its prerequisites have left it, so the order in which courses leave the queue respects every pair. Conversely, suppose some course is never taken. Its count never reached zero, so it has a prerequisite that was never taken either; repeating the argument walks backwards through untaken courses forever, which forces a cycle among them. So the count reaches V exactly when the graph is acyclic.

### Complexity

- Time: O(V + E) — building the lists is O(V + E); every course is enqueued at most once, and each pair is used for one decrement.
- Space: O(V + E) — the adjacency lists, the counters and the queue.

### Trade-offs

Linear, iterative and easy to extend: the dequeue order is a valid course order, and processing the queue level by level gives the number of semesters in Parallel Courses. It needs the in-degree array in addition to the adjacency lists.

### Pitfalls and edge cases

- Arrows point from the required course to the course that needs it; reversing them still detects cycles correctly but is easy to confuse when you also need an order.
- Count all courses, including those that appear in no pair.

### Language notes

- Python: `collections.deque` gives O(1) `popleft`.
- TypeScript: arrays have O(n) `shift`, so the reference walks a growing array with a `head` index; the array's final length is the number of courses taken.
- Java: `ArrayDeque<Integer>` is the standard queue; `--waiting[unlocked] == 0` decrements and tests in one step.
- Kotlin: `kotlin.collections.ArrayDeque` has `removeFirst` and `addLast`; destructuring `(course, before)` works on `IntArray` pairs.
- Go: a slice serves as the queue (`ready[1:]` pops the front), `waiting` is a counter slice, and `for course, count := range waiting` collects the courses that start with no prerequisites.
- Rust: `VecDeque<usize>` is the queue and is built from a `filter` over the course range. The counters are an `i32` vector that is only decremented for a course that is still waiting, so the `-= 1` never goes below zero when every edge is counted once.

## Approach: three-color-dfs (Depth-first search that detects a path looping back on itself)

### Intuition

Explore prerequisites depth-first. While a course's prerequisites are being explored, the course is "on the current path". Reaching a course that is still on the path means a chain of prerequisites has looped back to where it started: a cycle. Courses whose exploration finished are safe and never need to be explored again.

### Algorithm

1. Build `required[course]` and mark every course `UNVISITED`.
2. `completes(course)`: mark it `ON_PATH`; for each prerequisite, return `false` if it is `ON_PATH`, and recurse into it if it is `UNVISITED` (returning `false` if that fails); then mark the course `DONE` and return `true`.
3. Return whether `completes` succeeds for every course that is not yet `DONE`.

### Correctness

The `ON_PATH` courses are exactly the courses on the current chain of recursive calls, each a prerequisite of the one before. Finding an `ON_PATH` prerequisite closes that chain into a cycle, so the answer is `false`. If there is a cycle, consider the first of its courses that the search visits: all others on the cycle are reachable from it and still `UNVISITED`, so the search reaches the course just before it on the cycle while it is still `ON_PATH`, and the cycle is reported. A `DONE` course has had every prerequisite chain below it explored without finding a cycle, so skipping it later is safe.

### Complexity

- Time: O(V + E) — each course is marked `ON_PATH` and `DONE` at most once, and each pair is examined once, when its course is explored.
- Space: O(V + E) — the prerequisite lists, the states and a recursion depth of at most V.

### Trade-offs

Same bound as Kahn's algorithm, with less bookkeeping (no counts) but recursion as deep as the longest prerequisite chain, here up to 2000 calls. The post-order of `DONE` marks is also a valid course order, required courses first. Two colors are not enough: a plain visited flag cannot tell a cycle from two paths meeting at a shared prerequisite.

### Pitfalls and edge cases

- A diamond (two courses sharing a prerequisite) is not a cycle: the shared course is `DONE` the second time it is reached, not `ON_PATH`.
- Start the search from every course, not only from courses that appear in pairs, and skip those already `DONE`.

### Language notes

- Python: the runner raises the recursion limit, so recursion as deep as 2000 is safe here; the default limit of 1000 would not be.
- TypeScript: Node's default stack comfortably holds 2000 frames of this size.
- Java: the reference passes the graph and states as arguments to a private helper.
- Kotlin: a local recursive `fun` captures the graph and the state array; `all { ... }` stops at the first failure.
- Go: the three states are `iota` constants, and a recursive closure needs its `var completes func(course int) bool` declaration first, because the name must exist before the closure body refers to it. Goroutine stacks grow on demand, so deep chains do not overflow.
- Rust: the recursion is a free function that takes the prerequisite lists and the `state` slice as parameters, since a Rust closure cannot call itself. The `all` over the courses borrows `state` mutably inside the closure, which is fine because nothing else holds it. The runner gives each case a large stack, so a long prerequisite chain does not overflow.
