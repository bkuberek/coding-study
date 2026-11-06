# Debug: Async Batch (TypeScript)

## Statement

A nightly job imports a batch of products into a store and writes one audit entry. Operations noticed that the job reports `finished` within a millisecond of starting, with a count of 0, and that the audit trail says `imported 0 of 3`. The products do turn up in the store, a little later. The code type-checks, and it looks like it awaits what it should. Find the bugs and fix them.

### Bug report

> **Title:** The import says it finished before it started
>
> The dashboard shows `finished` for a batch still being written, so the downstream job reads half a catalog. The count in the log is always 0. Last week a store write failed, and the whole job died instead of skipping that row.

## Input

- `new BatchImporter()`: an importer with an empty store.
- `skus`: the products of a batch, in the order they must be written.

## Output

Each method returns what its level describes.

## Project

`cstudy start` copies the importer into `projects/debug-async-batch-typescript/`:

- `src/importer.ts`: the class `BatchImporter`, exported by name, where the bugs are.
- `src/shelfStore.ts`: `ShelfStore`, the store. It takes writes one at a time, and each write takes 100 ms.
- `src/auditLog.ts`: `AuditLog`. An entry takes 50 ms to reach it.
- `tests/virtual-clock.ts`, the grader's clock, which must stay as it is, and `tests/level-<n>.test.ts`: the examples of each open level as `node:test` tests, written when the level opens and never rewritten.
- `README.md`, `package.json` and `tsconfig.json`.

`cstudy test debug-async-batch-typescript` runs your tests, and so does `node --test` in the project folder; either run is feedback only, and `cstudy test --typecheck` also type-checks the project. `cstudy submit debug-async-batch-typescript` grades every case of the open levels, hidden ones included, and opens the next level when they all pass. Each submission grades the earlier levels again.

## Level 1: Finished means finished

- `importAll(skus)`: writes each SKU to the store, in order, one at a time, because the store takes one write at a time. Then it writes the audit entry `imported <saved> of <total>`. Only then does its promise resolve, with the number of SKUs saved.
- `state()`: `idle` before the first batch, `running` from the moment `importAll` is called until the audit entry is written, then `finished`.
- `savedSkus()`: the SKUs in the store, in the order they were written.
- `auditLog()`: the audit entries, in the order they were written.

So a batch of `n` SKUs takes `n * 100 + 50` ms.

### Example 1

<!-- case: ex1 -->

Three writes of 100 ms and one audit entry of 50 ms: the batch ends at 350 ms, having saved 3.

### Example 2

<!-- case: ex2 -->

At 150 ms the first write is done and the second is under way, so the importer is still `running`. Waiting for the batch moves the clock to 250 ms.

## Level 2: Bad rows and double starts

Two more rules, for the same method.

**A rejected row is skipped.** The store rejects a SKU that starts with `bad-`, after the same 100 ms. That row counts as not saved and the batch goes on with the next one. The audit entry and the promise's value count only what was saved. `failedSkus()` returns the rejected SKUs of every batch so far, in order.

**A second batch is refused.** A call to `importAll` while a batch is running writes nothing and resolves at once with `-1`, leaving the running batch alone. Once a batch is finished, a new one can start.

### Example 1

<!-- case: ex3 -->

`bad-1` takes its 100 ms and is rejected, and `c` still gets written. The batch saved 2 of 3.

### Example 2

<!-- case: ex4 -->

The second call arrives while the first is running. It answers `-1` at once, at time 0, and the first batch carries on and ends as usual.

## Constraints

- At most 100 SKUs per batch and 20 calls per test.
- A SKU is 1 to 20 lowercase letters, digits or `-`.

## Follow-ups

- The store can take writes in parallel after all, up to 5 at a time. What would you change, and what would `Promise.all` do when one write rejects?
- Your process is killed at 150 ms. What has been written, what does the audit trail say, and how would a retry avoid writing the first SKU twice?

## Hints

### Hint 1

Put a `console.log(Date.now())` before and after the `forEach`. How long does it take? What does `forEach` do with the promise that an `async` callback returns?

### Hint 2

An `await` pauses the function it is in, and nothing else. Which function is the `await` in the loop inside?

### Hint 3

The loop is not the only thing that isn't waited for. Read the line after it, and look up what `AuditLog.record` returns.

### Hint 4

`try { save(x); } catch {}` catches nothing that `save` rejects with, unless the call is awaited: by the time the promise rejects, the `try` has long been left.
