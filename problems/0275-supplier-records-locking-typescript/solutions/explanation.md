# Supplier Records with Optimistic Locking (TypeScript): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | O(s log s) per list request; O(1) per other request | O(s + c + q) | default answer: a version that only goes up, a per-field history where a merge needs it, and a replay layer in front of every write |

Here `s` is the number of suppliers, tombstones included, `c` the number of counters and `q` the number of stored answers.

## How the project grows level by level

| Level | New requirement | What the code adds |
|-------|-----------------|--------------------|
| 1 | Stale writes | `src/kernel/versionCheck.ts`, and a store whose `apply` changes the version only when a field changes |
| 2 | Safe merges | `src/model/merge.ts`, a pure decision, `src/commands/patchSupplier.ts`, and `lastChanged` per field in the store |
| 3 | Retries | `src/kernel/replay.ts`, one function wrapped around every write in the route table |
| 4 | Counters | `src/model/counterStore.ts`, `src/commands/swapCounter.ts`, `src/commands/addToCounter.ts`, and a line in the table for each: the replay comes free |
| 5 | Deletes | `src/commands/deleteSupplier.ts`, and tombstones in the store, which keep the version |

## Approach: reference (Versions that never go back with field history and a replay layer in front of every write)

### Intuition

A read and a later write are not one operation, however close together they are in the code. Between them, anyone else can write. An optimistic lock is the smallest thing that makes that visible: the write says what it read, and the store refuses it if that is no longer true. Nothing waits and nothing is held, so an idle client costs nothing. The price is that someone has to deal with being refused, which is what the other levels are about.

Three ideas do most of the work here, and each is easy to get subtly wrong.

**A version is a promise that "something happened", and a value cannot make that promise.** 5, then 6, then 5 looks unchanged and isn't. A swap that compares values misses that (the ABA problem), and so does a delete and re-create that starts counting from 1 again. So a version never goes back, which is why a deleted row stays as a tombstone.

**A merge is a judgement about the result, not about the edit.** Field-level history answers "did someone change what I changed?", but two edits to different fields can still break a rule between them. Raising the minimum is fine, and lowering the maximum is fine, and together they are not. That is write skew, and the only way to catch it is to validate the merged record.

**A retry isn't a new write.** A write that succeeded and whose answer was lost looks exactly like a stale write, so the check has to come before the version check, and before anything else that the first attempt changed. The stored answer is the truth about the first attempt, and the current state isn't.

### Say it out loud

"Every write says what it read. If the version moved, it's a 409 with the current record, so the client can show the person what changed. A write with no version is a 428, rather than a blind write, because that's how lost updates come back. And I'd only bump the version on a real change, or a no-op save makes everyone else's read stale.

"For merging: I track the version where each field last changed, so a stale edit to an untouched field can land. But I validate the merged result, because two edits that are each valid can break a rule together. And some fields, like `status`, shouldn't merge at all, because they're a decision about the record as you read it.

"For retries, the classic bug is that a successful write whose response got lost looks like a conflict on retry. So an idempotency check runs first, before the version check. I store the answer as it was, only for successes, and I fingerprint the request, so reusing an id for something else is an error and not a silent replay.

"For the counter, a compare-and-set on the version, not the value, because of ABA. And I'd rather offer an atomic add, so nobody has to read at all. Everything that changes the value bumps the version, or a swap from an old read would erase an add."

### Algorithm

1. In front of every write, `withReplay` reads the body. If it holds a text `requestId` with a stored answer, compare fingerprints: the same request gets the stored status and text, and another gets a 422.
2. The handler checks existence, then the body, then that the version key is present, then all the fields, then the version.
3. `PUT` stores the fields, and `apply` takes a version only if one of them differs. It records that version as `lastChanged` for the ones that did.
4. `PATCH` runs `decideMerge`: drop changes that are already true; at the current version only the result's rule matters; at an older version, conflicts come from `status` and `lastChanged`, then the merged result is checked; a version from the future conflicts on everything.
5. A swap checks the version and writes, and an add writes. Both take the next version, always.
6. A delete checks the version and leaves a tombstone. A create on a tombstone continues from its version, with all fields changed at that version.
7. Back in `withReplay`, an answer from 200 to 299 is stored as text under its `requestId`.

### Design

| File | Responsible for |
|------|-----------------|
| `src/api.ts` | `SupplierApi`: the route table, in which `write(...)` marks everything that replays, and the only `catch` |
| `src/kernel/replay.ts` | The replay layer, in one place, outside every handler, so a new write gets it by wrapping |
| `src/kernel/versionCheck.ts` | The version's presence, shape and the 409, shared by every versioned write |
| `src/kernel/router.ts`, `body.ts`, `errors.ts`, `json.ts` | Plumbing, unchanged from the starter |
| `src/model/merge.ts` | `decideMerge`: a pure function from the current state and an edit to a decision |
| `src/model/supplier.ts` | The fields and their rules, unchanged from the starter |
| `src/model/supplierStore.ts` | Versions, the per-field history and tombstones |
| `src/model/counterStore.ts` | Counters, whose every write takes a version |
| `src/commands/*.ts` | The order of the checks for each write, and nothing else |
| `src/queries/*.ts` | Reads, which go through the store's filter on tombstones |
| `tests/merge.test.ts` | Every path through the merge decision, without a request |

Why is the replay a wrapper and not a call inside each handler? Because the rule is "before any other check", and in a handler that is easy to break: put it after the existence check, and a retry after a delete answers 404. Wrapped around the handler, it cannot come second.

### Next in production

- Make the check and the write one statement: `UPDATE suppliers SET ..., version = version + 1 WHERE id = $1 AND version = $2`, and read the row count. Zero rows means stale (or gone). In this exercise one thread makes the read and the write atomic, and in production that `WHERE` clause is the whole mechanism.
- Use the HTTP forms the web already has: an `ETag` on every read, and `If-Match` on every write. Caches and generic clients understand them, and a missing `If-Match` is what 428 was made for.
- Give retries a bound and a backoff on the client, and watch the 409 rate. A rising rate means a hot record: that record's shape is wrong, or something is writing it too often.
- Consider a pessimistic lock where conflicts are the normal case, and retrying costs more than waiting. Optimistic locking is cheap only while conflicts are rare.
- Give stored answers a TTL longer than any client's retry window, and put them in the same transaction as the write they record. Otherwise a crash between them makes a successful write look unattempted.
- Use the `add` form wherever the arithmetic is the whole write: `SET value = value + $1 WHERE value + $1 >= 0`. A read-modify-write loop under load mostly produces 409s.
- Delete softly, as here, for as long as a client might hold an old version. If you must purge, keep the version counter somewhere, or use a fresh id.

### Correctness

Every write goes through `store.apply`, `store.create`, `store.delete` or `counters.write`, and those are the only places a version changes. Each of them moves it forward from the stored one, or leaves it, and a tombstone keeps the last one, so a version never goes back for a given id. So if `expectedVersion` equals the current version, then nothing has been written since the client read it, including a delete and a re-create.

Merging is safe for the fields it allows: a conflict is declared whenever a field in the edit has `lastChanged` above `baseVersion`, so a merge cannot overwrite a change its author did not see. The merged record is validated before it is written, so a merge cannot store a record that breaks the rule between fields. `status` always conflicts when stale, and a future `baseVersion` conflicts on every change, so neither reaches a merge.

The replay runs before the handler, so its answer depends only on the stored text and the fingerprint, not on any later state. The text was made at the moment of the first answer, so later writes can't change it. Only successes are stored, so a refused request has no stored answer, and a retry of it is judged afresh.

Each swap and add writes a new version, so a swap based on any read older than the latest write fails its check. So every update either lands or is refused, and none can be silently overwritten: the final value counts every update that answered 200.

### Complexity

- Time: O(s log s) per list request; O(1) per other request — a list sorts the suppliers, and everything else is one map lookup and a fixed number of fields. A body's size is bounded by the constraints.
- Space: O(s + c + q) — one entry per supplier, tombstones included, with its history of six fields; one per counter; and one stored answer per `requestId`.

### Trade-offs

- **Optimistic against pessimistic.** Optimistic costs nothing until there is a conflict, and then costs the client a retry. A lock costs every write a wait, and has to be released. Prefer optimistic when conflicts are rare and retrying is cheap.
- **Reject against merge.** Rejecting all stale writes is simple, and it annoys people who changed unrelated fields. Merging is friendlier, and it needs history and a rule per field. Here it is opt-in by route: `PUT` stays strict, and `PATCH` merges.
- **Field history against keeping old versions.** `lastChanged` is one number per field, and enough to detect a conflict. Keeping old versions would also let you show a diff and do a real three-way merge of text, at a much higher cost.
- **Storing only successes.** Storing every answer would make any retry return the same thing, which is what some payment APIs do. It also means a client can never fix and resend under the same id. Here a 409 is an answer about the moment, so it is not stored.
- **A version bump on a no-op.** Bumping on every save is simpler, and it fails anyone who read just before a harmless save. A counter's swap does bump on the same value, because there the version is the whole record of what happened.

### Pitfalls and edge cases

Each wrong approach below was run as a one-line change on the reference, through `cstudy submit`, and each fails the cases named with it.

**Stale writes.**

- **No check, or a check that passes a missing version.** The last save wins, silently, which is the bug the whole problem is about. Caught by `ex1`, `ex2`, `h3` and `h5`.
- **`Number(expectedVersion)` or `==`.** `"1"` passes as 1, and a client bug goes unseen. Caught by `h2`.
- **Refusing only when the version is lower.** A version nobody issued goes through. Caught by `h6`.
- **A version bump on every save.** A save that changes nothing makes everybody else's read stale. Caught by `h4`.
- **Checking the version before the fields.** The answer to a bad request depends on who else has written. Caught by `h7`.
- **Leaving the current record out of the 409.** The client has to read again, and may race again. Caught by `ex1` and `h3`.
- **Spreading the body into the record.** A client can set its own `version`. Caught by `h10`.

**Merging.**

- **Refusing every stale edit.** It's safe, and the level's point is that it isn't necessary. Caught by `ex3` and `h17`.
- **Merging everything.** That is last write wins with extra steps. Caught by `ex4`, `h17` and `h18`.
- **Letting `status` merge.** Caught by `h12` and `h18`.
- **`>=` on the field's version.** A field you had already seen conflicts with you. Caught by `ex3` and `h19`.
- **Checking the edit but not the merged result.** Each change was valid, and the record you store is not. Caught by `h13`.
- **Treating an identical value as a change.** Two people making the same fix get a conflict over nothing. Caught by `h15` and `h16`.
- **Applying the fields that do not conflict.** A half-applied edit is a state nobody asked for. Caught by `h17`.
- **Letting a version from the future merge.** `lastChanged > baseVersion` is never true for it. Caught by `h21`.
- **One "last changed" for the whole record.** Every stale edit then conflicts. Caught by `ex3` and `h19`.
- **Forgetting that a `PUT` changes fields too.** A stale merge overwrites what the `PUT` wrote. Caught by `h20`.
- **`key in someObject` as the allowlist.** `in` walks the prototype chain, so `constructor` passes. Caught by `h23`.

**Retries.**

- **No replay.** A write that worked is reported as a conflict, and the client tells the person it failed. Caught by `ex5` and `h26`.
- **Replaying without comparing the request.** A client bug gets someone else's answer. Caught by `ex6`, `h29` and `h34`.
- **A fingerprint of the raw text.** The same JSON with its keys in another order looks like a different request. Caught by `h28`.
- **A fingerprint of the body alone.** The same body on another supplier gets the first supplier's answer. Caught by `h29` and `h51`.
- **Storing failures.** A 409 sticks to that id forever, and the client can never recover. Caught by `h26`, `h27` and `h41`.
- **Replaying by handling the request again.** The answer is then about now, not about the first attempt. Caught by `h30`, `ex8` and `h54`.
- **Running the replay after the version check, or wrapping only some writes.** Caught by `ex5` and `h32`; `h31` for creates; `ex8` and `h44` for counters; `h50` for deletes.
- **Not checking the type of `requestId`.** Caught by `h33`.

**The counter.**

- **Comparing the value in a swap.** 5 to 6 and back to 5 looks unchanged, and a read from before it all goes through. Caught by `h36`.
- **A swap to the same value keeping the version.** Caught by `h37`.
- **An add that keeps the version.** A swap from an older read then erases the add. Caught by `h38` and `h39`.
- **Stopping silently at 0.** The amount is lost, and the client is told it worked. Caught by `h40` and `h41`.
- **Accepting `"1"` as an amount.** Caught by `h42`.

**Deletes.**

- **A delete with no version check.** It removes a record its author has not seen. Caught by `ex9` and `h55`.
- **Deleting the row, so a comeback restarts at 1.** A client holding an old version 1 overwrites the new supplier. Caught by `ex10`, `h45` and `h52`.
- **A comeback that keeps the old field history.** An old read merges into a record it has never seen. Caught by `h45`.
- **Leaving tombstones in the list, or readable.** Caught by `ex9`, `h53` and `h46`.
- **Finding the record before looking for the stored answer.** A retry after a delete answers 404, though the write worked. Caught by `h49` and `h50`.
- Project traps: `src/api.ts` must export `SupplierApi` by name; local imports need their `.ts` extension; `enum`, `namespace` and constructor parameter properties make Node refuse the file before any test runs.
