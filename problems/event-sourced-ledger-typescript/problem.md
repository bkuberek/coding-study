# Event-Sourced Ledger (TypeScript)

## Statement

A sports club keeps a wallet for each member, topped up at the desk and spent at the bar and on court bookings. The club never edits a wallet's balance. Every change is an event appended to a store that keeps everything: a deposit, a withdrawal, money moving from one member to another. The balance shown at the desk is a projection, what the events add up to, kept in a table so that reading it is cheap. Because the events are the truth, the projection can always be thrown away and made again, and the club can say what any wallet held on any day.

Build the ledger in levels, on Postgres. It appends events and keeps the balance projection in step with them, settles bursts of withdrawals from one wallet so that none is ever overdrawn, rebuilds the projection from the events alone, applies a command sent twice only once, and answers a balance as it stood at any moment in the past. `cstudy` runs your app and its database in a Docker sandbox and judges it by what it answers over HTTP, including bursts of requests sent at the same moment. The club, its members and its numbers are invented.

## Input

HTTP requests with JSON bodies: `GET /accounts/{account}` and `GET /accounts/{account}/events` to read an account and its events, and `POST /accounts/{account}/deposits`, `POST /accounts/{account}/withdrawals` and `POST /transfers` to change it. Each level says what it adds.

## Output

JSON, always with `Content-Type: application/json`. A refusal is `{"error": "<code>"}`, with the codes each level names. Your app reads its port from `PORT` and listens on all interfaces inside the container (`0.0.0.0`), and `GET /health` answers 200 once it is ready.

## Project

`cstudy start` copies the service into `projects/event-sourced-ledger-typescript/`, and `cstudy dev` runs it with its database. Node runs the files by stripping their types, so write no `enum`, no `namespace` and no constructor parameter properties, and import your own files with their `.ts` extension.

- `src/server.ts`: the routes, and where the server starts. It answers `GET /accounts/{account}/events` from the store already, and 501 to the rest.
- `src/db.ts`: the connection pool, from `DATABASE_URL`.
- `migrations/`: the schema, as plain SQL files that node-pg-migrate applies in name order. `0001_baseline.sql` is the problem's and stays as it is; add yours after it, `0002_...sql` and on. Each file starts with `-- Up Migration`, and node-pg-migrate runs each in a transaction of its own and records it in `pgmigrations`.
- `scripts/reset.ts`: puts the database back as it was after your migrations, before a case that starts fresh. You should not need to change it.
- `tests/`: your tests, run by `cstudy test`.
- `.env`: what your app reads, written by `cstudy start` from the problem's settings. Your app's environment already holds it.

`cstudy test` starts a sandbox, applies the migrations, runs your tests beside the app, and then the visible cases of your open levels. `cstudy submit` grades every case of the open levels, hidden ones included, and opens the next level when they all pass. Each submission grades the earlier levels again, so a later change must keep their answers. To look at the data yourself while `cstudy dev` runs, `docker ps` shows its database container, whose name ends in `-db-1`, and `docker exec -it <that name> psql -U app` opens a shell on it.

### The event store

`0001_baseline.sql` creates `events`, the store. Grading writes to it, so your migrations may add indexes, constraints and triggers to it, but must not rename, drop or change a column:

| Column | Holds |
|--------|-------|
| `position` | The store's own order, given by Postgres |
| `stream_id` | The account the event belongs to: an account's events are its stream |
| `version` | The event's place in its stream: 1 for an account's first event, then 2, 3 and on, with no gap and no repeat |
| `event_id` | The event's id, unique within its stream. The two events of a transfer share one |
| `type` | `deposited`, `withdrawn`, `transferred_out` or `transferred_in` |
| `data` | `{"amount": 2500}`, plus `"to"` on a `transferred_out` and `"from"` on a `transferred_in`, naming the other account |
| `recorded_at` | When the event was appended, `now()` by default |

An account exists once its stream holds an event. Its balance is what its `deposited` and `transferred_in` events brought, less what its `withdrawn` and `transferred_out` events took, and its version is how many events it has. Money is in whole cents: 2500 is 25.00. Events are only ever appended: never updated and never deleted.

### The history you start with and the events you do not see

The baseline already holds the club's history, recorded in 2026:

| Account | Events | Balance | Version |
|---------|--------|---------|---------|
| `ana` | 5000 deposited on 5 January, 1200 withdrawn on 10 February, 800 to `ben` on 2 March | 3000 | 3 |
| `ben` | 2000 deposited on 20 January, 800 from `ana` on 2 March | 2800 | 2 |
| `cleo` | 500 deposited on 1 April | 500 | 1 |

When `cstudy submit` grades, it applies the baseline, then appends hidden events to `events`, as another service writing to the store would, and only then applies your migrations. Account ids that start with `x-` are reserved for those events. A balance is what the events say, whoever appended them, so your projection must count them. Grading also applies your migrations to a database that holds the baseline alone, which must work too.

A case that starts fresh gets the database as it was right after your migrations, and your app started again.

## Level 1: Events and a balance projection

`GET /accounts/{account}` answers 200 with the account's balance and version, read from a projection: a table of your own, one row per account, filled from the events the store already holds and moved along by each event your app appends, in the same transaction as that event. Fill it from the history in your migration, or when your app starts.

```json
{"account": "ana", "balance": 3000, "version": 3}
```

`GET /accounts/{account}/events` answers 200 with the account's events in version order, as the store holds them, here `ben`'s:

```json
[{"version": 1, "type": "deposited", "data": {"amount": 2000}}, {"version": 2, "type": "transferred_in", "data": {"amount": 800, "from": "ana"}}]
```

Three commands append events, and each answers 201 with what it changed, as `GET /accounts/{account}` would show it after:

| Request | Body | Appends |
|---------|------|---------|
| `POST /accounts/{account}/deposits` | `{"amount": 2500}` | `deposited` to the account's stream. The first deposit to an account with no events opens it at version 1 |
| `POST /accounts/{account}/withdrawals` | `{"amount": 1200}` | `withdrawn` |
| `POST /transfers` | `{"from": "ana", "to": "ben", "amount": 800}` | `transferred_out` to `from`'s stream and `transferred_in` to `to`'s, sharing one event id, in one transaction: both or neither |

A transfer answers both accounts: `{"from": {"account": "ana", "balance": 2200, "version": 4}, "to": {"account": "ben", "balance": 3600, "version": 3}}`. Every event needs an `event_id`; make up one that is unique, `crypto.randomUUID()` for instance, until level 3 lets the client choose it.

| Field | Rule |
|-------|------|
| `{account}`, `from`, `to` | 1 to 64 letters, digits, `-` or `_` |
| `amount` | A whole number of cents from 1 to 1000000 |
| `from` and `to` | Two different accounts |

| Request | Status | Body |
|---------|--------|------|
| A body that is not a JSON object, or a field missing or breaking its rule | 400 | `{"error": "invalid_request"}` |
| A withdrawal from an account with no events, or a transfer from or to one | 404 | `{"error": "unknown_account"}` |
| A withdrawal or a transfer of more than the balance | 409 | `{"error": "insufficient_funds"}` |

A command is checked in the order of this table, and a refused one appends nothing. `GET` of an account with no events, or of its events, is 404 `unknown_account`.

### Example 1

<!-- case: v1 -->

`ana`'s balance and version, from the history the baseline holds.

### Example 2

<!-- case: v2 -->

A deposit of 25.00 is `ana`'s fourth event.

### Example 3

<!-- case: v3 -->

`cleo` withdrew 2.00 first, and her stream now holds two events.

### Example 4

<!-- case: v4 -->

`ben` sends `cleo` 10.00.

### Example 5

<!-- case: v5 -->

`cleo` has 5.00 and asks for 5.01.

## Level 2: One version at a time

Deposits and withdrawals take `expected_version`, a whole number from 0: the version the client last read. The command appends only if the account is still at that version, and otherwise answers 409 `{"error": "version_conflict"}`, so a client that decided on a stale balance hears about it. An account with no events is at version 0, so `expected_version: 0` opens an account only if nobody has.

A command without `expected_version` appends at whatever version the account has when it runs, and never answers `version_conflict`: when another append gets there first, it reads again and decides again. The cases send bursts of up to 20 requests at the same moment, and judge how many succeeded and what the account holds after. However the requests interleave, a balance never goes below 0, each command that succeeds appends exactly one event to each stream it changes, versions stay 1, 2, 3 with no gap and no repeat, and transfers between the same two accounts in both directions all go through.

| Request | Status | Body |
|---------|--------|------|
| `expected_version` that is not a whole number from 0 | 400 | `{"error": "invalid_request"}` |
| `expected_version` that is not the account's version | 409 | `{"error": "version_conflict"}` |

`version_conflict` comes right after `unknown_account` and before `insufficient_funds`.

Reading the balance, deciding, and then writing is the bug: between your read and your write, every other request of the burst read the same balance and the same version. A unique index on `events (stream_id, version)` lets exactly one append at each version commit; the others fail with a unique violation, and the command runs again on what is now committed. A burst's example shows the request it repeats and the statuses expected, which can come back in any order.

### Example 1

<!-- case: v6 -->

Five withdrawals of 10.00 at once from `ben`'s 28.00: two succeed, and he has 8.00 left.

### Example 2

<!-- case: v7 -->

Five withdrawals at once, all expecting version 3: the first to append wins, and the others conflict.

### Example 3

<!-- case: v8 -->

A deposit moved `ana` to version 4, and this one still expects 3.

## Level 3: Rebuild and replay

`POST /admin/rebuild` makes the projection again from the events alone, and answers 200 with `{"status": "rebuilt"}` once it is done. Afterwards every account shows what its events say, which must be exactly what the appends had made: a projection that drifts from its events is wrong. Run it in one transaction, so that no reader sees the projection half made.

Deposits, withdrawals and transfers take `event_id`, the id the client gives the command, 1 to 64 letters, digits, `-` or `_`. The event, or the two events of a transfer, are stored with it. A client that never heard an answer sends the command again with the same id, and that must change nothing: a command whose event id the account's stream already holds, for a transfer `from`'s stream, appends nothing and answers 200 with the account, or both accounts, as they stand now. That holds when the same command arrives ten times at once, too. An event id is unique within its stream, not across streams, and a refused command does not take its id.

| Request | Status | Body |
|---------|--------|------|
| `event_id` breaking its rule | 400 | `{"error": "invalid_request"}` |
| An `event_id` the stream already holds | 200 | The account as it stands, or both accounts for a transfer |

A replay is recognized right after `unknown_account`, before `version_conflict` and `insufficient_funds`: the version a retried command expected may be the very one it moved.

### Example 1

<!-- case: v9 -->

A deposit, a withdrawal and a transfer, then a rebuild: `ana` shows the same balance and version as the appends had left her.

### Example 2

<!-- case: v10 -->

The deposit `top-up-1` arrives a second time: nothing is appended, and `cleo` still has 7.50 at version 2.

### Example 3

<!-- case: v11 -->

The rebuild's answer.

## Level 4: Balances in the past

The projection only knows now. The club's auditors ask what a wallet held at the end of a month, and the events can say: `GET /accounts/{account}?as_of=<time>` answers 200 with the account as it stood at that moment, after every event recorded at or before it, by `recorded_at`.

```json
{"account": "ana", "balance": 3800, "version": 2}
```

A time is written `YYYY-MM-DDThh:mm:ss`, optionally with a fraction of a second, then `Z` or an offset such as `+01:00`, and names a real date and time: `2026-03-15T13:00:00+01:00` is the same moment as `2026-03-15T12:00:00Z`.

| Request | Status | Body |
|---------|--------|------|
| `as_of` that is not such a time: a date alone, a time with no offset, 30 February | 400 | `{"error": "invalid_request"}` |
| An account with no event recorded by then | 404 | `{"error": "unknown_account"}` |

### Example 1

<!-- case: v12 -->

By 15 February, `ana` had deposited 50.00 and withdrawn 12.00.

### Example 2

<!-- case: v13 -->

A deposit made today is not in her balance as of June.

### Example 3

<!-- case: v14 -->

`ben`'s first event came on 20 January.

## Constraints

- Postgres 17, through `DATABASE_URL`, with node-pg-migrate's plain SQL migrations. The baseline migration stays as it is, and `events` keeps its columns.
- Bursts of up to 20 requests at once; a case has 10 s for all its requests.
- Every answer of a case that repeats must be right on every run: a race that loses one time in three still fails.
- Grading appends hidden events before your migrations run, and also migrates a database that holds the baseline alone.

## Follow-ups

- A wallet with ten million events: the rebuild and a balance in the past both fold every one. Where would snapshots go, how often would you take them, and what must a rebuild do with them?
- Here each append updates the projection in its own transaction. What changes when a separate process follows the store and updates the projection instead, and how does a reader learn how far behind it is?
- The rebuild empties the table and makes readers wait while it runs. How would you build a new projection beside the live one and switch over with no pause?
- A deposit was made by mistake, and events are never deleted. How does the ledger take it back, and what would the account's events look like afterwards?
- `position` comes from an identity column, given out when a row is inserted, not when it commits. Why can a reader that follows the store by position miss an event, and what would you do about it?
- Transfers gain a `memo`, and the old events stay as they were written. How does the code read both shapes for years to come?

## Hints

### Hint 1

Start with one migration that creates the projection, one row per account with its balance and version, and fills it from the events already there with one `INSERT ... SELECT ... GROUP BY stream_id`. Or fill it when your app starts: either way it begins from the history.

### Hint 2

`pool.connect()` gives you one connection to run `BEGIN`, the event's insert, the projection's update and `COMMIT` on. Statements through `pool.query` each take whichever connection is free, so they are not one transaction. A transfer is two inserts and two updates in one transaction, and a `ROLLBACK` takes back all four.

### Hint 3

`CREATE UNIQUE INDEX ON events (stream_id, version)`: of two transactions that append the same version, the second fails with code `23505` once the first commits. Catch it, roll back and run the whole command again. A command that carried `expected_version` then finds the version moved and answers the conflict; one that did not decides again on the new balance.

### Hint 4

Two transfers between the same accounts in opposite directions each append to one stream and then wait for the other's: Postgres ends that deadlock by failing one of them. Append to the two streams in one order every time, by account id for instance.

### Hint 5

Write what an event does to an account once, as a function from an account and an event to the next account, and use it for every append, for the rebuild and for a balance in the past. Three places that each work it out are three places that can disagree.

### Hint 6

`CREATE UNIQUE INDEX ON events (stream_id, event_id)` makes ten copies of one command fail like a lost race. When the command runs again, look for its event id before anything else.

### Hint 7

Check `as_of`'s shape with a regular expression before `new Date()` reads it: `Date` takes a date alone, reads a time with no offset in the machine's own zone, and rolls 30 February over to 2 March.
