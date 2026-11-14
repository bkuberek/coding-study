# Debug: Async Batch (TypeScript): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | O(n) per batch | O(n) | default answer: a `for...of` loop that awaits each write, then awaits the audit entry |

## How the project grows level by level

| Level | New requirement | What the code adds |
|-------|-----------------|--------------------|
| 1 | Report finished only when finished | `for...of` in place of `forEach`, and an `await` on the audit entry |
| 2 | Bad rows and double starts | `try`/`catch` around the awaited write, a list of failed rows, and a guard at the top of `importAll` |

## Approach: reference (A for-of loop that awaits each write)

### Intuition

`forEach` calls its callback and throws away what the callback returns. An `async` callback returns a promise, so `forEach` starts every write and moves on. The `await` inside the callback is real, but it pauses only that callback, not `importAll`. So when control returns, nothing has been written, `saved` is still 0, and the function reports `finished` with a count of 0. The writes finish later, unobserved, and all at the same time, on a store that takes one at a time.

The second bug is simpler and just as common: `this.#audit.record(...)` returns a promise that nobody awaits, so its failure and its timing belong to no one.

Neither is a type error. `forEach` accepts a function returning anything, and an unused promise is a legal expression. A lint rule catches them, and the compiler doesn't.

### Say it out loud

"`forEach` doesn't await its callback: it ignores the promise an `async` function returns. So this fires everything off, and then reports done. `await` only suspends the enclosing function, so it needs to be in `importAll` itself. I'd use `for...of` for one at a time, or `await Promise.all` over a `map` for all at once. And anything returning a promise that I care about must be awaited, or its errors and its timing are lost."

### Debugging approach

1. **Measure.** Log the time before and after the loop, and it takes no time. A loop of awaited writes can't take no time.
2. **Read what the loop does with the callback's result.** `forEach` ignores it.
3. **Ask of each call that returns a promise: who awaits this?** That finds the audit entry as well.
4. **Check the half-fixes.** `await Promise.all(skus.map(...))` waits, but it writes in parallel on a store that can't take it, which `@now` shows (`ex1`), and so does `savedSkus` at 250 ms (`h2`). `for...of` without an `await` on the write is no better (`ex1`). Awaiting the writes and not the audit returns at 300 ms with an empty log (`h3`).

### Algorithm

1. If a batch is running, return `-1`. This check and the next line have no `await` between them, so nothing can slip in.
2. Set the state to `running`.
3. For each SKU in order: await the write inside a `try`. Count it if it worked, and remember it as failed if it was rejected.
4. Await the audit entry, set the state to `finished`, and return the count.

### Design

| File | Responsible for |
|------|-----------------|
| `src/importer.ts` | `BatchImporter`: the order of the writes, what counts as saved, the state and the guard. The only file that changes |
| `src/shelfStore.ts` | `ShelfStore`: a write that takes time and may reject |
| `src/auditLog.ts` | `AuditLog`: an entry that takes time |

What a senior engineer would do next in production:

- Turn on `no-floating-promises` and `no-misused-promises`, which flag both of these bugs at the line they are written.
- Decide what happens when the process dies in the middle: which rows were written, and how a retry avoids writing them twice.
- Use `Promise.allSettled` with a concurrency limit, if the store can take parallel writes, because plain `Promise.all` rejects on the first failure while the rest keep running.
- Make the double-start guard real: an in-memory flag protects one process, and two processes need a lock or a unique "running job" row.

### Correctness

Each iteration of the `for...of` suspends `importAll` until that write has settled, so writes happen strictly one after another, in order, and the clock reaches `n * 100` before the audit entry starts. `saved` is read after every write has settled, so the entry and the return value are right. The state changes only after the audit entry, so `finished` is never visible early.

The `try` encloses an `await`, so a rejection arrives inside it, and the row is recorded as failed while the loop continues.

The guard is checked and the state set with no `await` between them, and JavaScript runs one piece of code at a time between `await`s, so two calls can't both pass the guard.

### Complexity

- Time: O(n) per batch — one awaited write per SKU, and one audit entry.
- Space: O(n) — the saved and the failed SKUs.

### Trade-offs

- `for...of` is right when order matters or the other side takes one at a time. `await Promise.all(skus.map(...))` is right when they can run together, and it finishes in `100 + 50` ms here, but it would write in parallel, and the first rejection would make it reject while the others keep running.
- `reduce` with a chain of `.then` also runs one at a time, and it is harder to read and to put a `try` around.
- Resolving with `-1` for a double start keeps `importAll` total, and suits this exercise. A real API would more likely answer a 409, or return the running job's id.

### Pitfalls and edge cases

Each wrong approach below was run against the hidden cases named with it, and each fails them.

- **`forEach`, `map` or `filter` with an `async` callback and nothing awaiting the result.** Caught by `ex1` and `ex2`.
- **`Promise.all` over a `map`.** It waits, but everything runs at once. Caught by `ex1` and `h2`.
- **Awaiting the writes but not the audit entry.** Caught by `ex1` and `h3`.
- **Setting `finished` before the audit entry is written.** Caught by `h3`.
- **Counting before the write has happened.** Caught by `ex3` and `h8`.
- **A `try` around the whole loop.** The first bad row ends the batch. Caught by `ex3` and `h9`.
- **`try { this.#shelf.save(sku); } catch {}`, with no `await`.** The `try` has been left by the time the promise rejects, so nothing catches it, and in Node an unhandled rejection ends the process. Caught by `ex3`.
- **No guard, or a guard on the wrong state.** Two batches then run together. Caught by `ex4`.
- **A guard that never resets, or that resets only on success.** Caught by `h12` and `h13`.
- Project traps: `src/importer.ts` must export `BatchImporter` by name; local imports need their `.ts` extension; keep `tests/virtual-clock.ts` as it is.
