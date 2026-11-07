# Transactional Outbox (TypeScript): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | O(t) per action; O(p + t l) per relay pass | O(r + a + p) | default answer: the event commits with the state, and a relay publishes it afterwards, holding back only the rental that failed |

Here `t` is the size of the tables (the in-memory transaction copies them, a real database would not), `p` the outbox rows, `l` the limit, `r` the rentals and `a` the audit rows.

## How the project grows level by level

| Level | New requirement | What the code adds |
|-------|-----------------|--------------------|
| 1 | Atomic state and audit | `MemoryDatabase.transaction`, a deep copy on the way in and a restore on a throw; `RentalService.act` runs in it and turns `WriteFailed` into `failed` |
| 2 | The outbox row | `MemoryOutbox`, an `outbox` table and a counter that lives in the tables; one more write inside the same transaction |
| 3 | The relay | `src/core/relay.ts`: publish, then mark, each row in its own transaction |
| 4 | Order per rental | One `Set` in the relay's pass: the rentals held back |
| 5 | Consumer and cleanup | `src/downstream/availabilityBoard.ts`, and `deleteSent`, which works only because level 2 did not derive numbers from rows |

## Approach: reference (The outbox row in the state's transaction and a relay that holds back a failed rental)

### Intuition

"Save, then publish" is a distributed transaction with no coordinator. The save can succeed and the publish fail, so state changed and nobody heard. Reverse it and a consumer hears about a change that then rolls back. No amount of retrying closes that window, because the process can die between the two.

The outbox removes the second system from the moment that matters. The event becomes a row, and a row can commit with the state in an ordinary database transaction. So there is one decision, not two. Getting the row to the broker is now a separate job that can be retried for as long as it takes, because the row is durable, and "publish then mark" fails only one way: it sends again. That is at-least-once delivery, by design, and a consumer can handle a duplicate if the event has an id that does not change.

The order is the subtle part. Retrying a failed row after the others have gone is natural and it is wrong: a consumer hears `picked_up` before `reserved`. So after a failure, that rental's later rows wait. Other rentals don't, because one stuck rental should delay only itself.

### Say it out loud

"Writing to the database and then publishing is a dual write: there's no way to make it atomic, and a crash in between loses the event or invents one. So I'd make the event a row in the same transaction as the state change, and have a relay publish committed rows.

"That gives me at-least-once. The relay publishes and then marks. If the confirmation is lost it can't tell, so it sends again. That's fine as long as the id is assigned when the row is written, not when it's sent, so consumers can dedupe.

"Ordering is per aggregate, not global. If a publish fails for one rental I hold back its later rows for this pass, and the others carry on. A global stop would let one bad rental block everything.

"And I'd watch my batch query. If I take the first N pending rows and then skip the blocked ones, a stuck aggregate fills the window and starves everyone behind it. So the limit has to count attempts, not rows read."

### Algorithm

1. `act`: open a transaction. Find the rental, ask the table for the next state, and refuse if there is none. Change the rental, write the audit row, write the outbox row. Commit. A `WriteFailed` anywhere rolls back everything, and answers `failed`.
2. The event's number comes from a counter inside the tables, so a rollback restores it and pruning leaves it alone. Its sequence is the rental's version, for the same two reasons.
3. `relay(limit)`: read the pending rows, oldest first. For each, stop if `limit` attempts were made, and skip it if its rental is held back. Otherwise count an attempt, publish it from the row, and mark it in its own transaction.
4. If the publish or the mark fails, hold the rental back for the rest of this pass. The row stays `pending`, so the next pass starts with it.
5. The board remembers the event ids it has applied, and ignores the others.
6. `prune`: delete rows marked `sent`.

### Design

| File | Responsible for |
|------|-----------------|
| `src/desk.ts` | `RentalDesk`: wiring, and turning rows into the lines and JSON the outside sees |
| `src/core/rental.ts` | The table of moves, now with its event types |
| `src/core/rentalService.ts` | The use case: what goes into one transaction, and what `failed` means |
| `src/core/relay.ts` | One pass of the relay. It knows the outbox and the publisher, and nothing about rentals |
| `src/core/ports.ts` | What the core needs: tables, `UnitOfWork`, `EventPublisher`, and the two failures. The core imports no adapter |
| `src/adapters/memoryDatabase.ts` | The tables, the counter, the fault switch and `transaction`, with the table classes reading through `database.tables`, so a restore reaches them |
| `src/adapters/fakeBroker.ts` | The broker: refuses, delivers, and loses confirmations on cue. Unchanged except that it meets `EventPublisher` as it was |
| `src/downstream/availabilityBoard.ts` | The consumer. In production this is another team's service, and its only contract with us is the event |
| `tests/relay.test.ts` | The relay on its own: overtaking, and rows held back taking no attempts |

The rollback uses `structuredClone` because the service changes rentals in place. That is the JavaScript version of a point worth knowing: a copy of a `Map` holds the same row objects, so a "snapshot" of that kind restores nothing once a row has been mutated.

### Next in production

- Run one relay per shard, or take row locks with `FOR UPDATE SKIP LOCKED`, and think about order: two relays that each take some of a rental's rows can swap them. Partition by aggregate id, so that one owner holds each rental at a time, and key the broker's partition the same way.
- Alert on the age of the oldest pending row, not on the row count. A healthy outbox with a busy hour has many rows, and a stuck one has an old row.
- Decide what a stuck aggregate does. Holding it back forever needs a dead-letter state and a person, because at some point the order matters less than the backlog.
- Prune on a schedule, by age, well after `sent`, so you can replay a recent window to a consumer that lost data. Index `(status, id)`, or the relay's scan becomes the slowest query you own.
- Consider change data capture on the outbox table instead of polling. It cuts latency and load, and adds an operational dependency. The transactional part of the design stays the same.
- Give events a schema, a version field and a stable contract. The outbox makes an internal table into a public API.
- Tell consumers plainly that delivery is at-least-once, and ordered per aggregate only, and put the event id in the contract so they can dedupe.

### Correctness

Every move is one transaction, and `transaction` restores a deep copy on any throw, so after `act` either all three rows landed or the tables are exactly as before, counter included. So there is an event exactly when there was a change. That is the invariant the whole design rests on.

The relay reads only committed rows, and publishes them as they were written, so what a consumer hears was true at that sequence, whatever has happened since. A row changes to `sent` only after the broker confirmed it, so no event is lost: a row is either confirmed or still pending, and any pending row is attempted again, for as long as passes keep running.

Within a pass, rows are read in commit order, and one rental's sequence grows with commit order, so a rental's rows are attempted in sequence. After a failure, `heldBack` skips the rest of that rental for the pass. The next pass reads from the oldest pending row, which is the failed one, so no later row of that rental can ever be delivered first. A lost confirmation repeats a row, and the repeat comes before any later row: consumers see `2, 2, 3`, and never `3, 2`.

Numbers come from `eventsWritten` and `version`, which `deleteSent` does not touch, so a pruned id is never reused, and a consumer's memory of applied ids stays valid.

### Complexity

- Time: O(t) per action; O(p + t l) per relay pass — a transaction copies the tables here, a pass reads the pending rows once, and marks at most `l` of them. A real database makes both of these a few index operations.
- Space: O(r + a + p) — one row per rental, audit entry and outbox row. The board adds one id per event in this exercise; in production it would expire them.

### Trade-offs

- **Polling relay against change data capture.** Polling is simple and adds load and latency. A log-based reader does neither, and is another system to run.
- **Holding back one rental against a global stop.** A global stop gives a total order, which nobody here asked for, at the price of one bad rental stopping the desk. Per-aggregate order is usually the promise you can keep.
- **One transaction per mark against one per batch.** A batch mark is faster, and on a failure it rolls back marks for rows the broker already has, so a whole batch goes out twice. It is still correct at-least-once. It is just noisier.
- **`sent` flag and pruning against deleting on send.** Deleting at once keeps the table small and gives up any chance to replay.
- **Saga or two-phase commit.** Two-phase commit across a database and a broker is rarely available, and it costs availability when it is. An outbox gives up immediacy, and nothing else.

### Pitfalls and edge cases

Each wrong approach below was run as a one-line change on the reference, through `cstudy submit`, and each fails the cases named with it.

- **A shallow copy as the snapshot.** The service changes rows in place, so the "restored" table holds the changed rows. Caught by `ex2`, `h4` and `h12`.
- **Catching the failure and restoring nothing.** Caught by `ex2`, `h2` and `h4`.
- **Writing the event after the commit.** When that write fails, the state has moved and nobody will ever hear. Caught by `ex4` and `h12`.
- **Writing the event before the transaction.** When a later write fails, an event survives for a change that never happened. Caught by `h7`, `h8` and `h9`.
- **Keeping the event counter in a field, and writing the event first.** A rollback does not restore it, so a number is lost. Caught by `h9`.
- **Taking the event number from the table's size.** It works until something is deleted, and then numbers repeat, and a consumer drops a new event as a duplicate. Caught by `ex10` and `h29`.
- **Counting a rental's rows for its sequence.** The same mistake, for the sequence. Caught by `h30`.
- **Assigning the id when publishing.** Every retry is a different event to the consumer. Caught by `ex6` and `h13`.
- **Marking the row first, then publishing.** A refused publish loses the event for good. Caught by `ex6` and `h13`.
- **Marking the row whatever happened.** The same loss, spelled as a `finally`. Caught by `ex6`, `h17` and `h18`.
- **Marking at the end of the pass.** One failure means rows already delivered go out again. Caught by `h17` and `ex7`.
- **Building the event from the rental's state now.** Every event then says the latest state. Caught by `h16`.
- **Publishing newest first.** Caught by `ex5` and `h14`.
- **Carrying on after a failure with the same rental.** The rental's later events overtake the one that failed. Caught by `ex7`, `ex8` and `h21`.
- **Retrying failed rows at the end of the next pass.** It keeps every row and loses the order. Caught by `ex7`, `ex8` and `h21`.
- **Stopping the pass at the first failure.** One rental then holds up all of them. Caught by `h17` and `ex7`.
- **Choosing `limit` rows before the pass starts.** A stuck rental fills the window, and starves whoever is behind it. Caught by `h23` and `h24`.
- **Counting skipped rows as attempts.** The same starvation. Caught by `h23` and `h24`.
- **Not counting a failed attempt.** A dead broker then costs a pass nothing, and the pass goes on trying everything. Caught by `h18` and `h25`.
- **Letting a failed mark escape.** The broker has the event, and the pass dies with an error. It must count as a failure of that rental. Caught by `h26`.
- **A consumer that applies every delivery.** A count goes wrong on the first duplicate. Caught by `ex9` and `h34`.
- **A consumer that dedupes on the sequence alone.** Sequences are per rental, so a second rental's first event looks like a duplicate. Caught by `h29`, `h33` and `h35`.
- **Pruning pending rows.** They were not delivered yet. Caught by `ex10` and `h31`.
- Project traps: `src/desk.ts` must export `RentalDesk` by name; local imports need their `.ts` extension; `enum`, `namespace` and constructor parameter properties make Node refuse the file before any test runs.
