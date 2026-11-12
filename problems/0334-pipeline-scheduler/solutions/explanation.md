# Pipeline Scheduler: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| partition-ledger | optimal | O((V + E) log V) to order; O(V (V + E)) to find the tasks on cycles; O(V + E w) per run of a day; O(R P i + P log P) per backfill | O(V + E) for the graph, plus each written partition and the writes it read | default answer; one ledger of numbered writes answers what is done, what is stale and what a backfill must redo |

Here `V` is the number of tasks, `E` the number of dependencies, `w` the widest window, `P` the number of partitions in a backfill's plan, `R` its number of rounds, and `i` the largest number of partitions that one partition needs (at most `E w`).

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | Tasks and their order | each task's dependencies, in a map; the order is computed on demand from counts of unlisted dependencies and a heap of ready names |
| 2 | Daily partitions | a window per (task, dependency); a map from (task, day) to the partition's state; one helper that lists the partitions a partition needs |
| 3 | Runs, retries and reruns | retries per task and a queue of scripted outcomes per partition; one attempt helper that writes or fails a partition |
| 4 | Backfills | a write counter; each written partition keeps its write number and, for each input, the number it read |

The helper that lists a partition's inputs is the hinge of the design. `runnable` asks whether they are all done, `run` asks the same thing at each task's turn, `stale` compares their write numbers with the ones remembered, and a backfill uses it both ways: forward to skip, and backward (through the tasks that depend on a task) to plan. Writing it once, with the clipping at day 0 and the windows, is what keeps the four levels consistent with each other.

## Approach: partition-ledger (A heap of ready tasks for the order, and a ledger of numbered partition writes)

### Intuition

A run order is a topological order: every task after the tasks it reads. Counting, for each task, how many of its dependencies are not listed yet tells at once which tasks are ready (count zero), and listing a task can only make the tasks that depend on it ready. A heap of the ready names gives the smallest one each time, which is the tie-break the statement asks for. Tasks that never become ready are on a cycle or behind one, and a short search from each of them tells which.

For partitions, the only facts that matter are "done or not" and "what did it read". Numbering every write turns "what did it read" into a few integers, so a partition is stale exactly when one of the numbers it remembers is no longer the current one.

### Algorithm

1. `addTask` stores the dependencies, without repeats, unless the name exists.
2. Order: for each task count its dependencies that are tasks, and for each task list the tasks that depend on it. Put every task with count zero in a min-heap. Pop the smallest, list it, lower the count of each task that depends on it, and push those that reach zero. Repeat until the heap is empty.
3. `validate`: every dependency that is not a task is an `unknown-dependency`. If the order did not list every task, search from each leftover task along its dependencies; it is on a cycle when the search returns to it. Sort the rows. `runOrder` returns `[]` when `validate` reports anything, else the order.
4. `inputs(task, day)`: for each dependency, the days from `max(0, day - window + 1)` to `day`.
5. `runnable(day)`: the tasks whose partition is not done and whose inputs are all done, sorted.
6. `store(task, day)` (for `markDone` and for a successful attempt): add one to the write counter, mark the partition done with that number, and record, for each input, its current number (its write number if it is done, else 0).
7. `attempt(task, day)`: up to `1 + retries` times, take the next scripted outcome (or `ok` if none is left); on `ok`, store the partition and stop. If every attempt failed, mark the partition failed.
8. `run(day)`: for each task in run order, skip it if an input is not done; otherwise attempt it. Report `[task, status, attempts]`.
9. `stale(day)`: the done partitions of that day for which some input's current number differs from the number recorded.
10. `plan`: start from `(task, d)` for each day of the range. For a planned `(u, d)`, each task `t` that depends on `u` with a window of `w` days on it has the partitions `(t, d)` to `(t, d + w - 1)` that need `(u, d)`; add those that are done and not planned yet, and continue from them. Sort by day, then by position in the run order.
11. `backfill`: repeat rounds until every planned partition has a result. In each round, first walk the plan in order and mark as skipped every partition without a result that has a planned input which failed or was skipped, or an input outside the plan that is not done. Then take, in plan order, the partitions without a result whose planned inputs all succeeded, keep the first `cap`, and attempt each one. Report the results sorted by round, day and run order.

### Correctness

The order lists a task only when its count is zero, that is, after all its dependencies, and the heap always holds exactly the tasks that are ready and not yet listed, so taking its smallest name is the statement's tie-break. A task on a cycle can never reach count zero, because one of its dependencies is itself waiting for it; so every task on a cycle is left over, and the search from each leftover task finds a way back to it exactly when one exists. Tasks behind a cycle are left over too, but no way leads back to them, so they are not reported.

`inputs` returns exactly the partitions that the statement says a partition needs: the window's days, with the days before 0 removed. A run attempts a task only when all of them are done at its turn, and since the run goes in run order, a dependency's partition for the day has already been written or has failed by then; a failure therefore stops everything after it. An attempt that succeeds stores a new partition, which replaces the old one, and the attempts of a run are counted from zero, so running a day twice leaves the same states as running it once.

Each write has a number that no other write has, and a partition records the numbers it read, so its recorded number differs from the current one exactly when that input was written again, failed, or was written for the first time after it: the definition of stale. The plan adds exactly the done partitions that need a planned one, and repeats from them, which is the closure the statement describes. In a backfill, every input of a partition comes earlier in plan order, since it is on the same day or an earlier one, and on the same day it belongs to a task earlier in run order. One pass in plan order therefore decides every skip of a round: an input is decided before the partitions that need it. A partition is ready only if every planned input succeeded in an earlier round, so the partitions run in one round never depend on each other, as with `cap` tasks running side by side.

### Complexity

- Time: O((V + E) log V) to order; O(V (V + E)) to find the tasks on cycles; O(V + E w) per run of a day; O(R P i + P log P) per backfill — the order pushes and pops each task once and touches each dependency once. Only when some tasks are left over, a search from each one may visit the whole graph. A run looks at each task once and reads each of its inputs. Each round of a backfill reads the inputs of the partitions without a result, at most `P i`, and the plan and the report are sorted once.
- Space: O(V + E) for the graph, plus each written partition and the writes it read — a partition stores one number per input it read.

### Trade-offs

- A strongly connected components algorithm finds every task on a cycle in one linear pass. The search from each leftover task is shorter to write and quadratic only on graphs that have cycles: level 1's `validate` must report those, and from level 2 on the cases promise valid pipelines.
- A sorted set of ready names works as well as a heap. Sorting the ready tasks of one "layer" at a time does not: it gives another order, because a task that becomes ready after a small name is listed must compete with the names already waiting (`h1`).
- Write numbers make every rewrite a change, even one with identical data. Storing a checksum of the data instead would let a backfill stop at partitions whose output did not change, at the cost of computing it.
- The backfill decides in rounds, all tasks of a round taking the same time. A scheduler with durations would hand a free slot to the next ready partition as soon as one finishes, with the same skip and readiness rules.

### Pitfalls and edge cases

- Ordering ready tasks by insertion order, or level by level, instead of always taking the smallest ready name (`h1`).
- Counting a dependency listed twice twice, so that the task never becomes ready (`h3`); letting a second `addTask` replace the first (`h3`).
- Reporting every task left over by the order as on a cycle: a task that depends on a cycle, or sits between two cycles, is not on one (`h4`, `h5`).
- Sorting the problems by task instead of as rows of text (`h4`).
- A window of `days` that needs `days + 1` partitions, or only its two ends (`h12`); a window that is not clipped at day 0, so that early days are never runnable (`h8`).
- Applying one dependency's window to all of a task's dependencies (`h9`).
- Skipping a task only when a dependency failed in the same run, and missing an earlier day of its window that is not done (`h16`).
- Adding up attempts across runs, or leaving a partition done after a failed rerun (`h15`).
- Restarting a partition's script on every run, or appending to it on a new `script` call (`h14`, `h18`); reading `retries` as the total number of attempts (`h13`).
- Running only the tasks that are not done, which makes `run` no rerun at all (`h19`, `ex6`).
- A staleness check that misses an input that failed, or a partition marked done before its input existed (`h20`, `h21`).
- A plan that stops at the direct dependents, follows only same-day partitions, includes partitions that were never written, or sorts by name (`h22`).
- A backfill that ignores the cap, runs a partition in the same round as its input, decides skips a round late, or starts with the newest days (`h23`, `h24`, `h26`), or that runs a partition whose input outside the plan is missing (`h25`).

### Language notes

- Python uses `heapq`, Java and Kotlin a `PriorityQueue<String>`, Rust a `BinaryHeap` of `Reverse<String>`, and Go `container/heap` over a slice of names. TypeScript has no heap in its standard library, so it keeps the ready names in an array sorted by binary insertion, which is fine for the 200 tasks of the constraints.
- Every language keys the partition maps by (task, day): a tuple in Python and Rust, a struct in Go, a string `task + "\u0000" + day` in TypeScript, and a small record in Java and Kotlin.
- Rows that mix names and numbers are lists of strings, so the numbers go through `str`, `String`, `toString`, `strconv.Itoa` or `to_string`.
- Default string ordering is by character codes in every language here: Python's code points, Java's and Kotlin's UTF-16 code units, TypeScript's default comparison, and Go's and Rust's bytes agree on printable ASCII.

## Further reading

- A. B. Kahn, "Topological sorting of large networks", Communications of the ACM 5(11), 1962, pages 558 to 562, [doi:10.1145/368996.369025](https://doi.org/10.1145/368996.369025): an early general method for putting the nodes of large networks, such as project-planning networks of tens of thousands of activities, in topological order.
- R. Tarjan, "Depth-First Search and Linear Graph Algorithms", SIAM Journal on Computing 1(2), 1972, pages 146 to 160, [doi:10.1137/0201010](https://doi.org/10.1137/0201010): finding the strongly connected components of a directed graph with depth-first search, in time and space linear in the numbers of vertices and edges, the one-pass way to name every task on a cycle.
