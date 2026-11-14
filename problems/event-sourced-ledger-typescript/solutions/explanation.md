# Event-Sourced Ledger (TypeScript): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | per request | per request | default answer: events are the only truth, one `evolve` function folds them everywhere, and a unique index on each stream's versions lets exactly one append win each version |

## How the project grows level by level

| Level | New requirement | What the code adds |
|-------|-----------------|--------------------|
| 1 | Append events, keep a balance projection in step, transfers as two events | `0002_ledger.sql`'s `accounts` table, `evolve` in `src/events.ts`, `append` and `current` in `src/store.ts`, the three commands in `src/commands.ts`, and `rebuild` run once at startup so the projection begins from the history |
| 2 | `expected_version`, and bursts that never overdraw | The unique index on `(stream_id, version)`, `untilAppended` in `src/db.ts`, which runs a command again when its append lost the race, and transfers that append in account order |
| 3 | A rebuild on demand, and commands that carry their event id | `POST /admin/rebuild` calling the same `rebuild`, the unique index on `(stream_id, event_id)`, and the replay check that comes before the version check |
| 4 | Balances in the past | `instant` in `src/requests.ts`, and `balanceAsOf` in `src/queries.ts`, which folds the events recorded by then through the same `evolve` |

## Approach: reference (One evolve function for every fold, and a unique index that lets one append win each version)

### Intuition

In an event-sourced ledger the events are the only thing that is true. The balance is not stored as a fact; it is what the events add up to, and the table that holds it is a cache with a name, a projection. Two consequences shape the whole service. Whatever the projection says must be exactly what a fresh fold of the events would say, at every moment and after every rebuild. And a balance that never existed as a row, such as the one an account had in March, can still be answered, by folding only the events up to then.

The first consequence is a matter of writing the meaning of an event once. `evolve(account, event)` says what a deposit, a withdrawal or either leg of a transfer does to a balance and a version. Each append computes the projection's new row with it, the rebuild folds every stream with it, and a balance in the past folds a stream's early events with it. A projection drifts when two pieces of code each work out what an event means and one of them is wrong, so there is only one.

The second is that the event and the projection change together or not at all: the event's insert and the projection's update run in one transaction, and a transfer's two events and two updates run in one too.

Concurrency is where the version earns its place. Every append writes the next version of its stream, and a unique index on `(stream_id, version)` means only one transaction can ever write version 4 of `ana`. A withdrawal reads `ana` at version 3 with 30.00, decides that 5.00 fits, and appends version 4. Nineteen others read the same version and the same balance; the first to commit wins, and the other appends fail on the index. Those commands run again from the top, now reading version 4, and decide again on what is really left. Nothing is locked while the decision is made: this is optimistic concurrency, and the store's own versions are the check. A client that sends `expected_version` is doing the same thing one level up: it read version 3 on its screen, and the command refuses to append on top of anything newer.

Idempotency falls out of the same index trick. A client that never heard an answer sends the command again with the same `event_id`, and a unique index on `(stream_id, event_id)` means the store can hold that event once. The command looks for its id first, and if ten copies race, nine lose on the index and find it when they run again.

### Say it out loud

"The events table is the truth; the balance table is a projection I can rebuild. I write one `evolve` function that applies an event to an account, and every fold uses it: the live append, the rebuild, and the as-of query, so they can't disagree.

"A command reads the account from the projection, decides, and appends the event at version plus one, updating the projection in the same transaction. A unique index on stream and version means only one append per version commits; a loser gets a unique violation, and I rerun the command on fresh state. With `expected_version`, a mismatch is a 409. Without it, the retry just decides again, so a burst of twenty withdrawals never overdraws. A transfer appends two events in one transaction, in account-id order so opposite transfers can't deadlock.

"Event ids are unique per stream, so a replayed command finds its own event and answers 200 without appending; I check for it before the version, since the retry's expected version is the one it already moved. The rebuild truncates the projection and refolds every stream in one transaction. A balance as of a time folds the stream's events recorded by then."

### Algorithm

1. On start, rebuild the projection: in one transaction, empty `accounts`, read every event by stream and version, fold each stream with `evolve` from `{balance: 0, version: 0}`, and insert the results.
2. A deposit or withdrawal: check the body; then, in a transaction, read the account from `accounts`. A withdrawal from an account with no row is 404.
3. If the command carries an `event_id` the stream holds, answer 200 with the account as read. If it carries an `expected_version` other than the account's, answer 409 `version_conflict`. If a withdrawal asks for more than the balance, 409 `insufficient_funds`.
4. Compute the next account with `evolve`, insert the event at its version, upsert the projection row, commit, answer 201.
5. If an insert fails on either unique index, roll back and go to step 2.
6. A transfer reads both accounts, checks for its event id in `from`'s stream and the balance of `from`, then appends `transferred_out` and `transferred_in` with one event id, in account-id order, and updates both rows, in one transaction; a lost race runs it again.
7. `POST /admin/rebuild` runs step 1. `GET /accounts/{account}?as_of=T` checks `T`, reads the stream's events with `recorded_at <= T` in version order, and folds them with `evolve`.

### Design

| File | Holds |
|------|-------|
| `migrations/0002_ledger.sql` | The unique indexes on `(stream_id, version)` and `(stream_id, event_id)`, a trigger that refuses any update or delete of an event, and `accounts`, the projection, with `balance >= 0` |
| `src/events.ts` | The event types, `evolve`, and `fold`: the one place that says what an event does |
| `src/store.ts` | `current`, the account as the projection has it; `holds`, whether a stream has an event id; `append`, the event's insert and the projection's update in the caller's transaction |
| `src/db.ts` | The pool, `inTransaction`, and `untilAppended`, which runs a command again when a unique index refused its append |
| `src/commands.ts` | `deposit`, `withdraw` and `transfer`, and `replayOrConflict`, the checks made before anything is appended |
| `src/projection.ts` | `rebuild` |
| `src/queries.ts` | The account now, the account as of a time, and the events |
| `src/requests.ts` | The statement's field rules, and `instant`, which reads `as_of` |

The commands decide from the projection, not by folding the stream each time, which is what makes a read and a decision cheap however long the history grows. That is safe only because the projection row and the event are written together, and because a decision made on a row another append has since moved cannot commit: its insert fails on the version index.

The retry loop catches only unique violations, the one failure that means "another append got there first". Any other error still becomes a 500, so a bug cannot hide as a retry. A command that fails a check returns its refusal from inside the transaction, which commits having written nothing.

The trigger in the migration makes "append-only" a rule of the database rather than a habit of the code: an `UPDATE` or `DELETE` on `events` raises, whoever runs it.

### Correctness

Each stream's versions are written by inserts that a unique index keeps distinct, and each command writes version `v + 1` after reading version `v`, so the versions of a stream are exactly 1 to n with no repeat. The insert of version `v + 1` commits only if no other transaction committed it first, so the command's decision was made on the latest committed state of that stream: a withdrawal commits only if the balance it checked is still the balance, which keeps every balance at or above 0. The projection row is updated in the same transaction as the event, with the value `evolve` gives from the row the command read, and that row was current when the event's version was free, so the row always equals the fold of the stream's committed events. The rebuild computes that fold directly, so it leaves every row as it was.

A transfer inserts both events and updates both rows in one transaction, so either both legs commit or neither does. Every transfer touches its streams in account-id order, so two transfers never wait on each other in a cycle; one waits for the other's insert on their first common stream and then retries.

A replay is answered when the stream already holds the command's event id. Of several copies in flight, the unique index on `(stream_id, event_id)` lets one commit; the rest fail on an index, run again, and find the id. A refused command commits nothing, so it never takes its id. A balance as of `T` folds exactly the stream's events with `recorded_at <= T`, through the same `evolve`, so it is what the projection would have shown at `T`.

### Complexity

- Time: per request — a command reads one projection row and appends one event to each stream it changes, retrying once per competing append that commits first; the rebuild and a balance in the past read every event they fold
- Space: per request — one row per event, kept forever, and one projection row per account

### Trade-offs

Optimistic concurrency does no waiting while a command decides, and loses work instead: under a burst of twenty withdrawals on one account, the last to commit has run up to twenty times. A row lock on the account's projection row, `SELECT ... FOR UPDATE`, would make them queue instead and run each once, which is what a single hot account wants. The version index stays either way, as the guarantee that no two events ever share a version. Optimistic appends fit an event store well because most streams are quiet, and because the version is also what the client sends back as `expected_version`.

The projection is updated in the same transaction as the event, so a reader never sees a balance that disagrees with the store. The usual alternative is a projector that follows the store and updates projections afterwards: appends get faster and projections can live anywhere, but they lag, and a reader can see a deposit's answer before its balance. The rebuild then becomes the projector starting from zero.

Rebuilding at every start keeps a single fold in the code and makes the projection begin from the history whatever the migrations did, at the cost of reading every event at each start. With millions of events, the projection would be filled once by a migration and kept, and snapshots, an account's state saved every so many events, would let a rebuild or a balance in the past start from the latest snapshot before the point it needs. A balance in the past here reads a stream's events with the version index; a very long stream would want an index on `(stream_id, recorded_at)` too.

The rebuild empties the table in its transaction, so readers wait for it. A live system builds the new projection in a second table and swaps the names in one short transaction.

### Pitfalls and edge cases

**Wrong approaches.** Each fails a hidden case, and the failure names what it did. Parallel cases send their burst at once, behind a barrier, and repeat three times from a fresh database, so a race that loses only now and then still fails. None of these are stored as solutions: a pass of a parallel case finds no race and proves none, and the broken solutions are checked by hand until the grader's D7 runs them.

| What it does | Why it is wrong | What catches it |
|--------------|-----------------|-----------------|
| Updates the balance row on a deposit and appends no event | The store does not know the deposit, so the stream lacks it and a rebuild takes it away | `h6`: `body: expected 3 elements, got 2`, and `v9`, `h53` after a rebuild |
| Reads the balance and version, checks the funds in the app, appends at the next version with no unique index, writes back the balance it computed, and ignores `expected_version` | Every request of the burst reads the same balance and the same version, so all of them append, and each overwrites the others' balance | Every burst on its first run: `h30`: `20 requests at once: expected 6 to answer 201 and 14 to answer 409; 20 answered 201; after GET /accounts/ana: body.balance: expected 0, got 1000`, and `h31`: `after GET /accounts/cleo: body.balance: expected 2500, got 900; ... body.version: expected 21, got 5`; then `v8`, `h38`, `h40` and `h42` for the version it never checks |
| Appends with the version index but answers 409 or 500 when its append loses the race | A command without `expected_version` must decide again, not fail | `h31`, `h32`: `expected 20 to answer 201` |
| Debits `from` in one transaction and credits `to` in another, in account order | A credit that comes first stays when the debit is refused, and a credit that loses its race is gone | `h11`, and `h34` with its credits to `ben` |
| Appends a transfer's legs in the order the request names them | Two transfers in opposite directions each hold one stream and wait for the other's, and Postgres fails one with a deadlock | `h35`: answers of 500 among the twenty |
| A rebuild that adds to the rows already there, or skips one event type | The projection drifts from the events the moment it is rebuilt | `v9`, `h50`, `h53` |
| A rebuild that reads the app's own tables, or only the events the app appended | The hidden events are in the store and nowhere else | `h51`, `h52` |
| A rebuild that restores the balance and not the version | The next command expects a version the projection lost | `h54` |
| Looks the event id up, then inserts, with no unique index on it | Ten copies at once all find nothing, and all append | `h60`, `h61`: `expected 1 to answer 201 and 9 to answer 200` |
| Checks `expected_version` before the event id | A retried command whose first try moved the version is answered as a conflict, though it succeeded | `h62` |
| Keeps the ids it has seen in a table of its own | An id the store holds from another writer is not there | `h65` |
| Makes event ids unique across the whole store | A transfer's two events cannot share one, and two accounts cannot use the same id | `h64`, and every transfer that carries an id |
| Answers `as_of` from the projection | The projection only knows now | `v13`, `h86` |
| Passes `as_of` straight to `new Date()` | It accepts a date alone, reads a time with no offset in the container's zone, and turns 30 February into 2 March | `h89`, `h90`, `h92` |
| Compares `recorded_at < as_of`, or compares the text | An event at that very moment counts, and `+01:00` names the same instant as an hour earlier in `Z` | `h80`, `h82` |

**Edge cases.**

- The projection starts from the history the baseline and the hidden events hold, and an account whose events add up to 0 still exists (`v1`, `h1`, `h2`).
- A first deposit opens an account at version 1, and `expected_version: 0` opens one only if nobody has; of ten such deposits at once, one opens it (`h5`, `h33`, `h43`).
- A refused withdrawal or transfer appends nothing, and a transfer to an account with no events takes nothing from `from` (`h7`, `h10`, `h11`).
- A transfer of the whole balance leaves 0, which is allowed (`h8`).
- `version_conflict` is checked before `insufficient_funds`, and `unknown_account` before both (`h39`, `h40`, `h41`).
- A replayed transfer answers both accounts as they stand and leaves one event in each stream (`h58`, `h59`).
- A refused command does not take its event id, and an id is unique within a stream only (`h63`, `h64`).
- `as_of` is inclusive, works in any offset and with fractions of a second, and an account before its first event is 404 (`h80`, `h82`, `h84`, `h87`).
