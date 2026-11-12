# Plan and Execute

## Statement

Build `PlanRunner`, the part of an assistant that carries out a plan. The plan is written by a language model as a list of subtasks, and the runner does the work: it checks the plan, runs the subtasks in the right order, several at a time, deals with failures, and stops inside a budget. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working as they did.

**What is a plan, and who runs it?** A big job such as "compare three suppliers and write a summary" is made of smaller jobs, called *subtasks*, and some of them need the result of others: the summary needs the three comparisons, and each comparison needs the supplier's data. We say a subtask *depends on* another when it must wait for it. A *plan* is a list of subtasks with those dependencies. There are three common ways to organize such work with a model.

- **A fixed workflow.** The developer writes the steps in code, and the model fills in the contents of each step. It is predictable and cheap, and it can only do the jobs its author foresaw.
- **A step-by-step loop**, the pattern of the ReAct paper: the model thinks about what to do next, does one action, reads the result, and thinks again. It adapts to every result, but it needs a model call for every step, it works on one thing at a time, and nothing outside the model's head says what the whole job looks like, so there is nothing to check before work starts.
- **Plan and execute.** The model is asked once for the whole plan, as data. Ordinary code then checks it, runs it, and calls the model again only when something fails and the plan has to change. The plan can be validated before anything is spent, independent subtasks can run together, and a budget can be enforced. The price is that a plan made before seeing any result can be wrong, which is why a runner needs a way to replan.

This problem builds the runner. There is no model and no clock in it: a plan comes in as rows of text, the time each subtask takes and what it returns are given in the rows, and "time" is a count of simulated units, so every answer is exact. Since a model wrote the plan, the runner trusts nothing in it: level 1 is about finding out whether it is a plan at all.

Aim to finish in 150 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 40, level 2 by 70, level 3 by 120 and level 4 by 145, keeping the last minutes for a final run.

## Input

- `PlanRunner()`: creates a runner with an empty plan, no replans and no budget.
- A **task** is a row of strings `[id, duration, cost, script, output, dep, dep, ...]`:

  | Column | Meaning | Rule |
  |--------|---------|------|
  | `id` | the name of the subtask | 1 to 20 characters from `a` to `z`, `0` to `9` and `_`; ids are compared by the numeric value of their characters, so `10` comes before `9`, and digits before `_`, which comes before letters |
  | `duration` | simulated time units one attempt takes | digits only, at most four of them, value 1 to 1000 |
  | `cost` | what one attempt costs | digits only, at most four of them, value 0 to 1000 |
  | `script` | the result of each attempt, in order | only the letters `S` (success) and `F` (failure), possibly none |
  | `output` | what the subtask returns when it succeeds | any text, possibly empty |
  | `dep` | an id this task depends on | any number of columns; the same id twice means the same as once |

- A plan has at most 100 tasks, and a row has at most 100 columns.
- `cap` is from 1 to 10, `maxRetries` from 0 to 5, and a budget limit is `-1` (no limit) or from 0 to 1000000.
- Each level's section describes the methods it adds and their parameters.

## Output

Questions return lists of ids or rows of strings. Numbers inside rows are written in decimal as text. "Sorted" means compared by the numeric value of the characters of each column in turn.

## Level 1: Validating a plan

- `setPlan(tasks)`: checks the rows and, if they make a valid plan, installs it in place of the previous one. It returns the list of **errors** as rows `[code, detail]`, and `[]` when the plan is valid and installed. When there are errors, the installed plan does not change. An empty list of rows is a valid plan.
- `order()`: the ids of the installed plan in an order in which every task comes after the tasks it depends on, chosen as follows: repeatedly take, among the tasks whose dependencies have all been taken, the one with the smallest id. The answer is `[]` when there is no plan.

The checks come in stages, and a stage is reached only when the one before found nothing.

1. **Malformed rows.** A row is malformed when it has fewer than 5 columns, or its id, duration, cost or script breaks the rule of the table above. Each one gives `["malformed-task", index]`, with the index of the row in the list, counted from 0, as decimal text, in the order of the rows.
2. **Duplicate ids.** Each id that two or more rows have gives `["duplicate-id", id]`, once, sorted.
3. **Dependencies.** An id in a `dep` column that no task has gives `["unknown-dependency", "task>dep"]` (the task, the sign `>` and the unknown id), once for each pair. A **cycle** is a group of tasks that all wait, directly or through others, for each other: the strongly connected component of the dependency graph that has a cycle in it. A task that depends on itself is a cycle of one. Each cycle gives one row `["cycle", ids]`, where `ids` are the ids of the group, sorted and joined with commas. A task that only waits for a cycle, and is not part of it, is not in the row. Unknown dependencies are left out when looking for cycles. The rows of this stage are sorted as a whole, by code and then by detail.

### Example 1

<!-- case: ex1 -->

A diamond: `d` needs `b` and `c`, which both need `a`. The rows are given in any order, and `order` gives `a`, `b`, `c`, `d`. Three tasks with no dependencies come out sorted by id.

### Example 2

<!-- case: ex2 -->

A plan with two tasks that wait for each other and one with a dependency that does not exist is refused with one row for each problem, and the plan installed before stays in place, as `order` shows afterwards.

## Level 2: Waves and a timeline

The runner executes a plan in **waves**. At the start of a wave, the **ready** tasks are those that are not done yet and whose dependencies are all done. The wave takes the first `cap` of them in order of id (the rest wait for a later wave, together with the tasks that become ready). All tasks of a wave start at the same moment, the wave ends when the slowest of them ends, and the next wave starts then. The first wave starts at time 0. This is a deliberate simplification: a task whose dependencies finished early still waits for the end of the wave.

At this level every task runs once and succeeds; `script`, `cost` and `output` are not used.

- `timeline(cap)`: one row `[wave, id, start, end]` for each task, where `wave` counts from 1, `start` is the start of its wave and `end` is `start` plus the task's duration. The rows are sorted by wave and then by id. `[]` for an empty plan.
- `makespan(cap)`: the time at which the last wave ends, `0` for an empty plan.
- `criticalPath()`: the **critical path** is a chain of tasks, each depending on the one before, with the largest total of durations; it is how long the plan takes with as many workers as it wants, if tasks start the moment they can. The answer is the ids of the chain from first to last. When several chains have the same total, the answer is the one that is smaller when compared id by id from the first, and `[]` for an empty plan.

### Example 1

<!-- case: ex3 -->

The diamond with a cap of 2, then 1, then 9. With a cap of 2, `b` and `c` share a wave and the wave lasts as long as `b`; with a cap of 1 every task has a wave of its own, and the makespan is the sum of all durations.

### Example 2

<!-- case: ex4 -->

The critical path runs through `c` and `d` and not through the longer-looking `b`, and its total (9) is shorter than the makespan with a cap of 5 (12): a wave waits for its slowest task, so the barrier costs time. With a cap of 1 the makespan is the sum of all durations.

## Level 3: Failures, retries and replanning

- `run(cap, maxRetries)`: executes the installed plan once, from scratch, with waves as in level 2, and returns for every task of the run one row `[id, status, attempts, start, end]`, sorted by id. The installed plan does not change. For a task that never started, `attempts` is `0` and `start` and `end` are empty strings.
- `replanLog()`: the replans of the last run, as rows `[wave, failedId, result, detail]` in the order they happened; `[]` before any run.
- `setReplan(failedId, tasks)`: registers a **replan** for the task `failedId`: rows of new tasks, in the format of the input. It returns `true` when no replan was registered for this id and `false` when it replaces an earlier one. A registered replan stays until it is replaced, and is used by later runs.

**Attempts.** A task in a wave makes attempts one after the other, each lasting its duration. Attempt `k`, counted from 1, succeeds when the `k`-th letter of the script is `S`; when the script is shorter than `k` its last letter counts again, and an empty script always succeeds. The task stops at its first success, and its status is `done`. When it has made `1 + maxRetries` attempts and the last one failed, it has **failed for good**, with status `failed`. Its `start` is the start of its wave and its `end` is `start` plus `attempts` times the duration. The wave ends at the latest `end` of its tasks.

**Blocked.** A failed task is never done, so a task that depends on it never becomes ready, and neither does any task that depends on that. When the run has no ready task left, each task that never started has the status `blocked` (at this level; level 4 adds another reason).

**Replanning.** After a wave, look at the tasks of that wave that failed for good, in order of id. For one that has a replan registered, and whose replan has not been tried yet in this run, try it:

1. Form the **new plan**: the rows of all tasks that are `done` at this moment, followed by the rows of the replan. Check it with the stages of level 1. Then also refuse it if a task of the replan has the id of any task of this run that is not done: ids are never reused.
2. If there is an error, the replan is **rejected**: the first error of the sorted list becomes the detail `code:detail` of a log row `[wave, failedId, "rejected", detail]`, and the next failed task is tried.
3. Otherwise the replan is **applied**. Every task of the run that has not started gets the status `replaced`; the tasks of the replan are added, ready to run in the next wave and free to depend on done tasks; the log row is `[wave, failedId, "applied", "removed N, added M"]` with the number of replaced tasks and of added ones. Failed tasks stay `failed`. The wave is now finished with replanning: no other failure of the same wave is tried.

A replan is tried at most once per run. The tasks that a replan adds are ordinary tasks of the run: they are listed by `run`, they can fail and be replaced again by a replan registered for their id, and the ones that never started are `blocked` like any others.

### Example 1

<!-- case: ex5 -->

`a` fails twice and then succeeds. With two retries it makes three attempts (from time 0 to 6) and `b`, which waits for it, runs after. With one retry it fails after two attempts, `b` is blocked, and the independent `c` is done anyway. With none it fails at once.

### Example 2

<!-- case: ex6 -->

`a` always fails and `b` waits for it. A replan registered for `a` gives two new tasks that need `r` and `c`, which are done by the end of that wave. After the second wave the replan is applied: `b` is replaced and `x` and `y` run in the next waves. `a` stays failed, and the log has one row.

## Level 4: Budgets and the final report

- `setBudget(maxCost, maxSteps)`: sets the limits for the runs that follow, until set again. `-1` means no limit; the limits start at `-1`. Each **attempt** costs the `cost` of its task and is one **step**.
- `report()`: a summary of the last run, `[]` before any run (see below).

**Stopping.** An attempt may start only if it keeps the totals within the limits: the cost so far plus its cost at most `maxCost`, and the steps so far plus one at most `maxSteps`. Attempts are charged in **rounds** within a wave: first the first attempt of each task of the wave in order of id, then the second attempt of those that need one, and so on. The first attempt that is refused stops the run: no attempt starts after it (even one that would fit), and no replan is tried. The **stop reason** is `cost` when the cost limit refuses it, checked first, and `steps` otherwise. A run that never refuses an attempt has the stop reason `none`. The stop is clean: attempts already made stay, in `run` and in the report. A task of the stopped wave that has made an attempt but not finished is `failed`, with the attempts it made (its `end` is the end of its last attempt); one that has not made any attempt has not started. When a run stops, the clock is the latest `end` of any attempt made.

**What never ran.** A task that never started is `blocked` if a task it directly depends on is `failed` or `blocked`, and `skipped` otherwise; they are decided in dependency order, so a task that waits for a skipped task is skipped. A run with no limit has only blocked ones, as at level 3.

**The report** has these rows, in this order:

| Row | Content |
|-----|---------|
| `["stopped", reason]` | the stop reason |
| `["spent", cost, steps, time]` | the totals of the attempts made and the clock at the end |
| `["done", id, ...]` | the ids with status `done`, sorted (just `["done"]` when there are none) |
| `["failed", id, ...]` | likewise for `failed` |
| `["blocked", id, ...]` | likewise for `blocked` |
| `["skipped", id, ...]` | likewise for `skipped` |
| `["replaced", id, ...]` | likewise for `replaced` |
| `["replans", applied, rejected]` | how many replans were applied and rejected |
| `["results", "id=output", ...]` | the partial results: the output of each done task, sorted by id |

### Example 1

<!-- case: ex7 -->

With no limit, the plan costs 14 in 4 steps. With a cost limit of 8, `a` (3) and `b` (4) are paid, and the attempt of `c` (cost 2) would bring the total to 9: it is refused, the run stops with reason `cost`, and `c` and `d` are skipped. The partial results are those of `a` and `b`.

### Example 2

<!-- case: ex8 -->

With a limit of 3 steps and two retries, the wave of `a` and `c` makes `a` fail, `c` succeed, and then `a` retries (step 3) and fails again. The fourth step, the third attempt of `a`, is refused. `a` is failed with two attempts, `b` is blocked because of it, and `c` is done.

## Constraints

- At most 200 calls per test.
- A plan or a replan has at most 100 tasks.
- A run makes at most 1000 attempts in total.

## Follow-ups

- The runner starts a wave only when the previous one has ended. If a task could start the moment it is ready and a worker is free, how would the timeline and the makespan change, and how would you keep the answer deterministic? How does the makespan with an unlimited cap compare with the critical path then?
- A replan here replaces everything that has not started. When is it better to replace only the failed task and what depends on it? What would the runner have to remember to do that?
- A retry runs the task again. For a task that sends an email or charges a card, what has to be true for a retry to be safe, and who is responsible for it, the planner or the runner?
- The cost of an attempt is known in advance here. How would the budget work if the cost is only known when the attempt ends, and several attempts run at once?
- A plan that came from a model names tasks and tools. What else would you check before running it, and what do the checks of a guard for model-written SQL have in common with the checks of level 1?
- A step-by-step loop can handle a failure by choosing a different action on the spot. What does this runner need in a replan to do the same, and what does it give up?

## Hints

### Hint 1

A dependency is an arrow: "`b` depends on `a`" means `a` must be done before `b` starts. To see the order, play it by hand on three or four tasks on paper: write down the tasks that depend on nothing, do them, cross them out of everyone's list of waiting, and repeat with the tasks that now wait for nothing. If at some point there are tasks left but none of them is free, the plan cannot be run. Turn that into a loop and print the order for small plans before you worry about errors.

### Hint 2

Check the plan in the order of the statement and stop at the first stage that finds something. Read each row into a small record first, so that "malformed" is decided in one place. For the order, keep for each task the number of dependencies not yet taken and, for each task, the list of tasks that wait for it; when you take a task, lower the count of those that wait for it and note the ones that reach zero. Choose the smallest id among the free ones each time.

### Hint 3

A cycle is not just "the loop did not finish". The tasks that the order cannot place include the ones that merely wait for a cycle, and the statement does not want those. Ask for each task what it can reach by following dependencies; a task is on a cycle when it can reach itself, and two such tasks are in the same group when each reaches the other. Collect the groups as sorted lists so that the same group is not written twice.

### Hint 4

Level 2 is a loop over waves. Keep the set of done tasks and the clock. In each pass, find the ready tasks (not done, dependencies all done), sort them, cut to `cap`, give each the start time and its end, mark them done, and move the clock to the largest end. The critical path is a longest-path problem on an acyclic graph: go through the tasks in dependency order and, for each, remember the best total and the chain that gives it.

### Hint 5

For the tie-breaks of the critical path, compare chains as lists of ids; at each task, take the dependency whose best chain has the larger total and, on equal totals, the smaller list. The same comparison picks the final chain among all tasks. Because every duration is at least 1, a chain is never a prefix of another one with the same total.

### Hint 6

For level 3, give each task a status and a counter of attempts. In a wave, loop over the attempts of each task until it succeeds or runs out; to read attempt `k` of a script, take the letter at `min(k, length) - 1`. After the wave, handle the failed tasks in id order. Build the new plan out of the rows you kept for the done tasks and the rows of the replan, and give it to the same validation function as `setPlan`; do not write a second one. When the loop finds no ready task, go through the tasks that never started and mark them.

### Hint 7

For level 4, change the inside of the wave: instead of finishing one task at a time, repeat rounds, each round giving one attempt to every task of the wave that still needs one. Before each attempt, ask whether it fits both limits, cost first; if not, set the stop reason and leave all the loops. Tasks that made an attempt and are still undecided become failed. For the tasks that never ran, go through them in dependency order, so that a task can look at the final status of what it waits for. The report is then only a reading of the statuses, the totals and the replan counters.
