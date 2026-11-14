# Idempotent Document Consumer (TypeScript)

## Statement

Scanned documents reach an extraction service through a queue that delivers at least once. So any message can arrive twice, or late, or just as the process that holds it dies. Reading a scan is billed per page, so a consumer that repeats work pays for it, and one that loses work leaves a customer looking at an old document.

You inherit a consumer that works on a good day. Each level takes away one more assumption about the good day, and the design has to survive all of them at once.

All the documents and numbers here are invented.

The queue is not real: a test plays the broker. It calls `deliver` with the text of a delivery, decides what to deliver next, and reads the database through the other methods.

## Input

- `new DocumentConsumer()`: a consumer with an empty database. Each test gets a new one.
- `delivery`: the text of one delivery. It should be a JSON object with these fields, all of them required:

| Field | Meaning |
|-------|---------|
| `messageId` | The broker's name for the message. A redelivery of a message carries the same id |
| `documentId` | The document this message is about |
| `revision` | The document's revision, a whole number from 1, given by whoever uploaded it. A new upload has a higher revision |
| `pipelineVersion` | The version of the extraction code that should read this scan, a whole number from 1 |
| `body` | The text of the scan, not empty, with pages separated by `\|` |
| `deliveryCount` | How many times the broker has delivered this message, 1 on the first |

## Output

`deliver` returns what the broker should do: `ack` means it is done with this message and can forget it, and `retry` means it should deliver the message again later. The other answers come with their level.

`document(documentId)` returns the document as JSON text with sorted keys, or `""` for a document it has never published:

```json
{"documentId":"D-1","pages":2,"pipelineVersion":1,"revision":1,"words":4}
```

`ledger()` returns one line per extraction paid for, oldest first, as `<documentId> v<pipelineVersion> <pages>p`: `D-1 v1 2p`. The invoice is reconciled against it, so a line too many is money, and a line too few is a dispute.

## Project

`cstudy start` copies the consumer into `projects/idempotent-document-consumer-typescript/`:

- `src/consumer.ts`: the class `DocumentConsumer`, exported by name, which must stay there.
- `src/worker/`: `parseDelivery` and `DeliveryHandler`.
- `src/extraction/extractor.ts`: `Extractor`, the paid step. It counts pages and words, and fails on a scan whose text starts with `%%`, as it would on a corrupt file.
- `src/storage/`: `Database`, with `read` and `transaction`, and the two tables on top of it.
- `src/runtime/faults.ts`: `Faults`, the switches that make things fail on cue.
- `tests/storage.test.ts`: tests of those pieces, and `tests/level-<n>.test.ts`: the examples of each open level as `node:test` tests, written when the level opens and never rewritten.
- `README.md`, `package.json` and `tsconfig.json`.

`Database.transaction(work)` runs `work` on a private copy of the tables. When `work` returns, all of its writes land together. When it throws, none of them do. Add a table by adding it to `Tables` and `emptyTables`.

`cstudy test idempotent-document-consumer-typescript` runs your tests, and so does `node --test` in the project folder; either run is feedback only, and `cstudy test --typecheck` also type-checks the project. `cstudy submit idempotent-document-consumer-typescript` grades every case of the open levels, hidden ones included, and opens the next level when they all pass. Each submission grades the earlier levels again, so a later change must keep their rules. Node runs the files by stripping their types, so write no `enum`, no `namespace` and no constructor parameter properties, and import your own files with their `.ts` extension.

## Level 1: A duplicate changes nothing

The starter extracts and charges for every delivery. Fix that: a message delivered more than once is acknowledged every time and applied once. The redelivery has the same `messageId` and a higher `deliveryCount`, so its text is not the same as the first delivery's. A redelivery leaves the ledger and the document as they were.

### Example 1

<!-- case: ex1 -->

The second delivery is the same message at count 2. It answers `ack`, and the ledger has one line.

### Example 2

<!-- case: ex2 -->

Two messages about two documents are two extractions. A document nobody has sent reads as `""`.

## Level 2: The key is content plus version

A week in production shows that a `messageId` was the wrong key. When the uploading service times out, it publishes again, and that makes a new message with a new id and the same scan, which we pay for twice. And when the extraction code improves, the team wants to run old scans through it again, which a "seen" check on text alone would refuse.

From now on, what identifies a piece of work is **the body and the pipeline version together**, and the message id decides nothing. For each delivery:

- **Work not done yet** (no extraction of this body at this version): extract, charge, and publish the result to the document.
- **Work already done** (this body at this version was extracted before, under any message and any document): do not extract and do not charge, and the document still gets its result. The extraction you already paid for has the `pages` and `words`.

The document shows the `revision` and `pipelineVersion` of the delivery that published to it. A delivery that is the same revision and version a document already shows changes nothing.

The ledger line of an extraction names the document it was first done for.

### Example 1

<!-- case: ex3 -->

`m-2` is the publisher's retry of `m-1`: new id, same body, same version. No second line in the ledger.

### Example 2

<!-- case: ex4 -->

The same body at version 2 is new work, so the ledger gets a line for it, and the document shows version 2.

## Level 3: Out of order

Nothing promises that messages arrive in the order they were sent. A document must end up showing its newest result, whichever arrived last.

For one document, compare `revision` first, and within a revision compare `pipelineVersion`. A delivery that does not come after what the document already shows is **late**: answer `ack`, do no work, pay nothing, change nothing, and record nothing about it. A late scan is not a scan nobody needs: if a later revision has that same text, it is work that has not been done.

A delivery that does come after what the document shows follows level 2's rules, whether its work is new or already done.

### Example 1

<!-- case: ex5 -->

Revision 2 arrives first. Revision 1 is late, so we do not pay to read a scan nobody will see.

### Example 2

<!-- case: ex6 -->

Revision 3 goes back to the text of revision 1. We have already paid for that text, so the ledger stays at two lines. But the document has to show it: the answer to "has this work been done?" is yes, and the answer to "does the document need it?" is also yes.

## Level 4: Poison messages

A message that can never succeed must not be retried forever and must not hold up the ones behind it.

`failExtractions(times)` makes the next `times` extractions fail, whatever their text, as an outage of the extraction service would. Pass it to `Faults.failExtractions`. `deadLetters()` returns the dead-letter list, oldest first. Each entry is `<reason> <delivery text>`, with the text as it arrived, so that someone can replay it.

| What happens | Answer | Dead letter |
|--------------|--------|-------------|
| The delivery is malformed: `parseDelivery` throws `MalformedDelivery` | `ack`, at once, because trying again cannot help | `malformed` |
| The extraction fails and `deliveryCount` is below 3 | `retry` | None |
| The extraction fails and `deliveryCount` is 3 | `ack` | `retries_exhausted` |
| The work is not done and `deliveryCount` is above 3 | `ack`, without trying: earlier deliveries got their chance | `retries_exhausted` |

A failed extraction pays nothing and publishes nothing.

Once work is dead-lettered, another delivery of the same body at the same version is answered `ack` with no attempt and no second entry, under any message and any document. A new pipeline version is new work, and gets its own chances.

Dead-lettering is about work that has not been done, and the earlier checks still come first. A late delivery is late, and work that is already done is done, whatever their `deliveryCount`.

### Example 1

<!-- case: ex7 -->

A scan that starts with `%%` fails each time. The third delivery uses the last chance, so it goes to the dead-letter list and is acknowledged, and nothing else happened.

### Example 2

<!-- case: ex8 -->

The service failed once. The redelivery works.

## Level 5: A crash before the ack

The process can die anywhere. The broker hears nothing from a dead process, so it delivers the message again, with a higher count, to the next one.

`crashAt(point)` arms one crash, at one of these points:

| Point | What it stands for |
|-------|--------------------|
| `before-commit` | The next transaction to commit dies first, so none of its writes land |
| `after-commit` | The next transaction to commit does so, then the process dies |
| `before-ack` | The next `deliver` finishes all of its work, then the process dies before the broker hears the answer |

`Database.transaction` already reaches the first two, through `Faults`. Pass `crashAt` to `Faults.armCrash`, and call `crashIfArmed("before-ack")` in `deliver` just before it answers.

When the process dies during a `deliver`, `deliver` answers `crashed`. `ProcessCrash` stands for `kill -9`, which no real code could catch, so a broad `catch` has to let it pass.

`restart()` starts a new process over the same database: it replaces everything except the `Database` and the `Faults`, and nothing that was only in memory survives. A test reads `ledger`, `document` and `deadLetters` before or after the restart, straight from the database. It always restarts before the next `deliver`.

One delivery makes at most one transaction that matters: all of a delivery's effects land together or none of them do, so that no crash point can leave half of them behind.

### Example 1

<!-- case: ex9 -->

The commit landed and the broker never heard. The redelivery at count 2 finds the work done and pays nothing.

### Example 2

<!-- case: ex10 -->

The process died before the commit, so nothing landed, and the redelivery does the work. It pays once.

## Constraints

- At most 40 calls per test.
- A `body` is at most 200 characters.
- A document's revision and version pair always has the same body.
- The limit of 3 deliveries is fixed.
- A case runs in one thread, with no two deliveries at the same time.

## Follow-ups

- Two workers receive the same message at once, both before either commits. What does your database have to offer, and what would the second worker do?
- The dedupe table grows forever. How long must you keep a key, and what decides that?
- The extraction service charges its own invoice, on its own side of the network. Your transaction cannot include it. What can you send it, so that a crash between its work and your commit does not pay twice?

## Hints

### Hint 1

A broker's message id names one message. Does it name one piece of work? What would a publisher's retry look like?

### Hint 2

Two different questions hide in one "have I seen this?" check: has this work been done, and does this document show it yet? Different answers lead to different writes.

### Hint 3

Run the text and the version together with no separator, and work out which two messages then look the same.

### Hint 4

A message that kills the process never reaches your `catch`, so a retry count kept in your process stays at zero. Who else knows how many times this message was delivered?

### Hint 5

For each crash point, ask what is durable and what the next process will do when the same message arrives. If the answer depends on which of your writes landed first, those writes belong in one transaction.
