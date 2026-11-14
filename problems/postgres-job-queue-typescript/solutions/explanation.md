# Postgres Job Queue (TypeScript): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | per request | per request | default answer: one locking statement claims a job, and every finish is one conditional update fenced by the attempt number |

## How the project grows level by level

| Level | New requirement | What the code adds |
|-------|-----------------|--------------------|
| 1 | Enqueue, claim each job once under bursts, complete | `0002_claims.sql`, `newJob` in `src/requests.ts`, `enqueue` and `job` in `src/jobs.ts`, `claim` and `complete` in `src/workers.ts` |
| 2 | Claims that run out, and late completes refused | Nothing new to store: `run_after` already holds when a claim runs out, so the claim's `run_after <= now` takes expired claims back, and the complete's `attempts = $2 AND run_after > now` refuses late ones. `visibility_seconds` sets the time |
| 3 | Retries with backoff, dead letters | `0003_retries.sql`, `fail` with its `FAIL` statement, `BURY_EXPIRED` before each claim, and `deadLetters` |
| 4 | Priorities, fair shares between tenants, `urgent` migrated | `0004_priorities.sql`, and the `ORDER BY` of `CLAIM` |

## Approach: reference (Claim in one locking statement, and fence every finish with the attempt number)

### Intuition

A queue is a race with a hundred runners. Every worker that asks for a job wants the same one, the oldest, and a claim that reads the oldest waiting job and then marks it claimed gives it to every worker that read before the first write landed. The decision has to happen where the race is settled, in the database, and in one statement.

`SELECT ... FOR UPDATE SKIP LOCKED` is made for this. `FOR UPDATE` locks the row it returns, and `SKIP LOCKED` passes over rows another transaction has locked instead of waiting for them. Twenty claims at once each lock a different job, and none waits for another. Put it in the subquery of the `UPDATE` that marks the job claimed, and the read and the write are one statement: by the time a claim commits, the row says claimed, and no claim can lock it again.

A claim that runs out is the second idea, and it needs no timer. Each job keeps one time, `run_after`, meaning "not claimable before". A queued job's is when it may run; a claimed job's is when its claim runs out. Every claimable job then matches one condition, `run_after <= now`, whether it was never claimed or its worker went silent. No job sweeps expired claims, and none can be forgotten.

The worker that went silent may wake up. Its complete must not finish a job another worker now holds, and must not finish one nobody holds either, since a claim may take it at any moment. So every finish names the attempt its claim gave, and is one conditional `UPDATE`: the job must be claimed, by that attempt, and the claim must not have run out. Each claim raises the attempt, so the number works as a fencing token: a late worker names a number that is no longer the job's, and its update matches no row.

Retries reuse the same time. A failed attempt sets `run_after` to now plus the backoff, so the job waits without anything watching it. A job whose attempts are used up never matches the claim again: a fail of its last attempt marks it dead in the same statement, and a last claim that ran out is buried by the next claim on its queue, under the same row lock, so it is buried once.

Priorities and fairness are only the order the claim takes candidates in: priority first, then the tenant with the fewest running claims, then the job enqueued first. `SKIP LOCKED` walks that order and takes the first row nobody holds.

### Say it out loud

"Claiming is the race, so I make it one statement: an `UPDATE` that sets the job claimed, raises its attempts and sets when the claim runs out, on the row a subquery picks with `ORDER BY seq LIMIT 1 FOR UPDATE SKIP LOCKED`. Concurrent claims skip each other's locked rows, so each gets a different job and none waits.

"Each job keeps one `run_after`: when a queued job may run, or when a claimed job's claim runs out. So a job is claimable when it is queued or claimed with `run_after` at or before now, and a crashed worker's job comes back by itself. Completes and fails name their attempt and update only where the job is claimed, by that attempt, before `run_after`: a late worker's update matches nothing, and I answer 409.

"A fail either requeues with `run_after` set to now plus the backoff, doubled per attempt and capped at an hour, or marks the job dead and records it in the dead letters, in one statement. A last claim that ran out is buried by the next claim on its queue, which locks it with `SKIP LOCKED` first so two claims never bury it twice.

"For level 4 the claim orders by priority, then by how many claims the job's tenant is running in that queue, then by `seq`. The migration adds `priority` with a default of 5, raises the urgent jobs to 9, and drops the flag."

### Algorithm

1. `POST /queues/{queue}/jobs`: check the body against the statement's rules, then insert with `run_after` set to now, `ON CONFLICT (id) DO NOTHING`. No row inserted means the id was taken: 409 `job_exists`.
2. `POST /queues/{queue}/claim`, in one transaction: first bury the queue's jobs whose last attempt's claim ran out, each locked with `FOR UPDATE SKIP LOCKED`, marking them dead and inserting them into `dead_letters` with `claim expired`. Then run `CLAIM`: on the claimable job first in claim order that no other transaction holds, set `status = 'claimed'`, `attempts = attempts + 1` and `run_after = now + visibility`. No row: 204.
3. `POST /jobs/{id}/complete`: `UPDATE ... SET status = 'done' WHERE id = $1 AND status = 'claimed' AND attempts = $2 AND run_after > now`. No row updated: 404 if the job is unknown, 409 `stale_claim` otherwise.
4. `POST /jobs/{id}/fail`: the same condition. If this attempt was the last, set `dead` and insert the dead letter with the worker's error in the same statement; otherwise set `queued` and `run_after = now + least(backoff × 2^(attempt − 1), 3600)`.
5. `GET /jobs/{id}`: a claimed job whose `run_after` has passed reads as `queued`; a done or dead job reads `run_after` as `null`.
6. `GET /queues/{queue}/dead-letters`: the dead letters joined to their jobs, by the order they were inserted.

### Design

| File | Holds |
|------|-------|
| `migrations/0002_claims.sql` | `status`, `attempts` and `run_after` on `jobs`, `run_after` copied from `enqueued_at` for the jobs already waiting, and a partial index of claimable jobs by queue and `seq` |
| `migrations/0003_retries.sql` | `max_attempts` and `backoff_seconds` per job, `dead` as a status, and `dead_letters`, which references the job and records its error in the order jobs died |
| `migrations/0004_priorities.sql` | `priority` with a default of 5, the urgent jobs raised to 9, `urgent` dropped, and the claim's two indexes |
| `src/requests.ts` | The statement's field rules, as functions that answer a typed request or nothing |
| `src/jobs.ts` | `shown`, which turns a stored row into the job's answer at a moment, and `enqueue`, `job` and `deadLetters` |
| `src/workers.ts` | `CLAIM`, `BURY_EXPIRED`, `COMPLETE` and `FAIL`, and the routes that run them |
| `src/db.ts` | The pool, and `inTransaction`, which runs a claim's two statements on one connection |

The job keeps its row when it dies, so its id stays taken by the primary key and `GET /jobs/{id}` still finds it. `dead_letters` holds only what the death adds: the error and the order. A unique key on its `job_id` is a second guard against burying a job twice.

Every time comes from `now()` in `src/clock.ts` and goes to the query as a parameter. That is what makes the frozen clock work, and it is a good habit beyond it: one request uses one "now" for every comparison it makes.

### Correctness

Two claims never take the same job: each locks its row before it updates it, a locked row is skipped by every other claim until the holder commits, and once it commits the row is claimed with a `run_after` in the future, which no claim matches. A claim never comes back empty while a job it could take waits: `SKIP LOCKED` moves on to the next row instead of giving up, so a claim finds nothing only when every claimable row is held by another claim. A complete or fail updates only a row that is claimed by the attempt it names with the claim still running, and Postgres re-checks that condition after waiting for any concurrent update of the row, so of many finishes at once one updates it, and none updates a job a later claim took. A job is buried by the one claim that locked it first, inside the transaction that marks it dead, so it enters the dead letters once. A failed attempt that was the last marks the job dead in the same update that checks the attempt, so no claim can take it in between. The migrations copy `enqueued_at` and `urgent` into their new columns before anything is dropped, in one transaction each.

### Complexity

- Time: per request — a claim reads the claimable rows of one queue through the partial index, and at level 4 counts each candidate tenant's running claims through the second index; every other route touches one row
- Space: per request — one row per job, and one per dead letter

### Trade-offs

`FOR UPDATE SKIP LOCKED` trades strict order for throughput: when the first job is locked by a claim that has not committed yet, the next claim takes the second one. A queue that must run its jobs one at a time in order needs a lock that waits, or one queue per ordering key.

Keeping claims in the job row is simple and makes a claim that runs out free. The price is that the claim's time and the job's next run share one column, so a job view has to read the status to know which one it holds. A separate claims table would keep a history of attempts, which an operator debugging dead letters would want.

A claim that runs out counts as an attempt. That is what stops a job that crashes its worker from being claimed forever, and it means a job that is merely slow uses its attempts up too: a worker with a long job must ask for a long enough claim. Real queues add a heartbeat that extends a claim; this one leaves it to the follow-ups.

The level 4 fairness count runs a subquery per candidate job. It is exact against committed claims and cheap at this size, and two claims at the same moment cannot see each other's uncommitted claim, so under a burst fairness is approximate while exclusivity stays exact. A counter per tenant would be faster and would need its own updates on every claim, complete, fail and expiry, which is a race of its own.

Polling for work costs a query per worker per poll. `LISTEN` and `NOTIFY` let idle workers wait for an enqueue instead, and the claim stays exactly as it is.

### Pitfalls and edge cases

**Wrong approaches.** Each fails a hidden case, and the failure names what it did. Parallel cases send their burst at once, behind a barrier, and repeat three times from a fresh database, so a race that loses only now and then still fails. None of these are stored as solutions: a pass of a parallel case finds no race and proves none, and the broken solutions are checked by hand until the grader's D7 runs them.

| What it does | Why it is wrong | What catches it |
|--------------|-----------------|-----------------|
| Reads the first waiting job, then updates it to claimed by its id | Every claim of the burst reads the same job before any writes, so several get it | `v6`, `h20`, `h21`, each on its first run: `20 requests at once: expected 5 to answer 200 and 15 to answer 204; 16 answered 200 and 4 answered 204`, and `v6`'s `8 answered 200; after POST /queues/reports/claim: status: expected 204, got 200`, since a job nobody got is still waiting |
| Reads the first waiting job, then updates it only where it is still claimable | No job is handed out twice, but the claims that lose the race come back empty while other jobs wait | `v6`, `h21`: `10 requests at once: expected 10 to answer 200; 4 answered 200 and 6 answered 204` |
| Runs `BEGIN`, the `FOR UPDATE` and `COMMIT` through `pool.query` | Each query may take another connection, so the lock is released before the update | `h20`, like the first row |
| Claims only `queued` jobs, and completes without asking whether the claim ran out | A worker that crashes keeps its job for good, and its late complete still counts | 10 of the 15 level 2 cases: `v8` `status: expected 200, got 204`, `v9` `status: expected 409, got 200`, `h31` `step 3 POST /queues/reports/claim: status: expected 200, got 204`, and `h39` `10 requests at once: expected 3 to answer 200 and 7 to answer 204; 2 answered 200 and 8 answered 204` |
| Completes a job by its id, without the attempt | A worker whose claim ran out finishes the job another worker holds; if that worker then fails, the job is lost | `v9`, and `h31` at its fourth step |
| Checks the attempt but not that the claim is still running | A worker past its claim completes a job any claim may take at that moment | `h30`, `h57` |
| Reads the job's attempt and status, then updates it, on a complete or fail | Ten finishes at once all see the claim current | `h22`, `h40`, `h67`, which expect 1 to answer 200 and 9 to answer 409 |
| Requeues every failed attempt, with no limit | A job that always fails is retried forever | `h53`, whose fifth step expects `dead` |
| Limits fails but not claims that run out | A job that crashes its worker every time is claimed forever | `h54`, `h55` |
| Applies a backoff of `backoff_seconds × attempt`, or no cap | The second attempt happens to match; the third and the cap do not | `h51`, `h52` |
| Buries an expired last attempt with a plain read before the insert | Two claims at once both find it, and the second insert fails or lists it twice | `h68` |
| Uses Postgres's `now()` in the queries | The cases' times come from `CLOCK_NOW`; the real time is earlier, so claims expire at once or never | `v2`, `v8`, `v12`: times that are not the frozen clock's |
| Migration that adds `run_after` with `DEFAULT now()` | The waiting jobs get the real time, not the time they were enqueued | `v7`, `h19` |
| Level 4 migration that ignores `urgent` | The urgent jobs are served at 5, in their turn | `v19`, `h82`, `h83` |
| Level 4 migration that adds `priority` with a default of 0, then sets the default to 5 | The jobs already there keep 0, and every new job overtakes them | `h81` |
| Counts a tenant's jobs that are not done, or every claim ever made, as running | A tenant is held back for jobs nobody is running | `h86`, `h87`, `h91` |

**Edge cases.**

- A claim of 0 seconds has run out by the next request, and reads as `queued` with `run_after` at the moment it ran out (`v8`, `h33`).
- A complete from a claim that ran out is refused even when nobody claimed the job since, and the job can then be claimed again (`h30`, `h32`).
- A job whose claim ran out keeps its place in the queue, and so does a retried job (`h34`, `h70`).
- A claim that buries a job goes on to the next one in the same request (`h55`).
- A dead job's id stays taken, and a dead job cannot be completed (`h66`, `h71`).
- The order of claims is the order of enqueues, not of ids (`h25`).
- A payload comes back as it was sent, nested objects and lists included (`h24`).
- The hidden jobs are in `jobs` before your migrations run, and the cases ask for them by id and by queue (`h18`, `h19`, `h81`, `h82`, `h83`).
