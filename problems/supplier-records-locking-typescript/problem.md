# Supplier Records with Optimistic Locking (TypeScript)

## Statement

A small service keeps the company's supplier records, and several people edit them at once. Today the last save wins, so someone's change disappears with nobody told. You will make the service refuse a save based on a stale read, merge where that is safe, answer a retry truthfully, and keep a counter that cannot lose an update.

None of this takes a lock, a thread or a timer. A test plays several clients by interleaving their calls, which is exactly how these bugs happen in production: one read, another read, one write, another write.

All the suppliers, people and numbers here are invented.

The service has no network layer. A test plays each client by calling `request`, which takes what an HTTP request would carry and returns a status and a JSON body.

## Input

- `new SupplierApi()`: a service holding two seeded suppliers, `S-1` and `S-2`, both at version 1. Each test gets a new one.
- `method`: the HTTP method, in upper case.
- `path`: the path, with no query string.
- `body`: the raw request text, `""` when there is none. It may be anything a client can send, broken JSON included.

## Output

`request` returns `[status, json]`, two strings: the status code as text, and the body as JSON text. The keys of every object in `json` are in sorted order, with no whitespace, so the order in which your code builds an object does not matter.

A supplier looks like this:

```json
{"contactEmail":"orders@parts.example","id":"S-1","maxOrderCents":50000,"minOrderCents":1000,"name":"Placeholder Parts","notes":"","status":"active","version":1}
```

A failure has this shape, and some failures add keys that their level names:

```json
{"error":{"code":"not_found","message":"No supplier with id S-9"}}
```

## Project

`cstudy start` copies the service into `projects/supplier-records-locking-typescript/`:

- `src/api.ts`: the class `SupplierApi`, exported by name, which must stay there, and the route table.
- `src/commands/` and `src/queries/`: one file per request.
- `src/model/`: the fields of a supplier, their rules, and the store.
- `src/kernel/`: the router, body reading, errors and `canonicalJson`.
- `tests/kernel.test.ts`: tests of those pieces, and `tests/level-<n>.test.ts`: the examples of each open level as `node:test` tests, written when the level opens and never rewritten.
- `README.md`, `package.json` and `tsconfig.json`.

The starter already answers these:

| Request | Answer |
|---------|--------|
| `GET /suppliers` | 200, `{"items":[...]}`, sorted by id |
| `GET /suppliers/:id` | 200 with the supplier, or 404 `not_found` with the message `No supplier with id <id>` |
| `POST /suppliers` with `id` and the fields below | 201 with the new supplier at version 1, or 409 `already_exists` with the message `Supplier <id> already exists` |
| `PUT /suppliers/:id` with the fields below | 200 with the supplier |
| A path no route has | 404 `route_not_found` with the message `No route for <METHOD> <path>` |
| A route's path with another method | 405 `method_not_allowed` with the message `Method <METHOD> not allowed on <path>` |

A body that is not a JSON object answers 400 `invalid_json`, with the message `Request body must be a JSON object`. Bad fields answer 400 `validation_failed` with every problem, in the order of the table, and any other key in a body is ignored:

```json
{"error":{"code":"validation_failed","fields":[{"field":"name","message":"must be a non-empty string"}],"message":"Request validation failed"}}
```

| Field | Valid values | Message |
|-------|--------------|---------|
| `name` | text that is not blank | `must be a non-empty string` |
| `contactEmail` | text with an `@` in it | `must contain @` |
| `notes` | text, which may be empty | `must be a string` |
| `minOrderCents` | a JSON number, whole, from 0 | `must be a whole number from 0` |
| `maxOrderCents` | a JSON number, whole, from 0 | `must be a whole number from 0` |
| `status` | `active` or `paused` | `must be active or paused` |

When all of them are valid and `maxOrderCents` is below `minOrderCents`, the one problem is on the field `maxOrderCents`, with the message `must not be below minOrderCents`. A new `id` must look like `S-123`, with the message `must look like S-123`, and it is reported first.

`cstudy test supplier-records-locking-typescript` runs your tests, and so does `node --test` in the project folder; either run is feedback only, and `cstudy test --typecheck` also type-checks the project. `cstudy submit supplier-records-locking-typescript` grades every case of the open levels, hidden ones included, and opens the next level when they all pass. Each submission grades the earlier levels again, so a later change must keep their rules. Node runs the files by stripping their types, so write no `enum`, no `namespace` and no constructor parameter properties, and import your own files with their `.ts` extension.

## Level 1: Stale writes get a 409

A `PUT` now says which version it read, in `expectedVersion`. It goes through only if that is still the supplier's version. Check in this order:

| Check | Answer |
|-------|--------|
| The supplier exists | 404, as before |
| The body is a JSON object | 400 `invalid_json` |
| The key `expectedVersion` is in the body | 428 `version_required`, with the message `expectedVersion is required` |
| `expectedVersion` is a JSON number, whole, from 1, and the fields are valid | 400 `validation_failed`. `expectedVersion` comes first in the list, with the message `must be a whole number from 1` |
| `expectedVersion` is the supplier's `version` | 409, below, and nothing changes |

```json
{"error":{"code":"stale_write","current":{"contactEmail":"...","id":"S-1","...":"..."},"currentVersion":2,"message":"Supplier S-1 is at version 2"}}
```

`current` is the whole supplier, so the client can show the person what changed without another read.

The version goes up by one when a save changes a field. **A save that changes nothing answers 200 and keeps the version**, so that it cannot make anybody else's read stale.

### Example 1

<!-- case: ex1 -->

Ann and Ben read version 1. Ann saves and it goes to version 2. Ben's save is refused and told the current state, and it goes through once he says he read version 2.

### Example 2

<!-- case: ex2 -->

A write that does not say what it read cannot be checked, so it is refused rather than allowed to overwrite.

## Level 2: Merging where it is safe

Refusing every stale write is safe and annoying: Ann editing the notes should not block Ben fixing the email. `PATCH /suppliers/:id` takes the version the client read, and only the fields it changes:

```json
{"baseVersion":1,"changes":{"notes":"Call before noon"}}
```

Check in this order:

| Check | Answer |
|-------|--------|
| The supplier exists | 404 |
| The body is a JSON object | 400 `invalid_json` |
| The key `baseVersion` is in the body | 428 `version_required`, with the message `baseVersion is required` |
| `baseVersion` is a whole number from 1 | 400, as for `expectedVersion`, on the field `baseVersion` |
| `changes` is an object with at least one key | 400 on the field `changes`, with the message `must be an object with at least one field` |
| Every key of `changes` is an editable field, with a valid value | 400 on the field `changes.<key>`, in sorted order of the keys. A key that is not an editable field has the message `is not a field you can change`, and a bad value has its field's message |

Then decide. A key in `changes` whose value equals the supplier's current value is not a change.

1. **No key is a change.** Answer 200 with the supplier, version unchanged, whatever `baseVersion` says: what the client wanted is already true.
2. **`baseVersion` is the current version.** Apply the changes. A result with `maxOrderCents` below `minOrderCents` is a 400, as usual.
3. **`baseVersion` is older.** A change **conflicts** if it is to `status`, or if its field has changed in any version after `baseVersion`. So you need to know the version in which each field last changed. Any conflict refuses the whole edit, with the 409 below.
4. **`baseVersion` is older and nothing conflicts.** Check the result as it would really be, with the other client's changes in it. A result with `maxOrderCents` below `minOrderCents` is a 409, with `conflicts` listing `maxOrderCents` and `minOrderCents`. Otherwise apply the changes.
5. **`baseVersion` is above the current version.** Nobody was given that version, so every change conflicts.

Applying changes takes the next version. A change to a field through `PUT` counts as a change to that field at that version too, and a field a `PUT` left as it was does not.

```json
{"error":{"code":"merge_conflict","conflicts":["notes"],"current":{"contactEmail":"...","id":"S-1","...":"..."},"currentVersion":2,"message":"Supplier S-1 changed underneath this edit"}}
```

`conflicts` is sorted. `status` never merges because it is a decision made about the whole record, as read.

### Example 1

<!-- case: ex3 -->

Both clients read version 1, and they changed different fields. Ben's edit is based on an old version and still lands, on top of Ann's.

### Example 2

<!-- case: ex4 -->

Both changed `notes`. Whichever went second would overwrite a change its author never saw, so it is refused.

## Level 3: Retrying a write that succeeded

A client saves, the write works, and the answer is lost on the way back. So it retries the same request. By then its `expectedVersion` is stale, and the service answers 409, and the client tells the person their save failed, when it had in fact worked.

`POST /suppliers`, `PUT /suppliers/:id` and `PATCH /suppliers/:id` now take an optional `requestId`, text that is not empty (`must be a non-empty string`, reported last among the fields). The client makes one up per intended write, and sends the same one on a retry.

**Before any other check**, if the body is a JSON object whose `requestId` is text and that id has a stored answer:

- If it is the same request (same method, same path, same JSON, whatever the order of its keys), answer exactly what was answered the first time: the same status, the same body, even though the supplier has moved on since. Nothing changes.
- If it is not, answer 422 `request_id_reused`, with the message `requestId <id> was used for a different request`. Nothing changes.

Otherwise handle the request as usual. An answer from 200 to 299 is stored under its `requestId`. Any other answer is not stored: the write did not happen, so the client may try the same id again, and it will be judged afresh.

### Example 1

<!-- case: ex5 -->

Ann's save worked and her answer was lost. Ben saved after her. Ann's retry gets the answer she should have had, showing version 2, while the supplier stays at version 3.

### Example 2

<!-- case: ex6 -->

The same id with other content means a client bug, and replaying the old answer would hide it.

## Level 4: A counter that loses nothing

Add two counters, `open-orders` at 5 and `late-orders` at 0, both at version 1.

| Request | Answer |
|---------|--------|
| `GET /counters/:name` | 200, `{"name":"open-orders","value":5,"version":1}`, or 404 `not_found` with the message `No counter named <name>` |
| `POST /counters/:name/swap` with `expectedVersion` and `value` | 200 with the counter, holding that value |
| `POST /counters/:name/add` with `amount` | 200 with the counter, its value changed by that amount |

Check in the same order as level 1. For a swap, `expectedVersion` is as before, and `value` is a whole number from 0 (`must be a whole number from 0`). A stale swap answers the same 409 `stale_write`, with `current` being the counter and the message `Counter <name> is at version <n>`. For an add, `amount` is a whole number other than 0 (`must be a whole number other than 0`), and there is no version to send: the service does the arithmetic. An add that would take the value below 0 answers 422 `would_go_negative`, with the message `Counter <name> would go below 0`, and nothing changes.

**Every swap and every add that succeeds takes the next version**, even a swap to the same value. Both take the optional `requestId`, as in level 3.

### Example 1

<!-- case: ex7 -->

Two clients each read 5 and mean to add one. The first swap lands. The second is refused, so that client reads again and swaps from 6 to 7. Neither update is lost.

### Example 2

<!-- case: ex8 -->

An add needs no read, so it has nothing to lose. The retry has the same `requestId`, so it replays and does not add twice.

## Level 5: Deletes and comebacks

`DELETE /suppliers/:id` is a write, so it says what it read: `{"expectedVersion":2}`, with the checks of level 1, in the same order, and without the fields. It takes the optional `requestId`. It answers 200 and takes the next version:

```json
{"deleted":true,"id":"S-1","version":3}
```

After that the supplier answers 404 to `GET`, `PUT`, `PATCH` and `DELETE`, and `GET /suppliers` leaves it out.

`POST /suppliers` with a deleted id brings it back, which is no longer `already_exists`. **A version never goes back**: it takes the version after the delete, and every field counts as changed at that version. Otherwise a client that read version 1 of the old supplier could overwrite the new one, because the number would look right.

A write that succeeded replays as in level 3, even if the supplier has since been deleted, because the `requestId` check comes first.

### Example 1

<!-- case: ex9 -->

The first delete read an old version, so it is refused and the supplier stays. The second has read the current one.

### Example 2

<!-- case: ex10 -->

`S-1` is deleted at version 2 and comes back at version 3. A client still holding version 1 is told it is stale, and cannot overwrite a supplier it has never seen.

## Constraints

- At most 40 requests per test.
- Text fields are at most 100 characters, and numbers are at most 10^9.
- No request's handling is interrupted: requests run one at a time, so a handler's read and write have nothing between them. Two clients interleave only between requests.
- A stored answer is kept forever.

## Follow-ups

- This store is one object. On a database, what does `PUT` become, so that its check and its write are one atomic step? What does the row count of that `UPDATE` tell you?
- A client gets a 409 on every attempt, because a nightly job keeps changing the record. What can it do, and when is a pessimistic lock the better answer?
- Stored answers are kept forever here. For how long must they really live, and what does that decide?
- Two suppliers must change together, or not at all. How far does a version per row take you?

## Hints

### Hint 1

In TypeScript, `"1" == 1` is true and `"1" === 1` is false. What should a client that sends `"1"` get?

### Hint 2

A value alone can't tell you whether a field changed since someone read it. What small piece of history would?

### Hint 3

Two edits can each be valid against what their author saw, and be invalid together. Which record do you validate, the one the client read or the one you are about to store?

### Hint 4

What does a retry find when it arrives? Write down the checks in level 1 and ask which of them can be true of a request whose first attempt succeeded.

### Hint 5

A value that goes from 5 to 6 and back to 5 looks unchanged. What, in a swap, stops a client that read the first 5?

### Hint 6

When a supplier comes back at version 1, what does a client that read version 1 of the old one see?
