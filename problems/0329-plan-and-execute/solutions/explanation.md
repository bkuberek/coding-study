# Plan and Execute: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| wave-runner | optimal | O(w (n + e)) per run, w the waves | O(n + e) | default answer; one validation function serves the plan and every replan, and one wave loop serves the timeline, the retries and the budget |

Here `n` is the number of tasks, `e` the number of dependencies, and `w` the number of waves of a run, at most `n`.

## How the design grows level by level

| Level | Change | What the design adds |
|-------|--------|----------------------|
| 1 | Validate the plan, order it | A parser for one row, a staged validation that returns sorted error rows, and a topological order with a smallest-id tie-break |
| 2 | Waves, timeline, critical path | A loop that recomputes the ready set at each wave, and a longest-path pass over the topological order |
| 3 | Failures, retries, replans | A status and an attempt counter for each task, a settle step for the tasks that never ran, and a replan hook that reuses the level 1 validation |
| 4 | Budgets and the report | Rounds inside a wave, a stop flag checked before each attempt, and a report that only reads the final state |

The early choice that matters is a single `validate` function. `setPlan` calls it on the rows it is given, and a replan calls it on the rows of the done tasks followed by the rows of the replan. A first version that checks a replan with its own, lighter rules will accept a replan that reuses an id, depends on a task that has not finished, or closes a cycle with a task that is done, and the run then ends in an inconsistent state.

## Approach: wave-runner (Validate once, then run the ready set in waves and settle what never ran at the end)

### Intuition

A plan is a directed graph: an arrow from a task to each task it waits for. A graph like that can be executed only if it has no cycle, because a cycle is a group of tasks that each wait for another. So the first job is to check the graph, and every later job is easy once it is known to be acyclic: a task can run when all the tasks it waits for are done, and tasks that can run at the same moment can run together.

The runner repeats one move. Find the *ready* tasks, take the first `cap` of them in a fixed order, run them, and look again. The same loop produces the timeline when nothing fails, the retries and statuses when something does, and the stop when a budget is gone. A task that fails for good never becomes done, so nothing that waits for it ever becomes ready, and the loop ends by itself when the ready set is empty; what is left is by definition blocked, or skipped if the loop was stopped for another reason.

The contrast with the other designs is in what is decided when. A fixed workflow decides everything when the code is written. A step-by-step loop in the style of ReAct decides one step at a time, from the latest result, and so it cannot validate the whole job, run two steps together or put a budget on a plan it has not seen yet. Plan and execute decides the shape of the job once and checks it before spending anything, and keeps replanning for the moments when the world disagrees with the plan.

### Algorithm

1. **Parse a row.** Check the number of columns, the id pattern, the digits and range of the duration and the cost, and the letters of the script. Remove repeated dependencies, keeping the first of each.
2. **Validate.** Stage 1: collect the malformed rows and stop if there are any. Stage 2: count ids and stop on duplicates. Stage 3: list unknown dependencies, and for each task compute the set of tasks it can reach through known dependencies; a task whose set contains itself is on a cycle, and its group is the tasks it reaches that also reach it. Sort the rows of the stage.
3. **Order.** Kahn's method: a counter of unfinished dependencies for each task, a list of followers, and a min-heap of the free tasks by id.
4. **Waves.** Keep the done set and the clock. Recompute the ready tasks, sort by id, take `cap`, assign start and end, mark done, and move the clock to the latest end.
5. **Critical path.** Walk the topological order and keep for each task the best total and chain. The best dependency is the one with the larger total and, on equal totals, the smaller chain; the answer is the best over all tasks by the same comparison.
6. **Run.** Same waves, but inside a wave each task makes attempts. Attempt `k` reads letter `min(k, length)` of the script. The status becomes `done` on a success or `failed` when the allowed attempts are used. After the wave, go through the failed tasks in id order, try a registered replan once, and stop trying after the first one that is applied. Applying a replan marks every task that has not started `replaced` and adds the replan's tasks.
7. **Budget.** Run the wave in rounds: round `r` gives attempt `r` to every task that is still undecided, in id order. Before each attempt, test the cost limit and then the step limit. The first refusal sets the stop reason and ends all loops, and every task of the wave with a failed attempt but no result becomes `failed`.
8. **Settle.** Visit the tasks that never started in dependency order: `blocked` if a direct dependency is `failed` or `blocked`, `skipped` otherwise.
9. **Report.** Read statuses, totals and counters.

### Correctness

Validation is complete for the cases the statement lists, because each stage looks at a property of the rows that the earlier stages made well defined: row shape before ids, ids before references, references before cycles. A task is on a cycle exactly when it reaches itself, and two tasks are in the same strongly connected component exactly when each reaches the other, so the groups are the cycles of the statement. Kahn's method places every task of an acyclic graph, because while tasks are left there is one with no unfinished dependency, otherwise following unfinished dependencies backwards would walk forever in a finite graph and close a cycle.

The wave loop ends: each pass marks at least one task done, failed or started, or finds the ready set empty and stops. It is correct for the statement because the ready set is recomputed from the statuses at each wave, so a task never starts before a dependency is done. The critical path is correct because a chain that ends at a task is a chain that ends at one of its dependencies plus the task, so keeping the best chain of each dependency is enough, and the tie-break is safe because two chains with the same total cannot be a prefix of each other when every duration is at least 1.

For replans, the new plan is checked as a whole, with the done tasks included, so a replan cannot refer to a task that has not finished, cannot create a cycle with one that has, and cannot take the id of anything that was in the run. After an applied replan the only tasks that have not started are the replan's own, so nothing is run twice and nothing is lost: a replaced task is gone from the plan and appears in the report once.

The budget is correct because every attempt passes through one test before it starts, and the first refusal sets a flag that every loop reads. Rounds make the charging order a function of the plan, the cap and the scripts only, so a run is repeatable.

### Complexity

- Time: O(w (n + e)) per run, w the waves — each wave scans the tasks and their dependencies to find the ready ones; the attempts add at most one step for each of up to 1 + `maxRetries` attempts of each task, and validation, ordering and settling are O(n + e) each (plus O(n (n + e)) for the reachability of the cycle check, which only runs on a plan or replan that is being validated).
- Space: O(n + e) — the tasks, their dependencies, the statuses and the span of each task; the cycle check holds one reachable set for each task, O(n^2) for the moment it runs.

### Trade-offs

- Barrier waves are simple to state and to check, and they lose time: a task whose dependencies finished early waits for the slowest task of its wave. A scheduler that starts a task the moment it is ready and a worker is free has a shorter makespan, down to the critical path when workers are not limited, at the price of a simulated clock with events, and a rule for ties that must be written down for the answer to stay deterministic. Level 2 exposes the gap, since the makespan can be larger than the critical path even when the cap is not a limit.
- Replacing everything that has not started is the simplest replan, and it leaves the replanner free to rearrange work that was not affected by the failure. Replacing only what depends on the failed task keeps the parts of the plan that were fine, but it needs to know which parts those are and to keep their order stable.
- A retry runs the same attempt again. That is safe for a read and is dangerous for an action with effects, such as a payment or a message, unless the action can be repeated without effect (an idempotency key) or the plan marks it as not to be retried. The runner here does not know; the planner and the tools have to.
- A step-by-step loop is the better tool when the next step depends on what the last one found and the job is short; plan and execute is better when the shape of the job is known early, when independent parts can run together and when a spending limit must be enforced. A mixture is common: plan, run, and fall back to a loop for the part that the plan did not foresee.
- The budget limits what the runner starts and not what a running attempt consumes. A limit that must hold during an attempt needs the attempt itself to be bounded (a timeout, a maximum number of tokens).

### Pitfalls and edge cases

- Level 1: a task that only waits for a cycle is not in the cycle row. A dependency listed twice is the same as once. An unknown dependency is written `task>dep` and is left out of the cycle search. The `order` takes the smallest free id at each step, so `[m, a, z]` is a valid answer for a plan where `a` waits for `m`, and sorting all ids first would give `[a, m, z]`, which breaks the dependency.
- Level 2: the cap cuts the ready set by id and the rest wait; a task that becomes ready during a wave starts in the next one. The critical path is a longest chain by duration, not by number of tasks.
- Level 3: the last letter of a script repeats; a task with no failure letter within its attempts never fails. A failed task keeps its attempts, start and end; a replaced or blocked task has none. A replan that reuses the id of the failed task is rejected, since ids are never reused. A replan that depends on a task that is only ready, not yet done, is rejected, and the same replan is accepted in a run with a larger cap in which that task is done by then. The first applied replan of a wave ends replanning for that wave.
- Level 4: a refusal stops everything, including attempts of other tasks that would have fitted, and no replan runs after it. A cost of 0 never exceeds a limit of 0. A task that made an attempt in the stopped wave and is undecided counts as failed, with the attempts it made. A task that waits for a skipped task is skipped, not blocked.

### Language notes

- Python: `sorted` on strings and on lists of strings compares by code point, which is the order the statement asks for, and `min` with a key of `(-total, chain)` gives the critical path tie-break directly. `re.fullmatch` on `[0-9]` accepts ASCII digits only.
- TypeScript: the default `sort()` on strings compares UTF-16 code units, which agrees with the statement for the ids, and rows need an explicit comparator. A `Map` keeps insertion order, so the tasks are visited in the order given and sorted explicitly where the statement says so. The regular expressions are anchored with `^` and `$` because `test` finds a match anywhere.

## Further reading

- [ReAct: Synergizing Reasoning and Acting in Language Models, Yao, Zhao, Yu, Du, Shafran, Narasimhan and Cao, arXiv:2210.03629 (ICLR camera-ready version)](https://arxiv.org/abs/2210.03629): the paper proposes that a language model generates reasoning traces and task-specific actions in an interleaved manner, so that reasoning guides the actions and the actions bring in information from outside. It is the step-by-step loop that this problem contrasts with a plan made first.
- [ReWOO: Decoupling Reasoning from Observations for Efficient Augmented Language Models, Xu, Peng, Lei, Mukherjee, Liu and Xu, arXiv:2305.18323](https://arxiv.org/abs/2305.18323): a method that detaches the reasoning process from external observations, which the authors argue substantially lowers token use compared with approaches that interleave the two.
- [An LLM Compiler for Parallel Function Calling, Kim, Moon, Tabrizi, Lee, Mahoney, Keutzer and Gholami, arXiv:2312.04511](https://arxiv.org/abs/2312.04511): a system with a planner that formulates an execution plan for function calls, a unit that fetches tasks and an executor that runs the functions in parallel.
- [Topological sorting of large networks, A. B. Kahn, Communications of the ACM 5(11), 1962, pp. 558-562, doi:10.1145/368996.369025](https://doi.org/10.1145/368996.369025): the paper presents a general method for obtaining a topological order of a network of activities, the problem that `order` solves.
- [Depth-First Search and Linear Graph Algorithms, R. Tarjan, SIAM Journal on Computing 1(2), 1972, pp. 146-160, doi:10.1137/0201010](https://doi.org/10.1137/0201010): gives an algorithm for the strongly connected components of a directed graph whose time and space are bounded by constants times the vertices plus the edges. The reachability sets used for the cycle rows are simpler and slower; this is the linear-time way.
- [LLM10:2026 Improper Output Handling (2025: LLM05), OWASP Top 10 for LLM Applications 2026](https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/): a plan is output of a model that a later step acts on, which is the situation this entry warns about; level 1 is the check before acting.
- [LLM06:2026 Unbounded Consumption (2025: LLM10), OWASP Top 10 for LLM Applications 2026](https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/): its mitigations include rate limiting and quotas, managing resource allocation, and agentic circuit breakers that enforce step limits and per-run cost ceilings on every agent execution; the budget of level 4 is such a ceiling applied to one run.
