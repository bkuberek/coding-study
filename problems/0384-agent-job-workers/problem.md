# Agent Job Workers

## Statement

Build `AgentJobWorkers`, the machinery that runs AI agent work in the background. A user asks an agent for a report; the agent will need minutes of model calls and tool calls, so the request becomes a **job** that waits in a **queue**, and a pool of **workers** takes jobs from the queue and runs them. Splitting the work this way lets each layer grow on its own: the queue holds any number of waiting jobs, the pool grows and shrinks with the backlog, and the tools the agents call are protected from the crowd. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

Nothing here runs a real worker, a thread or a clock. Time is a whole number of seconds, `now`, that the caller passes in, and a worker is just a name in the calls it makes. A worker that crashes simply stops calling. Level 1 builds the queue, with **leases** so that a crashed worker's job is not lost. Level 2 keeps a job's progress in a shared store, so that the next worker resumes it instead of starting over. Level 3 decides how many workers to run from the size of the backlog, and level 4 puts a gateway between the workers and the tools they call.

Aim to finish in 150 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 40, level 2 by 65, level 3 by 95 and level 4 by 140, keeping the last minutes for a final run.

## Input

- `AgentJobWorkers(leaseSeconds)`: creates an empty system whose leases last `leaseSeconds` seconds, from 1 to 10^6.
- A job id, a worker id, a tenant and a tool are names of 1 to 20 characters from `a` to `z`, `0` to `9` and `-`.
- `now` is a time in whole seconds. Time never goes back: each method that takes `now` gets one at least as large as the last `now` given to any method.
- Each level's section describes the methods it adds and their other parameters.

## Output

Methods return status words, job ids and report rows, as each level describes. A status that turns a request down, such as `"duplicate"`, `"lost"`, `"already_done"` or `"gap"`, means that **nothing has changed**. Rows are lists of strings, in which numbers are written in decimal. Methods never throw, whatever order they are called in.

## Level 1: A job queue with leases

A queue is a list of jobs waiting to be done, and a worker is a program that repeatedly takes a job, works on it and reports it done. Two things can go wrong. A worker can crash in the middle of a job, and nobody will ever report the job done. And a client that sent a job and got no answer may send it again. The queue handles the first with a **lease** and the second by remembering every job id.

**Leases.** A worker takes a job by **claiming** it. The claim gives the worker a lease on the job: for `leaseSeconds` seconds, the job is the worker's, and no other worker can claim it. A lease given at time `t` **ends** at `t + leaseSeconds`; it is **active** at time `now` when `now < end`, so at its end second it is already over. A worker that is still working sends a **heartbeat** before the end, which renews the lease: it now ends `leaseSeconds` after the heartbeat. A worker that crashed sends nothing, its lease ends, and the job can be claimed again by any worker, under a lease of its own. A worker *holds* a job when the job's lease was last given to it and is still active.

- `submit(jobId)`: adds a job to the end of the queue and returns `"queued"`. A job id that was submitted before, whatever its job's state, returns `"duplicate"`: submitting is idempotent, so a client can safely send a job twice.
- `claim(now, workerId)`: a worker works on one job at a time. If `workerId` already holds a job, `claim` returns that job's id and changes nothing, not even the lease's end. Otherwise it gives the worker a lease on the job **submitted first** among the jobs that are not done and have no active lease, and returns its id. A job whose lease ended keeps its place in the queue. When no job can be claimed, it returns `""`.
- `heartbeat(now, workerId, jobId)`: when `workerId` holds `jobId`, its lease now ends at `now + leaseSeconds`: `"ok"`. Otherwise `"lost"`: the job is unknown, done, held by another worker, or its lease is over, even if nobody has claimed it since.
- `complete(now, workerId, jobId)`: asks, in this order: is the job done already? Then `"already_done"`, whoever asks: a second completion is harmless. Does `workerId` hold the job? Then the job is done, the worker holds it no more, and the answer is `"ok"`. Otherwise `"lost"`: a worker whose lease is over must not finish a job that another worker may be running.
- `jobState(now, jobId)`: `"unknown"` for a job never submitted, `"done"`, `"leased"` while its lease is active, and `"queued"` otherwise.

### Example 1

<!-- case: ex1 -->

The second `a` is a duplicate. Worker `w1` claims `a`, the job submitted first, and `w2` gets `b`; for `w3` nothing is left. When `w1` claims again while it holds `a`, it gets `a` back. It completes `a`, and a second completion hears `already_done`. At second 6, `a` is done, `b` is leased, and `c` was never submitted.

### Example 2

<!-- case: ex2 -->

Leases last 10 seconds. The lease from second 0 would end at 10, but the heartbeat at 8 renews it until 18, so the job is leased at 17 and free again at 18, when `w2` claims it. `w1` comes back too late: its heartbeat and its completion are `lost`, while `w2` completes the job. When `w1` tries once more, the job is done, and it hears `already_done`.

## Level 2: Resuming from the shared store

An agent job is a series of **steps**: plan, search, read, write a draft. Each step costs model calls, and some have effects outside, such as sending a message. A worker that keeps its progress in its own memory loses it when it crashes, and the next worker repeats every step. So workers keep nothing: after each step, the worker saves the step's output in a **shared store** under the job's id. Any worker that claims the job reads what was saved and continues with the first step that is missing.

The steps of a job are numbered from 1, and the store holds the outputs of the steps saved so far, in order.

- `checkpoint(now, workerId, jobId, step, output)`: saves the output of step `step` of the job. It asks, in this order:
  1. Does `workerId` hold the job? If not, `"lost"`: a worker whose lease is over must not write, even a step that is already saved, because another worker may be running the job.
  2. Is the step already saved, `step <= saved` where `saved` is the number of steps saved? Then `"duplicate"`, and the saved output stays, even when this one differs. A worker that is not sure its write went through can send it again.
  3. Does the step skip ahead, `step > saved + 1`? Then `"gap"`.
  4. Otherwise the output is saved as the next step, and the lease is renewed as by a heartbeat: it now ends at `now + leaseSeconds`. A worker that makes progress is alive. The answer is `"ok"`.
- `progress(jobId)`: the outputs of the job's saved steps, in step order; `[]` for a job with none and for an unknown job. A resuming worker continues with the step after the last one saved.

Progress belongs to the job: it stays when a lease ends, when another worker claims the job, and when the job is done. `complete` is unchanged and does not look at the steps.

### Example 1

<!-- case: ex3 -->

Leases last 10 seconds. Each checkpoint renews `w1`'s lease, so the second one, at 9, moves its end to 19: the job is still leased at 18. Then `w1` crashes, and at 19 `w2` claims the job, reads the two saved steps and continues with step 3. Nothing is done twice.

### Example 2

<!-- case: ex4 -->

`w1` saves step 1 at second 1, then stalls past the end of its lease, 11, when `w2` claims the job. `w1`'s write at 12 is `lost`. `w2`, unsure whether step 1 is saved, sends it again: `duplicate`, and the first output stays. Step 3 cannot come before step 2 (`gap`); step 2 is saved, and the job holds two steps.

## Level 3: Scaling by the backlog

How many workers should run? A worker that runs an agent spends most of its time waiting for a model or a tool to answer, so its processor stays almost idle even when hundreds of jobs wait. A rule that adds workers when the processors are busy would never add one. The signal that matters is the **backlog**: the number of jobs submitted and not yet done, waiting or being worked on. A **controller** turns the backlog into a worker count.

- `setScaling(minWorkers, maxWorkers, jobsPerWorker, upCooldown, downCooldown, alertBacklog)`: starts the controller with these settings. The worker count is `minWorkers`, and no change is on record yet. A later `setScaling` starts the controller again the same way.
- `scale(now)`: evaluates the rule below and returns `[decision, workers, desired, alert]`; `[]` when `setScaling` was never called.

**The rule.**

1. `needed` is the backlog divided by `jobsPerWorker`, rounded **up**: 5 jobs at 2 per worker need 3 workers, and an empty backlog needs 0.
2. `desired` is `needed` held between the bounds: `minWorkers` when it is lower, `maxWorkers` when it is higher.
3. When `desired` equals the worker count, the decision is `"hold"`.
4. Otherwise the controller wants to go up (`desired` is higher) or down. A change must wait for a **cooldown** after the previous change: `upCooldown` seconds to go up and `downCooldown` to go down, both counted from the last change, in either direction. The change is allowed when no change is on record yet, or when `now - lastChange >= cooldown`. Then the worker count becomes `desired`, at once and not one worker at a time, the change is recorded at `now`, and the decision is `"up"` or `"down"`. Otherwise the decision is `"cooldown"` and the count stays.
5. `alert` is `"on"` when the backlog is at least `alertBacklog`, and `"off"` otherwise: the backlog that should page a person, whatever the controller does.

`workers` is the worker count after the decision, and `desired` is the value of step 2. Starting workers takes time and stopping them loses work in flight, so a controller that follows every small change would keep adding and removing workers; the cooldowns damp that, and a long `downCooldown` with a short `upCooldown` scales up fast and down slowly.

### Example 1

<!-- case: ex5 -->

Two jobs per worker, between 1 and 5 workers. Five jobs need 3 workers, and the first change needs no wait: `up`. Four more jobs make 9, which need 5, but only 5 seconds have passed of the 10-second cooldown: `cooldown`, with the alert on, since the backlog reached 8. At second 10 the cooldown is over.

### Example 2

<!-- case: ex6 -->

One job per worker and a minimum of 0. Both jobs are being worked on, and they still count: 2 workers, and a backlog of 2 turns the alert on. When one is done, 1 worker is enough, but going down waits 30 seconds after the last change, made at 0. At 31 both jobs are done and the pool goes straight to 0.

## Level 4: A gateway for the tools

Every agent calls tools: a web search, a code runner, a paid data service, shared by all the workers and all the **tenants** (the customers whose jobs they run). More workers mean more calls, and a tool has limits of its own and fails from time to time. A **gateway** sits between the workers and the tools: it limits how fast each tenant and each tool is called, retries a call that fails, stops calling a tool that keeps failing, and says why it refused.

- `setToolLimit(tool, capacity, refillPerSecond)` and `setTenantLimit(tenant, capacity, refillPerSecond)`: give the tool, or the tenant, a **token bucket**, replacing any earlier one. A tool or a tenant without one has no limit.
- `setRetry(maxAttempts, baseDelay, maxDelay)`: the retry policy of every call, replacing any earlier one. Before the first `setRetry`, `maxAttempts` is 1: no retry.
- `setBreaker(tool, failureThreshold, openSeconds)`: gives the tool a **circuit breaker**, replacing any earlier one; it starts closed with no failures counted. A tool without one is never refused by a breaker.
- `call(now, tenant, tool, outcomes)`: the tenant calls the tool, starting at `now`. The tool's answers are given as data: `outcomes[i]` is `"ok"` or `"error"`, what attempt `i + 1` gets if it is made. It returns `[result, attempts, end]`, described below.
- `breakerState(now, tool)`: `"closed"`, `"open"` or `"half_open"` at `now`, by the rules below; `"none"` for a tool without a breaker.

**Token buckets.** A bucket holds whole tokens, at most `capacity`, and starts full. It gains `refillPerSecond` tokens per second: each time the gateway looks at a bucket at time `t`, the bucket first gains `refillPerSecond * (t - last)` tokens, where `last` is the time it was last looked at, and is then cut back to `capacity` if it holds more. The first look at a new bucket finds it full. An attempt needs one token from the tenant's bucket and one from the tool's, when they have one.

**Circuit breakers.** A tool that is down gets no better for being called, and every call that waits for it ties up a worker. A breaker counts the tool's **failures in a row**, across all calls and tenants: an attempt that gets `"error"` adds one, and one that gets `"ok"` sets the count back to 0.

- **Closed**: attempts go through. When the count reaches `failureThreshold`, the breaker **opens**, at the time of the attempt that failed.
- **Open**: no attempt is made. A breaker that opened at time `o` is open while `now < o + openSeconds`, and **half-open** from `o + openSeconds` on.
- **Half-open**: the next attempt is a **trial**. If it gets `"ok"`, the breaker closes with a count of 0; if it gets `"error"`, the breaker opens again at the time of the trial, for a whole new `openSeconds`. The gateway serves one call at a time, so a trial always ends before the next attempt.

**A call.** A call makes attempts, one after another, starting at time `t = now`. Before each attempt, at its time `t`, the gateway asks in this order, and the first yes refuses the attempt:

1. Is the tool's breaker open at `t`? Then `circuit_open`.
2. Does the tenant have a bucket with no token at `t`? Then `tenant_limit`.
3. Does the tool have a bucket with no token at `t`? Then `tool_limit`.

A refused attempt takes no token from any bucket and does not change the breaker, and the call ends with the reason as its result. Otherwise the attempt is made: it takes one token from each of the call's buckets, gets its outcome, and the breaker counts it. Every attempt is a real call to the tool, so retries count against the limits and the breaker like first attempts. Then:

- an `"ok"` ends the call with the result `ok`;
- an `"error"` on attempt `maxAttempts` ends it with `retries_exhausted`;
- after any other `"error"`, the call waits and tries again. The wait after the `k`-th failed attempt is `min(baseDelay * 2^(k - 1), maxDelay)` seconds, so it doubles from `baseDelay` until it reaches the cap `maxDelay`, and the next attempt's time is `t` plus the wait.

The row has the result, the number of attempts made (refused ones do not count) and the end, the time of the last attempt made, or of the refused one. A call refused at once has 0 attempts and ends at `now`. A call can run past `now`, so the next call starts no earlier than the end of the one before it.

### Example 1

<!-- case: ex7 -->

Tenant `t1` has a quota of 2 calls that never refills, and `search` allows one call per second. After the first call, `search` is empty: `t2`, which has no limit of its own, is refused with `tool_limit`, and so is `t1`, which keeps its last token because a refused attempt takes nothing. At second 1 `search` has a token again and `t1` spends its last one. At 2 `t1` is refused with `tenant_limit`, and the token `search` gained is left for `t2`.

### Example 2

<!-- case: ex8 -->

Retries wait 1, 2, then 3 seconds, where the doubling would give 4. The first call fails at 0 and 1 and succeeds at 3, which sets the count of failures back to 0. The second call fails at 5, 6 and 8: three failures in a row open the breaker at 8, for 10 seconds, so its fourth attempt, due at 11, is refused: the call made 3 attempts and ended at 11 with `circuit_open`. The breaker is still open at 17 and half-open at 18, when a trial succeeds and closes it.

## Constraints

- At most 400 method calls per test, and at most 200 submitted jobs.
- `0 <= now <= 10^9`, and every `now` given after a `call` is at least that call's end.
- `1 <= step <= 1000`, and an `output` has 1 to 100 printable ASCII characters.
- `0 <= minWorkers <= maxWorkers <= 1000`, `1 <= jobsPerWorker <= 1000`, `0 <= upCooldown, downCooldown <= 10^6`, `1 <= alertBacklog <= 1000`.
- `1 <= capacity <= 10^6` and `0 <= refillPerSecond <= 10^6`. `1 <= maxAttempts <= 10`, `1 <= baseDelay <= maxDelay <= 10^6`. `1 <= failureThreshold <= 100` and `1 <= openSeconds <= 10^6`.
- `outcomes` has at least `maxAttempts` entries, at most 10, each `"ok"` or `"error"`.

## Follow-ups

- A worker that pauses past the end of its lease and then writes to a system that knows nothing of leases, such as an outside service, is not stopped by `checkpoint`. How would a number that grows with every claim, sent with each write, let that system refuse the late write?
- A job that crashes every worker that runs it comes back forever. How would you count the claims of a job and move it aside after too many, and what should its owner see?
- When the controller scales down, which workers should stop, and what should a stopping worker do with the job it holds, so that the next worker does not wait for the whole lease?
- The cooldown ignores what the backlog did in the meantime. What changes if a scale-down instead uses the highest `desired` seen over the last `downCooldown` seconds?
- Many workers that fail at the same moment retry at the same moments too. How would you spread their retries in time and still test the gateway deterministically?
- A half-open breaker here lets one trial through, and the gateway serves one call at a time. What must change when many calls arrive at once while the breaker is half-open?

## Hints

### Hint 1

Start with one small record per job: whether it is done, which worker its lease was last given to, and when that lease ends. Keep the records in a map from job id to record. A map that remembers the order of insertion (a Python `dict`, a TypeScript `Map`) also keeps the queue's order for free, so a claim is a walk over the map from the start. "Is the lease active?" is then one comparison, `now < end`.

### Hint 2

Never change a lease on a timer: nothing runs between calls. A lease that ends at 18 is over for any question asked at 18 or later, so compute "active" from `now` whenever you need it, in one helper that `claim`, `heartbeat`, `complete` and `jobState` all use. A second helper, "the job, if this worker holds it", serves `heartbeat`, `complete` and `checkpoint`.

### Hint 3

In `claim`, two things are looked for in one walk: a job the worker already holds, which wins, and the first job that is free. Write down what "free" means (not done, no active lease) before you write the loop.

### Hint 4

Put the saved steps in the job's record, as a list of outputs, and never in anything keyed by the worker. Then the number of saved steps is the list's length, a duplicate is `step <= length`, and the only write that appends is `step == length + 1`. Check the lease before anything else.

### Hint 5

Keep a running count of the jobs done, so the backlog is the jobs submitted minus the jobs done. Round up with integers: `(backlog + per - 1) // per` in Python, `Math.ceil(backlog / per)` in TypeScript. Keep the time of the last change as "none" until the first change, not as 0, or the first change waits for a cooldown that never started.

### Hint 6

Write a bucket as a small object with two operations: "do you have a token at time `t`?", which refills first, and "take one". Refilling depends only on the time, so looking at a bucket early changes nothing. In a call, ask every bucket before you take from any.

### Hint 7

Write a call as a loop over attempts with a time `t` that starts at `now` and only grows. Compute the breaker's state at `t` from the time it opened rather than storing "half-open": then the breaker needs only a count of failures and an opening time, which is empty while it is closed.
