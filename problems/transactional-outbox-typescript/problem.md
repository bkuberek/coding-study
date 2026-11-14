# Transactional Outbox (TypeScript)

## Statement

A tool rental desk keeps its rentals in a database, and now other services want to hear about every move: a board that shows what is out, a reminder service, a report. Writing to the database and then telling a broker looks like one step, and it is two systems that can each fail on their own.

You will make a move, its audit row and its event commit as one, and then build the relay that gets those events out, in order, at least once, however the broker behaves.

All the rentals, people and events here are invented.

Nothing here runs over a network: a test calls the desk's methods, and the database and the broker are objects in memory that fail on cue.

## Input

- `new RentalDesk()`: a desk with no rentals. Each test gets a new one.
- `rentalId`: the rental's id, such as `R-1`.
- `action`: one of `reserve`, `pickup`, `return` and `cancel`. Anything else is refused.
- `actor`: who did it.

A rental moves like this, and every other move is refused:

| Action | From | To | Event type |
|--------|------|----|------------|
| `reserve` | no rental yet | `reserved` | `rental.reserved` |
| `pickup` | `reserved` | `out` | `rental.picked_up` |
| `return` | `out` | `returned` | `rental.returned` |
| `cancel` | `reserved` | `cancelled` | `rental.cancelled` |

## Output

`act` returns `ok`, `refused` when the table does not allow the move, or `failed` when the database refused a write.

`rental(rentalId)` returns the rental as JSON text with sorted keys, or `""` when there is none. `version` starts at 1 and goes up by one with each move:

```json
{"id":"R-1","state":"reserved","version":1}
```

`audit()` returns the audit trail, oldest first, one line per move: `R-1 v1 reserve by ann`.

## Project

`cstudy start` copies the desk into `projects/transactional-outbox-typescript/`:

- `src/desk.ts`: the class `RentalDesk`, exported by name, which must stay there.
- `src/core/`: `rental.ts` (the move table), `rentalService.ts` (the use case) and `ports.ts` (what the core needs from outside).
- `src/adapters/`: `memoryDatabase.ts` and `fakeBroker.ts`, which stand in for the real things.
- `tests/plumbing.test.ts`: tests of those pieces, and `tests/level-<n>.test.ts`: the examples of each open level as `node:test` tests, written when the level opens and never rewritten.
- `README.md`, `package.json` and `tsconfig.json`.

`failNextWrite(table)` makes the next write to a table throw `WriteFailed`. The tables are named `rentals` and `audit`, and later `outbox`.

`cstudy test transactional-outbox-typescript` runs your tests, and so does `node --test` in the project folder; either run is feedback only, and `cstudy test --typecheck` also type-checks the project. `cstudy submit transactional-outbox-typescript` grades every case of the open levels, hidden ones included, and opens the next level when they all pass. Each submission grades the earlier levels again, so a later change must keep their rules. Node runs the files by stripping their types, so write no `enum`, no `namespace` and no constructor parameter properties, and import your own files with their `.ts` extension.

## Level 1: One transaction

The starter writes the rental, then the audit row. When the audit write fails, the rental has moved with no record of who moved it.

`MemoryDatabase` has no transactions. Give it some: a move's writes all land, or none of them do. When a write fails, `act` answers `failed`, the database is exactly as it was before the call, and the next `act` works normally.

### Example 1

<!-- case: ex1 -->

Two moves, two audit rows. The version counts the moves.

### Example 2

<!-- case: ex2 -->

The audit write fails during `pickup`. The rental is still `reserved` at version 1, and the same `pickup` then works, at version 2.

## Level 2: The outbox row

Each move now also writes an event, as a row in a new table named `outbox`, in the same transaction as the move. `outbox()` returns the rows, oldest first, as JSON text with sorted keys:

```json
{"aggregateId":"R-1","id":"evt-1","sequence":1,"state":"reserved","status":"pending","type":"rental.reserved"}
```

| Field | Value |
|-------|-------|
| `aggregateId` | The rental's id |
| `id` | `evt-<n>`, where `n` counts the outbox rows ever committed, from 1. A rollback uses up no number |
| `sequence` | The rental's `version` after this move, which orders one rental's events |
| `state` | The rental's state after this move |
| `status` | `pending` |
| `type` | From the table of moves |

If any of the three writes fails, none of them land. A refused move writes nothing.

### Example 1

<!-- case: ex3 -->

Three moves on two rentals. `id` counts across the table, and `sequence` counts per rental.

### Example 2

<!-- case: ex4 -->

The outbox write fails, so the move and its audit row are undone too: there is no state that nobody hears about.

## Level 3: The relay

Now get the events out. `relay(limit)` makes one pass over the pending rows, oldest first, and publishes each to `FakeBroker`, up to `limit` publish attempts. Once the broker confirms a row, mark that row `sent`, in a transaction of its own. A pass returns how many rows it marked.

Publish the row as it was committed: `FakeBroker.publish` takes its `id`, `aggregateId`, `sequence`, `type` and `state`.

When a publish fails (`PublishFailed`), the row stays `pending` and the next pass tries it again, under the same id. The pass carries on with the next row. A failed attempt counts against the limit.

`published()` returns everything the broker has delivered, in order and with any duplicates, one line per delivery: `evt-1 R-1 #1 reserved`, which is `<id> <aggregateId> #<sequence> <state>`.

Two switches make the broker misbehave. Pass them to `FakeBroker`:

- `failNextPublish(rentalId, times)`: the next `times` publishes for that rental are refused, and nothing is delivered.
- `loseNextAck(rentalId)`: the next publish for that rental is delivered, and then throws `PublishFailed` as if it had not been. The relay cannot tell the two apart.

### Example 1

<!-- case: ex5 -->

Both rows go out and are marked `sent`, and the next pass finds nothing to do.

### Example 2

<!-- case: ex6 -->

The broker refuses, so the row stays `pending`, and the next pass sends it.

## Level 4: Order per rental

A consumer that hears `rental.picked_up` before `rental.reserved` has a bug it did not write. So events of one rental must reach the broker in `sequence` order, whatever fails.

Within one pass, once a publish for a rental fails, skip that rental's later rows until the next pass. Other rentals carry on, so one stuck rental delays only itself: the order across rentals is not promised.

A skipped row is not an attempt, so it does not count against `limit`. A row the broker confirmed and the database then refused to mark (`failNextWrite("outbox")` during a pass) stays `pending` and counts as a failure of that rental, and the pass does not return it in its count.

### Example 1

<!-- case: ex7 -->

`R-1` has three rows, and its first is refused. Its other two wait, and `R-2` goes ahead. The next pass sends all three of `R-1`'s in order.

### Example 2

<!-- case: ex8 -->

One row of `R-1` is already out. The next is refused, and the one after it must not overtake it.

## Level 5: The consumer and the cleanup

Build the first consumer: a board of how many rentals are out, which subscribes to the broker with `FakeBroker.subscribe`. It hears every delivery, duplicates included. A count is not idempotent, so it must apply each event once, by its id.

- `rentalsOut()`: how many rentals are out, by the events applied: `out` adds one, and `returned` takes one away.
- `eventsApplied()`: how many different events it has applied.

And the outbox cannot grow forever. `prune()` deletes the rows marked `sent` and returns how many it deleted. Rows still `pending` stay. Pruning changes no number that comes after it: the next event still gets the next `evt-<n>`, and the next move of a rental the next `sequence`.

### Example 1

<!-- case: ex9 -->

`evt-2` is delivered twice, because the first confirmation was lost. The board counts one rental out, and two events.

### Example 2

<!-- case: ex10 -->

The two sent rows go, and the pending one stays. The next event is `evt-4`, not `evt-2`.

## Constraints

- At most 40 calls per test.
- `limit` and `times` are whole numbers from 1 to 100.
- One thing happens at a time: nothing in this problem runs concurrently.
- `failNextWrite` applies to the next write to the table, whichever call makes it.

## Follow-ups

- Two relay processes run at once. What stops them from sending `R-1`'s rows out of order, and what would you lock: the row, the rental or the table?
- A rental's event fails for a whole day. How would you know, and what would you do about a rental that blocks its own events forever?
- A consumer asks to read every event from the start. Pruning has deleted them. What does your design offer it?
- Could a change-data-capture stream replace the relay? What would you gain and what would you give up?

## Hints

### Hint 1

Copying a `Map` copies its references. In the starter, `RentalService` changes a rental in place, on the object the table holds. What does a shallow copy of the table hold after that?

### Hint 2

Where does the next event number live? What happens to it on a rollback, and what happens to it when rows are deleted?

### Hint 3

The relay should read only the outbox row. If it goes back to the rental for anything, what state would it find by the time it runs?

### Hint 4

A relay that marks first and publishes second loses events, and one that publishes first and marks second repeats them. Only one of those can be fixed by the consumer.

### Hint 5

Choosing the first `limit` pending rows before you start can fill the whole window with rows you are about to skip.
