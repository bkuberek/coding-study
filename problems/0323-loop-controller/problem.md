# Loop Controller

## Statement

Build `LoopController`, the part of an agent harness that decides when the agent's loop must stop. An *agent* is a program that repeats one cycle: ask a language model what to do next, run the tool it picked (a search, a file read, a test run), show the model what came back, and ask again. The *harness* is the ordinary code around the model that runs this cycle. A model does not stop itself reliably: it can repeat a failing call forever, wander for hundreds of steps, spend a month of budget in an afternoon, or announce "done" when it is not. So the harness puts brakes on the loop, and the brakes are plain code that you can test without any model. This problem is those brakes. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

Nothing here calls a model or a tool. The whole conversation arrives as data: a list of **steps**, each one the model's choice together with what the tool returned and what it cost. The controller walks that list the way the real loop would, and reports why it stopped.

Aim to finish in 90 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 25, level 2 by 45, level 3 by 70 and level 4 by 88, keeping the last minutes for a final run.

## Input

- `LoopController()`: creates a controller with no brakes except the iteration cap that `run` takes.
- A **step** is a list of six texts, `[action, args, status, result, tokens, millis]`:

| Column | Meaning |
|--------|---------|
| `action` | The tool the model chose, 1 to 30 characters from `a` to `z` and `_`, or the word `final` when the model gave its answer instead of calling a tool. |
| `args` | The arguments of the call, as the text of a JSON object. Its values are strings, integers (at most 10^9 in size, written without a fraction or an exponent), `true`, `false`, `null`, arrays or objects, and no object repeats a key. For a `final` step it is `{}`. |
| `status` | `ok` or `error`. A `final` step is always `ok`. |
| `result` | What the tool returned, or its error message. For a `final` step, the answer. |
| `tokens` | The tokens the step used, a whole number written in decimal. |
| `millis` | The time the step took, in milliseconds, a whole number written in decimal. |

- Texts hold printable ASCII characters (codes 32 to 126) and, in a `result`, also tabs and newlines. A `result` has at most 100 characters.
- Each level's section describes the methods it adds and their other parameters.

## Output

Each method returns what its level describes. Whole numbers inside rows are written in decimal as text. Methods never throw, whatever order they are called in.

## Level 1: Running steps until a stop

A **run** is one pass of the loop over a list of steps. A controller keeps the report of its last run only; every `run` starts from zero.

- `run(maxIterations, steps)`: runs the steps in order, one **iteration** per step, and returns the **reason** the run stopped.
- `iterations()`: the number of iterations the last run executed, and `0` before any run.

Before each iteration the controller asks, in this order:

1. Have `maxIterations` iterations already run? Then stop with `max_iterations`.
2. Is there no step left? Then stop with `out_of_steps`.

Otherwise it executes the next step. If that step's action is `final`, the run stops with `final`. Whatever the other steps returned, `ok` or `error`, the loop goes on: at this level an error is just a result the model will read next.

The cap is asked first, so a run whose steps end exactly at the cap stops with `max_iterations`, and a cap of 0 runs nothing. A `final` step is always executed when its turn comes, so a final answer on the last allowed iteration counts.

### Example 1

<!-- case: ex1 -->

The first run reaches the `final` step on its third iteration, and `iterations()` says 3. The second run has the same steps and a cap of 2, so after two iterations the cap is asked first: `max_iterations`, and the final answer is never read. The third run has two steps and a cap of 10: after the second, no step is left, so `out_of_steps`.

## Level 2: Repeated failures

A model that gets an error often tries the very same call again. The loop would repeat it until the cap, so the controller can stop earlier.

- `setNoProgressLimit(limit)`: from now on, a run also stops with `no_progress` when `limit` failures in a row are the same failure. A `limit` of `0` turns the check off, which is the state of a new controller. A `limit` of `1` stops at the first failure.

**Same failure.** A step is a failure when its status is `error`. Two failures are the same when all three of these are equal:

- the `action`, compared exactly;
- the `args`, compared as JSON values, which means as if parsed: white space, and the order of the keys of an object, make no difference; the order of the items of an array does; `true`, `1` and `"1"` are three different values;
- the **normalized message**, that is, the `result` with its leading and trailing white space removed, every other run of white space (spaces, tabs, newlines) replaced by one space, and every run of digits `0` to `9` replaced by one `#`. Letters keep their case.

Masking digits is this problem's choice: line numbers, durations and counters change from one attempt to the next, while the failure stays the same. It also makes `exit code 1` and `exit code 2` look alike, which is the price.

**Streak.** The controller counts the failures in a row that are the same as the one before. A failure that differs from the previous step starts a new streak of 1; any step that is not a failure (a success, or a `final` step) ends the streak. When the streak reaches `limit`, the run stops with `no_progress`, right after that step.

After a step, the controller now asks: was it a `final` step? Then stop with `final`. Otherwise, is the streak at the limit? Then stop with `no_progress`. So a step that both reaches the limit and is the last the cap allows reports `no_progress`: the cap is only asked before the next iteration. The same success repeated is not a failure and never counts.

### Example 1

<!-- case: ex2 -->

With a limit of 3, the first run reads the same missing file three times and stops after the third: `no_progress`. In the second run, the first two failures are the same failure even though the keys of the arguments come in another order and the message has extra white space. A successful search ends that streak, so the two failures after it are a new streak of 2, one short of the limit, and the run reaches its final answer.

## Level 3: Token and time budgets

A loop also costs money and time. Each step reports the `tokens` it used and the `millis` it took, and the controller can stop when the totals pass a limit.

- `setBudgets(maxTokens, maxMillis)`: sets the limits for the tokens and for the time of one run, for the runs that follow. `-1` means no limit, which is the state of a new controller. `0` is a limit: a budget of 0 is spent before the first step.
- `tripped()`: the budgets that stopped the last run, as rows `[reason, phase, iteration, used, limit]`, in the order tokens then time; `[]` when the run did not stop for a budget, and before any run.

The totals of a run are the sums of the `tokens` and the `millis` of the steps executed so far. A budget is checked at two moments, with two different tests:

- **before a step**, a budget is **spent** when `used >= limit`: there is nothing left to start another step with;
- **after a step**, a budget is **exceeded** when `used > limit`: the step cost more than there was.

Using exactly the whole budget is therefore not an overshoot, but it still ends the run, at the next check before a step. Several checks can be true at once, so their order decides the reason:

| When | Order of the checks, the first true one stops the run |
|------|-------------------------------------------------------|
| Before each iteration | `max_iterations`, then `token_budget`, then `time_budget`, then `out_of_steps` |
| After each step | `final`, then `token_budget`, then `time_budget`, then `no_progress` |

So an answer that arrives with the step that went over budget is still `final`, and a step that goes over budget while reaching the no-progress limit reports the budget. When the reason is a budget, `tripped()` lists that budget first, and also the other budget if it tripped at the same check. A row has the name of the budget (`token_budget` or `time_budget`), the phase (`before` or `after`), the number of iterations executed so far, the amount used and the limit.

### Example 1

<!-- case: ex3 -->

The limits are 1000 tokens and 60000 ms. In the first run the three steps use 400, 400 and 300 tokens: after the third the total is 1100, over the limit, so the run stops with `token_budget` before the final answer is read, and `tripped()` shows the budget, the phase `after`, 3 iterations, 1100 used and the limit 1000. In the second run the time goes over after the second step (61000 ms). The third run finishes within both budgets with a final answer, and `tripped()` is `[]`.

## Level 4: Checking a claim of done

A model that says "done" may be wrong. The harness can hold the claim against a check, such as running the tests, and only believe the model when the check passes. Here the outcome of the check is given as data.

- `setCheck(claims, verdicts)`: installs a **check**. `claims` and `verdicts` have the same length. For each position `i`, a `final` step whose answer (its `result`) is exactly `claims[i]` gets the verdict `verdicts[i]`. An answer that no claim names gets the verdict `no verdict`. A new `setCheck` replaces the previous check; until the first one, there is no check.
- `summary()`: the trace of the last run, as rows described below; `[]` before any run.

**Claims.** Without a check, a `final` step is accepted as before. With a check, a `final` step is a **claim**: the verdict `pass` (the whole text, in lower case) accepts it, and the run stops with `final`. Any other verdict **rejects** it, and the verdict text is the **feedback** that goes back to the model. The loop then carries on, as the real loop would after telling the model what failed: the next step is read within the same caps and budgets.

**A rejection is a failure.** A rejected claim counts as a failure for the no-progress streak, with the action `final`, the arguments of the step and the feedback as its message, normalized like any other. A model that claims "done" again and again, and keeps getting the same feedback, is stuck like one that repeats a failing call, and it is stopped the same way. A rejected claim that goes over a budget stops the run with that budget, by the order of level 3.

**The trace.** `summary()` has one row for each iteration of the last run, in order, and one closing row:

| Row | Columns |
|-----|---------|
| `step` | `"step"`, the iteration number from 1, the `action`, the outcome, the tokens used so far and the milliseconds used so far |
| `feedback` | `"feedback"`, the iteration number, the feedback; right after the `step` row of a rejected claim |
| `stop` | `"stop"`, the reason, the iterations, the tokens and the milliseconds, once, at the end |

The outcome is `ok` or `error` for a tool step, and `accepted` or `rejected` for a `final` step. A run that executed nothing has only the `stop` row.

### Example 1

<!-- case: ex4 -->

Before any run the trace is empty. The check accepts only the claim "patched the parser and tests pass". The model first claims "patched the parser": rejected, with the feedback `fail: 2 tests failing` in the trace, and the loop goes on. After an edit it claims the accepted text, so the run stops with `final` after 4 iterations. The `step` rows carry the running totals: 300 tokens and 1500 ms were used once the first claim was made, at iteration 2.

## Constraints

- At most 200 steps per run, at most 300 calls per test, `0 <= maxIterations <= 1000`.
- `tokens` and `millis` of a step are from 0 to 10^6. `maxTokens` and `maxMillis` are `-1` or from 0 to 10^9. `limit` is from 0 to 100.
- A `result` or a claim has at most 100 characters; a verdict has at most 100 characters and is never empty. `claims` has no repeated text.
- Every `args` is valid as described in the Input section.

## Follow-ups

- A model stuck in a loop may alternate between two calls (A, B, A, B), and then no two neighbours are the same failure. How would you detect it, for example with the last `k` failures, and what does it cost in false stops?
- Masking digits merges `exit code 1` and `exit code 2`. Which parts of a message would you mask or keep in a tool you know, and how would you let each tool decide?
- Budgets here are checked between steps, so one long step can overshoot them. How would you stop a step that is already running?
- The check is given as data here. What changes when it is a real test run that can itself be slow, flaky or fail for a reason that has nothing to do with the claim?

## Hints

### Hint 1

A loop is: while you may go on, take the next step, update some numbers, and decide whether to stop. Write that for level 1 with one counter, the number of iterations, and the two questions that are asked before every step. Return the reason as text.

### Hint 2

Keep everything about one run in one small record that you create at the start of `run`, so that nothing from an earlier run can leak in. The methods that report on the last run only read that record.

### Hint 3

Two failures are "the same" when three things are equal. For each of the three, decide which differences must not matter (white space, the order of keys, the digits in a message) and how you could turn it into one canonical text that compares with `==`. Then a failure is just those three texts together.

### Hint 4

Keep the previous failure and a count. After each step there are only three cases: the step is not a failure, it is the same failure again, or it is a different failure. Write down what happens to the count in each, and only then compare it with the limit.

### Hint 5

Several stops can be true at once, so decide where in your loop the order of the table lives. Try two small ordered lists of checks, one asked before an iteration and one after a step, and ask yourself whether "the budget is used up" means the same before a step as after it. Record the rows of `tripped` where the reason is decided, so that the two cannot disagree.

### Hint 6

Decide what a step is before you decide what it caused. A function that turns a step into an outcome (`ok`, `error`, `accepted` or `rejected`) and a feedback text, using the check, lets the streak logic treat a rejected claim like an error without a special case.

### Hint 7

Build the trace as you go: push the `step` row right after the step is judged, the `feedback` row right after it when there is feedback, and the `stop` row once when the loop ends. Do not rebuild it at the end from other lists.
