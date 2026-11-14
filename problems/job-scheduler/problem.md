# Rate-Limited Job Scheduler

## Statement

Build `JobScheduler`, which decides which job starts next for a shared pool of workers. Jobs belong to tenants (the teams or customers who submit them) and carry a priority. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

The scheduler never runs anything itself. Callers ask it for the next job to start and later report how that job ended. Every method takes the current time as its first argument, `timestamp`, in milliseconds; nothing reads a clock.

## Input

- `JobScheduler()`: creates a scheduler with no jobs.
- `timestamp`: the time of the call. Within one test, timestamps strictly increase from call to call.
- `jobId`: a job identifier, unique for the whole lifetime of the scheduler.
- `tenant`: the tenant a job belongs to.
- `priority`: an integer; a larger number means more urgent.
- Each level's section describes the methods it adds and their other parameters.

## Output

Each method returns what its level describes. Failure is reported with a sentinel, never with an exception: `""` for strings, `false` for booleans and `-1` or `0` for numbers, as each method states.

## Level 1: Priority queue of jobs

- `submit(timestamp, jobId, tenant, priority)`: adds a job in status `"QUEUED"`. Returns `false` and changes nothing when the id was used before, whatever happened to that job.
- `runNext(timestamp)`: starts the queued job with the highest priority; among equal priorities, the one submitted first. The job's status becomes `"RUNNING"` and its id is returned. Returns `""` when no job can start.
- `status(timestamp, jobId)`: the job's status, or `""` for an unknown id.
- `queued(timestamp)`: the number of jobs in status `"QUEUED"`.

### Example 1

<!-- case: ex1 -->

`b` and `c` share priority 5, and `b` was submitted first, so it starts first; `a` has priority 1 and starts last. Reusing the id `a` fails even for another tenant. Once all three run, there is nothing left to start.

## Level 2: Per-tenant rate limits

- `setRateLimit(timestamp, tenant, limit, windowMs)`: from now on, a job of `tenant` may start at time `t` only if fewer than `limit` of the tenant's jobs started at times in the window `t - windowMs < s <= t`. Every start of the tenant counts, including starts before the limit was set. A new limit for the same tenant replaces the old one. Tenants without a limit are unlimited.
- `runNext` skips a job whose tenant is at its limit and starts the best job that is allowed; skipped jobs keep their place in the queue.

### Example 1

<!-- case: ex2 -->

`acme` may start one job per 100 ms. `x1` starts at 10, so at 20 `x2` must wait and the lower-priority `y1` of `zeta` starts instead. At 30 nothing is allowed. At 110 the start at 10 has left the window, because `110 - 100 < 10` is false, so `x2` starts.

## Level 3: Completion and retries

- `complete(timestamp, jobId)`: a running job finished; its status becomes `"DONE"`. Returns `false` and changes nothing when the job is not running.
- `setRetryPolicy(timestamp, tenant, maxRetries, baseDelayMs)`: the tenant's jobs may be retried up to `maxRetries` times. The policy in force when a job fails decides; tenants without a policy never retry.
- `fail(timestamp, jobId)`: a running job failed. Count this failure as the job's `k`-th. When `k <= maxRetries`, the job returns to `"QUEUED"` with its priority and its original place among equal priorities, but may not start before `timestamp + baseDelayMs * 2^(k-1)`; that time is returned. Otherwise the job's status becomes `"FAILED"` and the result is `0`. Returns `-1` and changes nothing when the job is not running.
- A retry is a start like any other and counts against the tenant's rate limit.

### Example 1

<!-- case: ex3 -->

With two retries and a base delay of 100, the first failure at 10 delays the job to 110 and the second at 120 delays it by 200, to 320. Before 110 the job is queued but cannot start. The third failure exceeds the retries, so the job is `FAILED` and `fail` returns `0`.

## Level 4: Dependencies and cancellation

- `submitAfter(timestamp, jobId, tenant, priority, dependsOn)`: like `submit`, but the job may start only once every job in `dependsOn` is `"DONE"`. Returns `false` and changes nothing when the id was used before or any dependency is unknown, `"FAILED"` or `"CANCELLED"`. An empty `dependsOn` behaves like `submit`.
- `cancel(timestamp, jobId)`: cancels a `"QUEUED"` job, including one waiting for a retry, and then every queued job that depends on a cancelled job, directly or through other jobs. Their status becomes `"CANCELLED"`. Returns the number of jobs cancelled, or `0` when the job is not queued.
- When a job becomes `"FAILED"`, the queued jobs that depend on it, directly or not, are cancelled in the same way.

### Example 1

<!-- case: ex4 -->

`test` outranks `build` but must wait for it, so `build` starts first and nothing else can start while it runs. Once `build` is done, `test` starts. Cancelling `deploy` cancels just that job, so nothing is left when `test` completes.

## Constraints

- At most 1000 calls per test.
- `1 <= timestamp <= 10^9`, strictly increasing within a test.
- `-10^6 <= priority <= 10^6`.
- `1 <= limit <= 1000` and `1 <= windowMs <= 10^9`.
- `0 <= maxRetries <= 10` and `1 <= baseDelayMs <= 10^6`.
- `dependsOn` has at most 10 distinct ids, none equal to `jobId`.
- Ids and tenants are 1 to 10 lowercase letters or digits.

## Follow-ups

- How would `runNext` avoid rescanning blocked jobs when one tenant floods the queue?
- What would change if several workers called `runNext` at the same moment from different threads?

## Hints

### Hint 1

Keep the queued jobs ordered by (priority descending, submission number ascending). Level 1 is then "take the first one".

### Hint 2

Later levels add reasons a job cannot start yet. Walk the ordered queue and start the first job that passes every check: retry time, dependencies, tenant limit.

### Hint 3

Each tenant's start times only grow, so a sorted list of them answers "how many starts in the window" with one binary search. Keep a list of dependents on every job, so a cancellation or final failure can walk forward through them.
