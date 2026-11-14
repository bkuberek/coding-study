# Postgres Job Queue (TypeScript)

## Statement

A service generates reports in the background. Producers enqueue a job for each report, and workers claim one, run it, and say how it went. The queue lives in Postgres, beside the rest of the service's data. On a quiet day, one worker takes one job. On a busy one, twenty workers ask for work in the same instant, and a queue that reads the oldest waiting job and then marks it taken hands the same report to several of them. A worker that crashes holds its job forever unless its claim runs out. A report that fails every time must stop retrying somewhere. And one tenant that enqueues a thousand reports must not make every other tenant wait behind them.

Build the queue in levels, on Postgres. It enqueues and hands each job to exactly one worker however many ask at once, takes a job back when its claim runs out and refuses the late answer of the worker that lost it, retries failures with a growing backoff until a dead-letter table, and finally serves jobs by priority and gives every tenant its turn, with a migration that carries the first version's jobs into the new order. `cstudy` runs your app and its database in a Docker sandbox and judges it by what it answers over HTTP, including bursts of requests sent at the same moment. The service, its tenants and their reports are invented.

**The clock is frozen.** Your app's "now" is `CLOCK_NOW` from its environment: `1803902400`, which is 2027-03-01 12:00:00 UTC. `now()` in `src/clock.ts` reads it. Use it for every time your app stores or compares, and pass it to your queries as a parameter: Postgres's own `now()` and `CURRENT_TIMESTAMP` read the real time, which the cases do not know. Since time does not pass, a claim of 0 seconds has run out by the next request and a claim of 30 seconds never runs out during a case, which is how the cases make a claim run out without waiting. A real service would read its real clock, and nothing else would change.

## Input

HTTP requests with JSON bodies: `POST /queues/{queue}/jobs` to enqueue, `GET /jobs/{id}` to read a job, `POST /queues/{queue}/claim` to claim one, and `POST /jobs/{id}/complete` to finish it. Each level says what it adds.

## Output

JSON, always with `Content-Type: application/json`, except a 204, which has no body. A refusal is `{"error": "<code>"}`, with the codes each level names. Times are in UTC, to the second, as `"2027-03-01T12:00:30Z"`, which is what `timestamp()` in `src/clock.ts` writes. Your app reads its port from `PORT` and listens on all interfaces inside the container (`0.0.0.0`), and `GET /health` answers 200 once it is ready.

## Project

`cstudy start` copies the service into `projects/postgres-job-queue-typescript/`, and `cstudy dev` runs it with its database. Node runs the files by stripping their types, so write no `enum`, no `namespace` and no constructor parameter properties, and import your own files with their `.ts` extension.

- `src/server.ts`: the routes, and where the server starts. It enqueues and answers `GET /jobs/{id}` from the database already, as the first version did, and answers 501 to claims and completes.
- `src/clock.ts`: `now()`, the frozen clock, and `timestamp()`, which writes a time as the answers do.
- `src/db.ts`: the connection pool, from `DATABASE_URL`.
- `migrations/`: the schema, as plain SQL files that node-pg-migrate applies in name order. `0001_baseline.sql` is the problem's and stays as it is; add yours after it, `0002_...sql` and on. Each file starts with `-- Up Migration`, and node-pg-migrate runs each in a transaction of its own and records it in `pgmigrations`.
- `scripts/reset.ts`: puts the database back as it was after your migrations, before a case that starts fresh. You should not need to change it.
- `tests/`: your tests, run by `cstudy test`.
- `.env`: what your app reads, written by `cstudy start` from the problem's settings. Your app's environment already holds it.

`cstudy test` starts a sandbox, applies the migrations, runs your tests beside the app, and then the visible cases of your open levels. `cstudy submit` grades every case of the open levels, hidden ones included, and opens the next level when they all pass. Each submission grades the earlier levels again, so a later change must keep their answers. To look at the data yourself while `cstudy dev` runs, `docker ps` shows its database container, whose name ends in `-db-1`, and `docker exec -it <that name> psql -U app` opens a shell on it.

### The data you start with and the data you do not see

`0001_baseline.sql` creates `jobs`, the table the first version enqueued into:

| Column | Holds |
|--------|-------|
| `id` | The job's id, the primary key |
| `seq` | A number that grows with each insert, so it orders jobs by when they were enqueued |
| `queue`, `tenant`, `payload` | What the producer sent |
| `urgent` | A flag an earlier producer set on some jobs. Nothing reads it yet; level 4 does, so keep it |
| `enqueued_at` | When the job arrived |

Three jobs are waiting in it, in the queue `invoices`:

| Id | Tenant | Payload | Urgent | Enqueued at |
|----|--------|---------|--------|-------------|
| `inv-1001` | `acme` | `{"invoice": 1001}` | no | 2027-02-28 09:00:00 |
| `inv-1002` | `birch` | `{"invoice": 1002}` | no | 2027-02-28 09:10:00 |
| `inv-1003` | `acme` | `{"invoice": 1003}` | yes | 2027-02-28 09:20:00 |

Every job already in `jobs` is waiting: never claimed, and claimable since the moment it was enqueued. Your migrations must keep them so, and the rest of the schema is yours to design. The cases never name a table: they ask your API.

When `cstudy submit` grades, it applies the baseline, then adds hidden jobs to `jobs`, and only then applies your migrations, so they run on a table that holds rows you never saw, as a migration in production does. Job ids and queue names that start with `x-` are reserved for those rows. A migration that loses them, or that gives them a time or a priority they did not have, fails the cases that ask for them. Grading also applies your migrations to an empty database, which must work too.

A case that starts fresh gets the database as it was right after your migrations, and your app started again.

## Level 1: Enqueue and claim

`POST /queues/{queue}/jobs` enqueues a job:

```json
{"id": "r1", "tenant": "acme", "payload": {"report": "sales", "month": "2027-02"}}
```

| Field | Rule |
|-------|------|
| `{queue}` | 1 to 32 lowercase letters, digits or `-`. A queue exists as soon as a job names it |
| `id` | The job's id, chosen by the producer: 1 to 64 letters, digits, `-` or `_`. Unique across every queue, forever |
| `tenant` | The account the job is for, by the same rule |
| `payload` | A JSON object, kept and given back as it was sent |

It answers 201 with the job, and `GET /jobs/{id}` answers 200 with the same shape:

```json
{"id": "r1", "queue": "reports", "tenant": "acme", "payload": {"report": "sales", "month": "2027-02"},
 "status": "queued", "attempts": 0, "run_after": "2027-03-01T12:00:00Z"}
```

| Field | What it says |
|-------|--------------|
| `status` | `queued`, waiting to be claimed; `claimed`, held by a worker; `done`, completed |
| `attempts` | How many times the job was claimed |
| `run_after` | When the job may next be claimed. For a queued job, when it was enqueued; for a claimed job, when its claim runs out; `null` once it is done |

`POST /queues/{queue}/claim`, with the body `{}`, claims the queue's waiting job that was enqueued first, and answers 200:

```json
{"id": "r1", "tenant": "acme", "payload": {"report": "sales", "month": "2027-02"},
 "attempt": 1, "expires_at": "2027-03-01T12:00:30Z"}
```

`attempt` is the job's number of attempts once this claim counts. The claim holds the job for 30 seconds, until `expires_at`, and nobody else can claim it before then. With nothing to claim, it answers 204, with no body. The jobs waiting since the first version are claimed as any other, in the order they were enqueued.

`POST /jobs/{id}/complete`, with the attempt the claim gave, `{"attempt": 1}`, finishes the job: it answers 200 with the job, now `done`, and the job is never claimed again.

| Request | Status | Body |
|---------|--------|------|
| A body that is not a JSON object, or a queue name or field breaking its rule | 400 | `{"error": "invalid_request"}` |
| An enqueue with an id a job already has, whatever its status | 409 | `{"error": "job_exists"}` |
| `GET` or `complete` of a job nobody enqueued | 404 | `{"error": "unknown_job"}` |
| A `complete` that does not name the attempt of the claim holding the job now | 409 | `{"error": "stale_claim"}` |

`attempt` is a whole number from 1. A request is checked in the order of this table.

Workers claim at once, so the cases send bursts of up to 20 claims at the same moment, and judge how many got a job and what is left. However the claims interleave, no job goes to two workers, and no claim comes back empty while a job it could take is waiting. Reading the first waiting job and then marking it claimed is the bug: between your read and your write, every other claim read the same job. `SELECT ... FOR UPDATE SKIP LOCKED` locks the row it returns and passes over rows other transactions have locked, so each claim gets a job no other claim holds; put it in the `UPDATE` that marks the job claimed, and the read and the write are one statement. A conditional `UPDATE ... WHERE status = 'queued'` after a plain read hands no job out twice, but the claims that lose the race come back empty while other jobs wait. The same goes for a burst of completes, and of enqueues of one id: exactly one wins.

A burst's example shows the request it repeats and the statuses expected, which can come back in any order.

### Example 1

<!-- case: v1 -->

The job waits, never claimed, from the moment it was enqueued.

### Example 2

<!-- case: v2 -->

Job `r1` was enqueued first. The claim holds it for 30 seconds.

### Example 3

<!-- case: v3 -->

Nothing waits in `reports`.

### Example 4

<!-- case: v4 -->

`r1` and `r2` were enqueued in that order, and `r1` was claimed already.

### Example 5

<!-- case: v5 -->

`r1` was claimed, as attempt 1.

### Example 6

<!-- case: v6 -->

Jobs `p1` to `p5` wait, and eight workers ask at once: five get a job each, and three get nothing.

### Example 7

<!-- case: v7 -->

A job of the first version: waiting, and claimable since it was enqueued.

## Level 2: Claims that run out

A worker that crashes never completes its job. A claim now runs out: once its `expires_at` has passed, the job reads as `queued` again, with `run_after` at the moment the claim ran out, and any claim may take it, in its place in the queue, as the job's next attempt.

`POST /queues/{queue}/claim` takes `visibility_seconds`, how long the claim holds the job: a whole number from 0 to 3600, 30 when left out. A claim of 0 seconds has run out by the next request.

A complete must now come from the claim holding the job: it names that claim's attempt, before the claim runs out. A complete from an earlier claim, or from a claim that ran out even if nobody claimed the job since, is 409 `stale_claim` and changes nothing: the job stays with whoever holds it, or waits for the next claim. The attempt number is the fence: each claim raises it, so a worker that wakes up late names a number that is no longer the job's.

| Request | Status | Body |
|---------|--------|------|
| A `visibility_seconds` breaking its rule | 400 | `{"error": "invalid_request"}` |

### Example 1

<!-- case: v8 -->

`r1` was claimed for 0 seconds, so its claim has run out.

### Example 2

<!-- case: v9 -->

Attempt 1 claimed `r1` for 0 seconds, and attempt 2 claimed it since. The worker of attempt 1 answers late.

### Example 3

<!-- case: v10 -->

The same, and the worker of attempt 2 completes the job.

### Example 4

<!-- case: v11 -->

The claim asks for 120 seconds.

## Level 3: Retries and dead letters

`POST /jobs/{id}/fail`, with `{"attempt": 1, "error": "renderer crashed"}`, says an attempt failed. It comes from the claim holding the job, as a complete does, and is refused the same way. `error` is 1 to 200 characters.

Enqueue takes the job's retry policy:

| Field | Rule |
|-------|------|
| `max_attempts` | How many attempts the job gets: a whole number from 1 to 10, 3 when left out |
| `backoff_seconds` | How long the job waits after its first failed attempt: a whole number from 0 to 3600, 30 when left out |

A failed attempt sends the job back to the queue after a backoff that doubles with each attempt: `run_after` becomes now plus `backoff_seconds × 2^(attempt − 1)` seconds, and never more than 3600 seconds from now. The fail answers 200 with the job, `queued`, and no claim takes it before its `run_after`. A claim that runs out is a failed attempt too, with no backoff: the job may be claimed again at once, as at level 2.

A job dies when its last attempt is over. A fail of the attempt numbered `max_attempts` answers with the job `dead`, with `run_after` `null`. When the claim of a job's last attempt runs out, the job reads as `queued` until the next claim on its queue, which sends it to the dead letters instead of claiming it, with the error `claim expired`, and goes on to the next job. A dead job is never claimed again, and its id stays taken. So a job that fails every time, or that crashes every worker that takes it, stops after `max_attempts`.

`GET /queues/{queue}/dead-letters` answers 200 with the queue's dead jobs, in the order they died:

```json
[{"id": "r1", "tenant": "acme", "payload": {"report": "sales"}, "attempts": 1, "error": "renderer crashed"}]
```

`error` is what the last attempt's fail said, or `claim expired`. Keep them in a table of their own, so a dead job leaves the claimable rows and an operator can look at what died and why.

| Request | Status | Body |
|---------|--------|------|
| A fail whose `attempt` or `error` breaks its rule, or an enqueue whose `max_attempts` or `backoff_seconds` does | 400 | `{"error": "invalid_request"}` |
| A fail of a job nobody enqueued | 404 | `{"error": "unknown_job"}` |
| A fail that does not name the attempt of the claim holding the job now | 409 | `{"error": "stale_claim"}` |

### Example 1

<!-- case: v12 -->

`r1` was enqueued with the default backoff of 30 seconds, and attempt 1 failed.

### Example 2

<!-- case: v13 -->

The same job, waiting out its backoff until 12:00:30.

### Example 3

<!-- case: v14 -->

`r1` was enqueued with a backoff of 0, and attempt 1 failed.

### Example 4

<!-- case: v15 -->

`r1` was enqueued with one attempt, and it fails.

### Example 5

<!-- case: v16 -->

The same job, after its only attempt failed.

## Level 4: Priorities and fair shares

Enqueue takes `priority`, a whole number from 0 to 9, 5 when left out. A claim now takes the highest priority first. Within one priority, it takes from the tenant with the fewest claims running in this queue, claims that have not run out, and among that tenant's jobs and any tie, the job enqueued first. So a tenant who enqueued a hundred reports keeps one worker busy while the next tenant gets the next worker. A tenant's done jobs, jobs waiting out a backoff, and claims that ran out do not count against it.

The first version's `urgent` flag becomes a priority: write a migration that gives every job a priority, 9 for the jobs it marked urgent and 5 for every other. The hidden jobs are in `jobs` before it runs, and some of them are urgent.

| Request | Status | Body |
|---------|--------|------|
| An enqueue whose `priority` breaks its rule | 400 | `{"error": "invalid_request"}` |

### Example 1

<!-- case: v17 -->

`low` has priority 2 and `high` priority 8, enqueued in that order.

### Example 2

<!-- case: v18 -->

`acme` enqueued `a1`, `a2` and `a3`, then `birch` enqueued `b1`, and `a1` was claimed already.

### Example 3

<!-- case: v19 -->

The first version marked `inv-1003` urgent, so it has priority 9 and the other invoices 5.

## Constraints

- Postgres 17, through `DATABASE_URL`, with node-pg-migrate's plain SQL migrations. The baseline migration stays as it is.
- The clock is `CLOCK_NOW`, through `now()`: no case can see the real time.
- Bursts of up to 20 requests at once; a case has 10 s for all its requests.
- Every answer of a case that repeats must be right on every run: a race that loses one time in three still fails.
- Grading applies your migrations to a database that already holds hidden jobs, and to an empty one.

## Follow-ups

- A job runs for ten minutes, and a claim lasts one. How would a worker keep its claim alive, and what must that request refuse?
- Twenty workers poll an empty queue every second. What does that cost Postgres, and how would `LISTEN` and `NOTIFY` let them wait instead?
- A worker completes a job and then sends the email the job was for. What happens when it crashes between the two, and which of them must be idempotent?
- Every worker that retries at the same backoff retries at the same moment. What does jitter change, and how would you grade it?
- Done jobs stay in `jobs` forever. When would you delete them, and what must the cleanup never race with?
- Counting a tenant's running claims for each candidate job costs more as the queue grows. What would you keep instead, and what race would that counter have?
- An operator fixes the bug behind the dead letters. How would they send those jobs back to the queue, and what must the attempt count become?

## Hints

### Hint 1

Start with one migration that adds a `status` and an `attempts` column to `jobs`. A new column on a table that has rows needs a default, or the migration fails on the rows already there, and a default is not always right: the waiting jobs were claimable from when they were enqueued, which the migration can copy from `enqueued_at`.

### Hint 2

Keep one time per job, "not claimable before": when the job is queued, the moment it may run; when it is claimed, the moment the claim runs out. Then a claim that runs out needs no write at all, and one condition finds every job a claim may take: queued or claimed, with that time at or before now.

### Hint 3

The claim is one statement: `UPDATE jobs SET ... WHERE id = (SELECT id FROM jobs WHERE ... ORDER BY seq LIMIT 1 FOR UPDATE SKIP LOCKED) RETURNING ...`. With `=`, the subquery is one value, which Postgres computes once, before the update.

### Hint 4

A complete is one conditional update too: `UPDATE jobs SET status = 'done' WHERE id = $1 AND status = 'claimed' AND attempts = $2 AND <the claim has not run out>`. When `rowCount` is 0, one more query tells an unknown job from a stale claim.

### Hint 5

`pool.connect()` gives you one connection to run `BEGIN`, your statements and `COMMIT` on. Statements through `pool.query` each take whichever connection is free, so they are not one transaction. A claim that first moves dead jobs out of the way and then claims needs both on one connection.

### Hint 6

For level 4, `ORDER BY priority DESC, (SELECT count(*) FROM jobs AS busy WHERE ...), seq` orders the candidates, and the subquery counts the running claims of each candidate's tenant in its queue. In the migration, add the column with the default the other jobs should have, then raise the urgent ones, and only then drop the flag.
