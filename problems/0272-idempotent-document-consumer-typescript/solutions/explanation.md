# Idempotent Document Consumer (TypeScript): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | O(b + t) per delivery | O(k + d) | default answer: the effect and its key commit together, and the ack goes last |

Here `b` is the length of the body, `t` the size of the tables (the in-memory transaction copies them, a real database would not), `k` the number of work keys and `d` the number of documents.

## How the project grows level by level

| Level | New requirement | What the code adds |
|-------|-----------------|--------------------|
| 1 | Duplicates | A check before the work, and a table it reads |
| 2 | Content plus version | `src/worker/workKey.ts`; the table holds extractions, not ids, and "already done" still publishes |
| 3 | Out of order | `supersedes`, checked before anything else, and writing nothing |
| 4 | Poison | The dead-letter table and `deadKeys`; a narrow `catch` around the extraction; the broker's count |
| 5 | Crashes | Nothing new in the logic, if the writes were already one transaction. The handler keeps no state, and the ledger, the document and the key move into one `transaction` |

## Approach: reference (One transaction for the effect and its key with the ack sent last)

### Intuition

At-least-once delivery cannot be turned into exactly-once delivery by anything on your side of the network. What you can build is an exactly-once **effect**: the handler may run many times, and the world changes once. That takes three things, and each level removes one of them from the naive version:

1. **A key that names the work, not the message.** A broker id names a message, and a publisher's retry is a new message. Hash what makes the work the same: the input and the code that reads it. Bump the version, and the key changes on purpose.
2. **The key and the effect commit together.** If the effect lands and the key does not, the redelivery pays again. If the key lands and the effect does not, the work is lost forever and nobody is told. There is no safe order for two commits, only one commit.
3. **The ack goes after the commit.** Ack first and a crash loses the work. Ack last and a crash means a redelivery, which the key absorbs. The whole design exists to make the second failure harmless, because you cannot prevent it.

The trap that catches good engineers is treating "seen" as one question. It is two: **has this work been paid for?** (the extraction table) and **does this document show the newest result?** (the document row). A document that goes back to old text answers yes to both, and an early `return` on "seen" leaves it showing the wrong thing.

### Say it out loud

"Exactly-once delivery isn't on offer, so I'm building at-least-once delivery with an idempotent effect. I need a key for the work: not the broker's message id, because a publisher retry gets a new one, but a hash of the content and the pipeline version, so a version bump is deliberately new work.

"I write that key in the same transaction as the effect. Two commits have a gap whichever way round I put them: effect first pays twice, and key first loses work silently. Then I ack last, so a crash after the commit is just a redelivery, and the key handles it.

"Ordering is a separate check from dedupe. I compare revision then version per document, and a late message writes nothing at all. I have to be careful there: if I record a late message as seen, a later revision with the same text gets skipped.

"For poison I use the broker's delivery count rather than my own counter, because a message that kills my process never reaches my `catch`. And a parse failure goes straight to the dead-letter list, because retrying can't fix it."

### Algorithm

1. Parse. A `MalformedDelivery` goes to the dead-letter list at once, and is acknowledged.
2. Compute the key from the body and the pipeline version, with a separator between them.
3. Read the document. If this delivery does not supersede what it shows, acknowledge and stop. Nothing is written.
4. If the key is dead, acknowledge and stop.
5. If the key has an extraction, publish it to this document in a transaction, acknowledge and stop. No charge.
6. If the delivery count is over the limit, dead-letter it without trying.
7. Extract, in a `try` around the extraction alone. On failure: below the limit answer `retry`, at the limit dead-letter it.
8. In one transaction: save the extraction under its key, add the ledger line, publish to the document.
9. Answer `ack`. Crash point `before-ack` sits in `DocumentConsumer.deliver`, after the handler has returned.

### Design

| File | Responsible for |
|------|-----------------|
| `src/consumer.ts` | `DocumentConsumer`: the process. Owns the `Database` and the `Faults`, which survive `restart`, and replaces the handler, which does not. Turns `ProcessCrash` into `crashed` |
| `src/worker/handler.ts` | `DeliveryHandler`: the order of the checks, and the one transaction per outcome. It has no field that holds state, so a restart loses nothing |
| `src/worker/workKey.ts` | What makes two pieces of work the same |
| `src/worker/delivery.ts` | Untrusted text to a typed `Delivery` or `MalformedDelivery`. Unchanged from the starter |
| `src/extraction/extractor.ts` | The paid step, kept outside the transaction: in production you would not hold a database transaction open across it |
| `src/storage/database.ts` | The tables: `documents`, `ledger`, and now `extractions`, `deadLetters` and `deadKeys`. `transaction` is the only way to write |
| `src/storage/documentIndex.ts`, `src/storage/ledger.ts` | Reads. Their own `transaction` calls are gone, because a repository that commits for itself can't join a bigger commit. That is the actual design change of level 5 |
| `src/runtime/faults.ts` | The test's switches. Unchanged |
| `tests/workKey.test.ts` | That the key separates its two parts |

Why does the handler read before the transaction, and then write in a second step? Because the extraction is slow and paid for. Holding a transaction across it would hold locks for the length of a remote call. In a real database, two workers can both read "not done" and both extract: the unique index on the key then makes one of them fail its commit, which it treats as a duplicate. You pay twice in that narrow race, and you never publish or charge twice, and that is a trade-off worth saying out loud.

### Next in production

- Make the key a `UNIQUE` column, and write it with `INSERT ... ON CONFLICT DO NOTHING`, then check the row count. In memory one thread hides the race between two workers. In production that index is what closes it.
- Decide how long keys live. A key only has to outlast the longest a duplicate can arrive, which is the broker's retention plus the publisher's retry window. Past that, expire it, and write down the number.
- Send your own key to anything outside your transaction. An extraction vendor's invoice can't join your commit, so pass it the work key as an idempotency key, or accept the double-charge window and reconcile. Say which.
- Alert on dead-letter depth and age, and build the replay tool before you need it. An unread dead-letter list is just silent data loss with extra steps.
- Rate-limit a version bump. Reprocessing the whole archive through the same queue starves live traffic, so give it a separate queue and a budget.
- Extend the visibility timeout (or heartbeat) during long extractions, or the broker redelivers to a second worker while the first is still working.
- Measure redelivery rate and duplicate-hit rate. A rise in either is the first sign of a broker or consumer problem.

### Correctness

Every delivery ends in exactly one of: no writes (late, dead, retry), one commit of the document alone (work already done), one commit of the extraction, ledger line and document together (new work), or one commit of the dead letter and its key together.

So consider any crash. Before a commit: nothing of this delivery landed, so the redelivery sees the state the first delivery saw, and does the same thing. After the commit, or before the ack: everything landed, so the redelivery finds the key (or sees that it is no longer newer) and writes nothing. No crash point can separate the ledger line from the key, so the ledger holds at most one line per key. And any delivered, non-late, non-dead work eventually commits or is dead-lettered, so it holds at least one, if the broker keeps delivering.

The late check comes first and writes nothing, so a late message can't mark its key as done. `supersedes` compares `revision` first, as numbers, so a higher version of an old revision is still late.

The dead-letter limit is checked after "already done", so a message whose acks were lost is not declared dead. It reads the broker's count, which a crash cannot reset.

### Complexity

- Time: O(b + t) per delivery — hashing and extracting read the body, and the in-memory `transaction` copies the tables. A real database would make the second term a few index lookups.
- Space: O(k + d) — one extraction or dead key per piece of work, and one row per document, plus one ledger line per extraction.

### Trade-offs

- **Dedupe table against a natural upsert.** If an effect is a pure overwrite keyed by document, you may not need a dedupe table at all. Here the ledger is an append, which is not idempotent, so it needs the key. Ask which of your effects are which.
- **Broker count against your own durable counter.** The broker's count is free and survives your crashes, but on some brokers it is approximate. A durable `attempts` row is exact and costs a write before each attempt.
- **Three attempts then dead letter against backoff.** Here the broker decides when to redeliver. Most systems also delay the redelivery, because retrying an outage three times in one second helps nobody.
- **Sharing an extraction between documents.** Keying on content alone saves money across documents, and it also means two customers' identical scans share one result row. That is fine for pages and words, and it would not be fine if the result held anything customer-specific. Then the customer belongs in the key.
- **Skipping late revisions.** It saves money and loses history. If someone needs to read old revisions, then a late delivery should be processed and stored, and only the "current" pointer should ignore it.

### Pitfalls and edge cases

Each wrong approach below was run as a one-line change on the reference, through `cstudy submit`, and each fails the cases named with it.

- **Keying on the message id.** A copy under a new id pays again. Caught by `h5` and `h7`, and at level 2 alone by `ex3`, before the ordering check of level 3 hides it for a single document.
- **Keying on the delivery's whole text.** Its `deliveryCount` changes, so a copy never matches. Caught by `h5` and `h10`.
- **Putting the document id in the key.** The same scan under another document pays twice. Caught by `h5`.
- **Keying on the body alone.** A version bump does nothing. Caught by `ex4`, `h8` and `h9`.
- **Running the text and the version together, either way round.** `("Form-1", 2)` and `("Form-", 12)` make the same string, and so do `(1, "2-Form")` and `(12, "-Form")`. Caught by `h6`.
- **Returning early when the work is done.** The document never moves. Caught by `h5`, `h10` and `ex6`.
- **Letting a late message record its key.** A later revision with that text is then skipped. Caught by `h14`.
- **Last write wins.** Whatever arrives last replaces the document. Caught by `ex5`, `h11` and `h17`.
- **Comparing the version before the revision.** A reprocess of an old revision beats a new revision. Caught by `h11` and `h13`.
- **Comparing the revision alone.** A higher version of the same revision is never published. Caught by `ex4` and `h8`.
- **Comparing revisions as text.** `"9"` sorts after `"10"`. Caught by `h18`.
- **Giving up one delivery early.** Dead-lettering at count 3 without trying throws away the last chance. Caught by `h28`.
- **Retrying once past the limit.** The third failure answers `retry`, so nothing is ever dead-lettered. Caught by `ex7` and `h22`.
- **Retrying a malformed delivery.** It will never parse. Caught by `h20` and `h21`.
- **Trying again past the limit.** A message that kills the process keeps killing it. Caught by `h25` and `h36`.
- **Counting attempts in the process.** A message that kills the process never reaches the counter, and the count starts again after every restart. Caught by `h25`, `h36` and `h38`.
- **Checking the limit before "already done".** Finished work is dead-lettered. Caught by `h30`.
- **Forgetting dead work.** A copy tries again and adds a second entry. Caught by `h24` and `h37`.
- **A dead key that ignores the version.** A fixed pipeline can never rescue the scan. Caught by `h23`.
- **Charging before the extraction returns.** A failure that will be retried has already cost money. Caught by `ex8`, `h27` and `h28`.
- **Charging in a transaction of its own.** The commit that lands first is only the charge, so the redelivery pays again. Caught by `ex9` and `h32`.
- **Recording the key in a transaction of its own, first.** The work is marked done and the charge and the result are lost. Caught by `ex9`, `h32` and `h40`.
- **Publishing in a transaction of its own, last.** It heals on redelivery, but a reader sees a charge with no result, and the rule says they land together. Caught by `h32`.
- **Remembering keys in a field of the handler.** They die with the process. Caught by `h32` and `h41`.
- **Treating a crash as a failure.** A broad `catch` that answers `retry` to `ProcessCrash`, or runs the commit inside the extraction's `try`, tells the broker something a dead process cannot. Caught by `ex9`, `ex10` and `h33`.
- Project traps: `src/consumer.ts` must export `DocumentConsumer` by name; local imports need their `.ts` extension; `enum`, `namespace` and constructor parameter properties make Node refuse the file before any test runs.
