# Rate-Limited Job Scheduler: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| ordered-queue | optimal | O(q (d + log s)) per runNext; O(q) per submit, retry or cancel | O(j + s) | default answer; every new rule is one more check in `canStart` |

Here `q` is the number of queued jobs, `d` the number of dependencies of a job, `s` the number of starts of one tenant, and `j` the number of jobs ever submitted.

## How the design grows level by level

| Level | New requirement | What the design adds |
|-------|-----------------|----------------------|
| 1 | Start the most urgent job | `jobs: id -> Job`, and `queue`, the queued jobs ordered by `(-priority, sequence)` |
| 2 | At most `limit` starts per tenant per window | `starts: tenant -> ascending start times`, and a window check in `canStart` |
| 3 | Completion, failure, retries with exponential backoff | `failures` and `notBefore` on `Job`, a `RetryPolicy` per tenant, and a retry that re-enqueues the job under its original order key |
| 4 | Dependencies and cascading cancellation | `dependsOn` and `dependents` on `Job`; a dependency check in `canStart`; a walk over `dependents` for `cancel` and for final failures |

The shape that carries all four levels is "an ordered queue plus one predicate". `runNext` never changes after level 1: it walks the queue in order and starts the first job for which `canStart` holds. Each level that introduces a reason to wait (a tenant over its limit, a retry delay, an unfinished dependency) adds one clause to `canStart`, and nothing else in `runNext` moves.

## Approach: ordered-queue (Ordered queue scanned for the first eligible job)

### Intuition

Priority order and eligibility are independent. The order of the queue never changes while a job waits, because priority and submission number are fixed, so the queue can stay sorted at all times. Eligibility does change with time and with other jobs, so it is evaluated when `runNext` asks, by walking the queue from the front. A blocked job is simply passed over and keeps its place, which is exactly what the statement requires.

### Algorithm

1. `submitAfter` (and `submit`, which is `submitAfter` with no dependencies): reject a known id or a dependency that is unknown, failed or cancelled. Otherwise create the job with `sequence` = number of jobs so far, register it in each dependency's `dependents`, and insert it into the queue.
2. `runNext(t)`: walk the queue in order. For the first job with `canStart(job, t)`, remove it from the queue, mark it `RUNNING`, append `t` to its tenant's start times and return its id. Return `""` if none passes.
3. `canStart(job, t)`: `job.notBefore <= t`; every dependency is `DONE`; and when the tenant has a limit, the number of its start times greater than `t - window` is below `limit` (one binary search, since start times are ascending).
4. `complete`: a running job becomes `DONE`.
5. `fail`: a running job counts the failure `k`. When `k <= maxRetries` under the tenant's current policy, set `notBefore = t + baseDelay * 2^(k-1)`, put the job back in the queue, and return `notBefore`. Otherwise mark it `FAILED`, cancel its dependents, and return `0`.
6. `cancel`: a queued job is removed and marked `CANCELLED`, then its dependents are cancelled; return 1 plus their count.
7. Cancelling dependents: walk the `dependents` lists with a stack. Each job still `QUEUED` is removed from the queue, marked `CANCELLED`, counted, and its own dependents are pushed. Jobs already cancelled are skipped, so a job reachable through two paths counts once.

### Correctness

Invariant: `queue` holds exactly the jobs whose status is `QUEUED`, sorted by `(-priority, sequence)`. Every transition into `QUEUED` (`submitAfter`, a retry) inserts the job, and every transition out of it (`runNext`, `cancel`, a cascade) removes it. Because the walk in `runNext` visits jobs in that order and stops at the first eligible one, the job it starts is the most urgent eligible job, ties going to the earliest submission. A retried job reuses its own `sequence`, so it returns to its original place among equal priorities.

The rate check counts starts in `(t - window, t]`: the start times are strictly ascending (at most one start per call, and timestamps increase), so the count is the length minus the position of the first time greater than `t - window`.

A queued job's dependencies are never `FAILED` or `CANCELLED`: `submitAfter` rejects those, and when a dependency later reaches either state, the cascade cancels the job. A dependency can only reach those states while the dependent is still queued, because the dependent cannot start before the dependency is `DONE`, and a `DONE` job never changes again. So the cascade only ever needs to look at `QUEUED` jobs, and `cancel` never has to touch a running job.

### Complexity

- Time: O(q (d + log s)) per runNext; O(q) per submit, retry or cancel — `runNext` may check every queued job, each check costing `d` status lookups and one binary search. Inserting into or removing from a sorted array is O(q) in Python and TypeScript (O(log q) with Java's and Kotlin's `TreeSet`). A cascade visits each cancelled job once.
- Space: O(j + s) — every job and its dependency lists are kept for status queries, plus every start time for the rate windows.

### Trade-offs

- A binary heap gives O(log q) pushes and pops but cannot skip a blocked job without popping it; you end up popping blocked jobs into a side list and pushing them back, which costs the same O(q log q) in the worst case and is harder to get right. The sorted queue keeps "skip and keep its place" trivial.
- The worst case is a flood of blocked jobs at the front, for example one tenant over its limit with thousands of urgent jobs. Per-tenant queues with a heap of tenant heads, or parking blocked jobs until their earliest possible start, fix that; mention them as the scaling follow-up.
- Keeping every start time makes the rate check exact even when a later `setRateLimit` widens the window. A ring buffer of the last `limit` starts is O(limit) memory per tenant but would have to be rebuilt when the limit changes.
- Tracking a count of unfinished dependencies per job (decremented on `complete`) makes the dependency check O(1) instead of O(d); with at most 10 dependencies the direct check is simpler.

### Pitfalls and edge cases

- The window is half-open: a start exactly `windowMs` ago no longer counts.
- Starts before `setRateLimit` count; the limit restricts the future but judges it with the full history.
- A retry keeps the job's priority and submission number; giving it a new sequence would push it behind later equal-priority jobs.
- The policy in force at the time of the failure decides, not the one at submission.
- `fail` distinguishes three results: the retry time, `0` for a final failure and `-1` when the job was not running.
- A diamond of dependencies must not count the shared descendant twice in a cascade.
- `cancel` of a running or finished job returns `0` and leaves its dependents alone.

### Language notes

- Python: `bisect.insort(queue, job, key=...)` and `bisect_right(..., key=...)` (Python 3.10 and later) keep the queue sorted by a `(-priority, sequence)` tuple; insertion into a list is O(q).
- TypeScript: no sorted collection exists, so the reference binary-searches the insertion point and uses `splice`. Statuses are a string-literal union type, which keeps the type checker honest without an `enum` (enums are not erasable syntax).
- Java: a `TreeSet<Job>` with a comparator on immutable fields is safe to remove from; mutating a field the comparator reads while the job is in the set would corrupt it. `Collections.binarySearch` returns `-(insertion point) - 1` for a missing value, so the first time after the threshold is `found + 1` or `-(found + 1)`.
- Kotlin: the same `java.util.TreeSet` with `compareByDescending<Job> { it.priority }.thenBy { it.sequence }`, an `enum class` for statuses, and `List<Long>.binarySearch` with the same return convention as Java's.
- Go: `sort.Search` finds the first queued job that sorts after the one being placed, which is the insertion point and, minus one, the position to remove; `slices.Insert` and `slices.Delete` do the shifting. The zero `retryPolicy` is the "no retries" default, so a missing tenant needs no special case. `baseDelayMs << (failures - 1)` is the doubling delay.
- Rust: jobs refer to each other (dependencies, dependents, the queue) by position in one `Vec<Job>`, which is also the submission sequence, because shared mutable `Job` objects would need `Rc<RefCell<..>>`. `partition_point` plays the part of `bisect_right` and `insort`. Statuses are a `Copy` enum with a `name()` for the output strings.
