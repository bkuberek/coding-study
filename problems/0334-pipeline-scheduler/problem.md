# Pipeline Scheduler

## Statement

Build `PipelineScheduler`, the part of a batch data pipeline that decides what runs, in which order, and what must run again. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**What is a batch pipeline?** A *task* is one step of data work: download yesterday's orders, clean them, add them up into a report. A task can only start once the tasks it reads from have finished, so the tasks and their **dependencies** form a graph. Here a task *depends on* the tasks it reads from, and runs after them. A graph whose dependencies never lead in a circle is a *DAG*, a directed acyclic graph, and a pipeline must be one.

**What is a partition?** A pipeline does not process all of history every time. It processes one slice at a time, usually one day, and each task writes one **partition** of its output per day: the orders of the 3rd, the cleaned orders of the 3rd, the report of the 3rd. Most of a scheduler's work is bookkeeping about partitions: which exist, which can be built now, and which are out of date.

**Why reruns must be safe.** Tasks fail, data arrives late, and bugs are fixed after the fact, so every partition gets computed more than once. A pipeline stays sane when running a task again for the same day *replaces* that day's partition instead of adding to it, so that a rerun gives the same result as a single run. Such a task is called *idempotent*.

Aim to finish in 120 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 30, level 2 by 55, level 3 by 85 and level 4 by 115, keeping the last minutes for a final run.

## Input

- `PipelineScheduler()`: creates a scheduler with no tasks.
- A **task name** is a non-empty string of at most 20 printable ASCII characters other than space (codes 33 to 126).
- A **day** is an integer from `0` to `10^4`. Days are numbered, so the day after day `d` is `d + 1`.
- Each level's section describes the methods it adds and their parameters.

## Output

Names are compared by the numeric codes of their characters, so `"B"` comes before `"a"` and `"10"` before `"9"`. Where a row mixes names and numbers, the numbers are written as decimal text, as in `["clean", "success", "2"]`.

## Level 1: Tasks and their order

- `addTask(name, deps)`: adds a task that depends on the tasks named in `deps`, and returns `true`. A name in `deps` may belong to a task that is added later, and a name listed twice counts once. If a task called `name` exists already, the call returns `false` and changes nothing.
- `validate()`: the problems that keep the tasks from being a pipeline, as rows:
  - `["unknown-dependency", task, dep]` for every name `dep` in the dependencies of `task` that is not the name of any task.
  - `["cycle", task]` for every task on a **cycle**: a task from which you can follow dependencies, one after another, and come back to the task itself. A task that depends on itself is a cycle of one. A task that only depends on a cycle, without being on it, is not reported.
  - The rows are sorted, comparing them as text element by element, so every `"cycle"` row comes before every `"unknown-dependency"` row. A valid pipeline gives `[]`.
- `runOrder()`: `[]` when `validate()` reports a problem. Otherwise every task once, each after all of its dependencies. Of the tasks whose dependencies are all already listed, the one with the smallest name comes next.

### Example 1

<!-- case: ex1 -->

The second `addTask("clean", ...)` returns `false`. `extract` and `users` have no dependencies, so both can go first, and `extract` has the smaller name. Once it is listed, `clean` is ready too, and `clean` comes before `users`. `report` waits for `clean` and `users`.

### Example 2

<!-- case: ex2 -->

`a`, `b` and `c` depend on each other in a circle, and `e` depends on itself, so all four are on cycles. `d` depends on `zzz`, which is no task. The rows come sorted, and since the tasks are not a valid pipeline, there is no run order.

## Level 2: Daily partitions

From now on every task writes one partition per day, written `(task, day)`. A partition of a task **needs** partitions of its dependencies, and is **done** once it has been written successfully.

- `setWindow(task, dep, days)`: the partition `(task, d)` needs the `days` partitions of `dep` from `d - days + 1` to `d`, a **lookback window**: a weekly summary of day `d` needs the seven days that end on `d`. Without a window, a partition needs its dependency's partition of the same day, which is a window of `1`. It returns `true`, or `false` when `dep` is not one of the dependencies of `task` (or `task` is not a task), and then it changes nothing.
- No partition exists before day `0`, so a window that reaches back before day `0` needs only its days from `0` on.
- `markDone(task, day)`: records that the partition `(task, day)` was written, outside the scheduler, as if a run had built it just now.
- `runnable(day)`: the tasks whose partition for `day` is not done, and whose needed partitions are all done, sorted by name.

The cases of this level and the next ones use valid pipelines, and they set every window before any partition is written.

### Example 1

<!-- case: ex3 -->

`weekly` has a window of 3 days on `clean`. On day 1, `clean` can run: its `extract` partition is done. On day 3 nothing can run: `extract` and `clean` are done, and `weekly` needs `clean` for days 1, 2 and 3, and day 1 is missing. Once it is done, `weekly` can run on day 3. On day 4, only `extract` can run, since it needs nothing.

### Example 2

<!-- case: ex4 -->

`weekly` has a window of 3 days on `clean` and of 2 days on `extract`. `setWindow` on a pair that is not a dependency is refused. At first only `extract` can run on day 1. For day 1 the windows reach back to day -1 and day 0; only days 0 and 1 exist, and `weekly` becomes runnable once both are done for both of its dependencies.

## Level 3: Runs, retries and reruns

- `run(day)`: runs the pipeline for `day`: it goes through **every** task in run order, whether its partition is done or not, and for each one:
  - If one of the partitions it needs is not done at that moment, the task is **skipped**: its partition stays as it was. This is how a failure stops the tasks after it: a failed partition is not done.
  - Otherwise it is **attempted**. An attempt either succeeds, and the partition becomes done, replacing whatever it held before, or fails. A failed attempt is tried again while the task has retries left; when its last attempt fails, the partition becomes **failed**, and what it held before is gone.
  - It returns one row per task, in run order: `[task, status, attempts]`, where `status` is `"success"`, `"failed"` or `"skipped"`, and `attempts` is the number of attempts made in this run (`"0"` for a skipped task).
- `setRetries(task, retries)`: a task with `retries` retries makes at most `1 + retries` attempts in one run. A task has 0 retries until this is called.
- `script(task, day, outcomes)`: the outcomes of the next attempts of the partition `(task, day)`, in order, each `"ok"` (it succeeds) or `"fail"`. Each attempt takes the next outcome from the front of the list, and an outcome that one run does not use waits for the next attempt of that partition, in a later run. When the list is empty, attempts succeed. A new `script` call for a partition replaces the outcomes it had left.
- `status(task, day)`: `"done"`, `"failed"`, or `"missing"` when the partition has never been written and has never failed.

A run *overwrites*: a partition holds only what its latest successful attempt wrote, so running a day again gives the same partitions as running it once, and the attempts of earlier runs do not count in a later run.

### Example 1

<!-- case: ex5 -->

`clean` has one retry, and its first attempt on day 1 fails, so it succeeds on the second. On day 2, `report` fails its only attempt, so its partition is failed, while its day-1 partition is still done.

### Example 2

<!-- case: ex6 -->

On day 3 `extract` fails, so `clean`, which needs it, is skipped, and so is `report`. `clean` has never been written for day 3, so its status is `"missing"`. The second run of day 3 has no failing outcome left, and every task succeeds. Running the day a third time gives the same result: the partitions are replaced, not added to.

## Level 4: Backfills

A *backfill* reruns a task over a range of past days, after a fix or after late data arrived. The partitions that read the old output are now out of date too, and must run again after it.

**Stale partitions.** Every write of a partition, by a successful attempt or by `markDone`, gets a number, larger than every number before it. When a partition is written, it remembers, for each partition it needs, the number of that partition's latest write, or `0` if that partition is not done. A done partition is **stale** when, for one of the partitions it needs, the number it remembers is not the current one: that input has been written again since, it is no longer done, or it has been written for the first time since.

- `stale(day)`: the tasks whose partition for `day` is done and stale, sorted by name.
- `plan(task, fromDay, toDay)`: the partitions that a backfill of `task` from `fromDay` to `toDay` would run, as rows `[day, task]`:
  - `(task, d)` for every day `d` from `fromDay` to `toDay`, whatever its state;
  - and every **done** partition that needs a partition of the plan, through its windows, and every done partition that needs one of those, and so on. A partition that is not done read nothing that changes, so it is not part of the plan.
  - The rows are in **plan order**: oldest day first, and for the same day, in run order.
- `backfill(task, fromDay, toDay, cap)`: runs the partitions of the plan in **rounds**, as a scheduler that may run at most `cap` tasks at once would:
  - At the start of each round, every partition of the plan that has no result yet is skipped if one of the partitions it needs is in the plan and has failed or been skipped, or is not in the plan and is not done. Its result is `"skipped"` in this round.
  - Then the partitions of the plan without a result, whose needed partitions that are in the plan have all succeeded in this backfill, are the **ready** ones. The first `cap` of them, in plan order, are attempted, as in `run`, with retries and scripted outcomes. A partition that waits for another one of this round cannot start until the next round.
  - Rounds go on until every partition of the plan has a result. The answer has one row per partition of the plan, `[round, day, task, status, attempts]`, sorted by round, then day, then run order.

### Example 1

<!-- case: ex7 -->

After days 0 to 3 have run, nothing is stale. Day 2 then runs again, which rewrites `extract`, `clean` and `weekly` for day 2. `weekly` on day 3 read `clean` of days 2 and 3, and day 2 has been written since, so it is stale. A backfill of `extract` on day 2 would rerun the three partitions of day 2 and `weekly` of day 3.

### Example 2

<!-- case: ex8 -->

A backfill of `clean` over days 0 and 1 plans those two partitions and the three `weekly` partitions that read them. With a cap of 2, the first round runs both `clean` partitions. The three `weekly` partitions are then ready, but only two fit in the second round, the oldest first, so `weekly` of day 2 runs in a third round. Afterwards nothing on day 2 is stale.

## Constraints

- At most 200 tasks and 2,000 dependencies, and at most 10^4 calls per test.
- `1 <= days <= 30` in `setWindow`, `0 <= retries <= 5`, `1 <= cap <= 100`.
- At most 10 outcomes per `script` call.
- `fromDay <= toDay`, and a plan holds at most 2,000 partitions.

## Follow-ups

- `validate` names the tasks on cycles by searching from each leftover task. How would an algorithm that finds strongly connected components name them all in one pass over the graph?
- Here an attempt either succeeds or fails at once. Real attempts take time. How would you simulate durations, so that a round ends when its first task finishes and the freed slot goes to the next ready task?
- A stale partition is detected from write numbers, so a rewrite with identical data still makes everything after it stale. What would you store instead to rerun only what really changed?
- A failed rerun here leaves the partition failed and its old data gone. What would writing to a temporary place and swapping it in at the end change about `stale` and about the tasks downstream?

## Hints

### Hint 1

For the run order, think about which tasks can go first: those with no dependencies at all. After they are listed, some other tasks have all their dependencies listed, and they can go next. Keeping a count of unlisted dependencies per task makes "is it ready?" a check against zero.

### Hint 2

Keep the ready tasks in a structure that always hands you the smallest name, such as a min-heap or a sorted set. When a task is listed, lower the count of every task that depends on it, and add those whose count reaches zero. If the procedure ends before every task is listed, the leftovers are on a cycle or depend on one.

### Hint 3

Among the leftover tasks, a task is on a cycle when a walk along its dependencies can come back to it. A search from each leftover task, with a set of the tasks already visited, answers that.

### Hint 4

For partitions, use a dictionary keyed by the pair (task, day). Write one helper that lists the partitions a partition needs: for each dependency, the days of its window, starting no earlier than 0. `runnable`, `run` and the backfill all ask the same question of that list: is every one of them done?

### Hint 5

Give every write a number from a counter, and store with each written partition a small dictionary from each partition it needs to the number it saw. Staleness is then a comparison of those numbers with the current ones. A run and a backfill can share one helper for the attempts of one partition: take outcomes from the front of its script until one succeeds or the attempts run out.

### Hint 6

To build the plan, keep, for each task, the tasks that depend on it. From a planned partition `(u, d)`, a dependent task `t` with a window of `w` days on `u` has the partitions `(t, d)` to `(t, d + w - 1)` that read it; add those that are done, and continue from them. In a backfill, a partition's inputs always come before it in plan order, so a single pass through the plan in that order at the start of each round finds every partition to skip.
