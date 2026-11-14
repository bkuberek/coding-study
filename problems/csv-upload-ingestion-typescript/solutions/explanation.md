# CSV Upload Ingestion (TypeScript): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | per file | per batch | default answer: each file streams into one transaction that first claims its upload, and its event is deleted only after the commit |

## How the project grows level by level

| Level | New requirement | What the code adds |
|-------|-----------------|--------------------|
| 1 | Load a file named by an event; delete the event only after the load; a file that is late is retried | `0002_imports.sql`, `src/ingest.ts` with its transaction, `importsOf` in `src/imports.ts`, and the consumer's `settled`, which deletes only what it finished |
| 2 | Rules per row, a report, mostly bad files, a file bigger than memory | `src/rows.ts`, `src/lines.ts`, which reads a chunk at a time, `src/load.ts` with its batches and its savepoint, and the report in `writeReport` |
| 3 | Duplicates, poison events, a crash halfway | Nothing new in the app: the claim at the start of the transaction was already the rule "once per upload", and a failed event was already left alone. `scripts/setup.ts` adds the dead-letter queue and the redrive policy |
| 4 | Events that are not a finished upload, and URL-encoded keys | `uploadIn` in `src/events.ts` answers nothing to load for a test event, a removal and a `.part` key, and decodes the key |

## Approach: reference (Stream each file into one transaction that claims its upload first, and delete the event only after the commit)

### Intuition

A queue promises to deliver each message at least once. It never promises exactly once, and it cannot know whether your work succeeded; it only knows whether you deleted the message before its visibility timeout ran out. So the service has two jobs that pull against each other: never lose an upload, which means deleting its event only after the work is safely done, and never load an upload twice, which means the work must recognize an event it has already finished.

Both come from one transaction per file. It begins by inserting the upload, its bucket, key and sequencer, into a table with a unique key on the three. It then loads every row and records the counts, and commits. If anything fails before the commit, whether a missing file, a dead connection or the process killed, the transaction rolls back, nothing of the file remains, and the event, never deleted, brings the whole file back. If the event arrives again after the commit, the insert finds the upload taken and the service deletes the event without loading anything. And if two deliveries race, the second insert waits on the unique key for the first transaction, then finds it taken.

The file's size is the other half. A 160 MB file does not fit in 128 MiB, so it is read as a stream: the S3 body is a Node stream, and pulling it a chunk at a time with `for await` asks for the next chunk only when the last one is used up. Lines are cut from chunks, rows are checked one by one, and good rows go to Postgres in batches of a few thousand, so neither memory nor round trips grow with the file.

The rest is reading the events honestly. S3 sends events that are not uploads, and encodes keys as a query string does. An event that is nothing to load is deleted, because leaving it would retry it until it lands in the dead-letter queue, which is for real failures.

### Say it out loud

"An event is deleted only after its upload is committed, so a crash loses nothing: the event comes back after its visibility timeout. Because it can come back, or come twice, the load starts by inserting the upload's bucket, key and sequencer into a table with a unique key, in the same transaction as the rows. A duplicate finds the key taken and changes nothing.

"The file is streamed: I read the S3 body a chunk at a time, cut lines, check each row and write good rows in batches with one `INSERT ... SELECT FROM unnest` per batch, summing each SKU within the batch since `ON CONFLICT DO UPDATE` may touch a row once per statement. If the file turns out mostly bad, I roll back to a savepoint taken before the rows and record it as rejected. The report goes to S3 before the commit, and the result is announced after it.

"A failing event is left alone; the queue's redrive policy moves it to the dead-letter queue after three receives. Test events, removals and `.part` keys are deleted with nothing loaded, and keys are URL-decoded first."

### Algorithm

1. Receive one event from `upload-events`, long-polling. While it is handled, extend its visibility by 3 seconds every second, so a long file is not delivered again meanwhile.
2. Read the event. A test event, an event that is not `ObjectCreated:*`, or a key that ends in `.part` is nothing to load: go to step 8. A body that is not an S3 event throws, so the event is left for the queue to retry.
3. Begin a transaction and insert the upload into `imports` with `ON CONFLICT DO NOTHING`. No row inserted means it was loaded before: commit nothing and go to step 8.
4. `GetObject`. `NoSuchKey` throws: roll back and leave the event.
5. Read the body a chunk at a time, cutting lines. The first line must be the header, or the outcome is `rejected` with the one report line `1,invalid_header`. Take a savepoint. Check each row; add good ones to a batch keyed by SKU, and write the batch when it holds 5000 lines; note each bad row's line and error.
6. If more than half the rows are bad, roll back to the savepoint: the file is `rejected`, with nothing loaded.
7. If anything was bad, put the report into `upload-reports` under the file's key. Update the import's status and counts, and commit. Send the result to `import-results`.
8. Delete the event. If any step threw, the event is not deleted: it comes back after 3 seconds, and the redrive policy moves it to `upload-events-dlq` after its third receive.

### Design

| File | Holds |
|------|-------|
| `migrations/0002_imports.sql` | `imports`, unique on bucket, key and sequencer, with the status and the counts |
| `scripts/setup.ts` | The buckets, the dead-letter queue first, then `upload-events` with its visibility timeout and a redrive policy naming the dead-letter queue's ARN, then `import-results`, then the migrations |
| `src/events.ts` | `uploadIn`: an `Upload`, nothing to load, or `MalformedEvent`; `decodedKey` |
| `src/lines.ts` | `linesOf`, an async generator that pulls chunks and yields lines, with a streaming `TextDecoder` |
| `src/rows.ts` | The header and the four row rules, in the statement's order |
| `src/load.ts` | `loadFile`: the savepoint, the batches, the counts and the report lines; `Batch` sums a SKU's lines and keeps the last description |
| `src/imports.ts` | `claim`, `finish` and `importsOf` |
| `src/ingest.ts` | `ingest`: the transaction around claim, read, load, report and finish, then the announcement |
| `src/consumer.ts` | The receive loop, the visibility extension, and `settled`, which decides whether the event is deleted |

The consumer handles one event at a time. That is the simplest way to keep memory flat, since one file streams at a time, and it is enough here; more throughput comes from more copies of the service, each reading the same queue, which the claim already makes safe.

### Correctness

An event is deleted only after `settled` returns true, which happens only after `ingest` returned, which is after the commit, or when the event is nothing to load. So every upload whose event is deleted was committed or deliberately skipped, and no upload is lost. Every row and the import row are written in one transaction, so after a crash at any point either all of a file is in the database with its import, or none of it is. A second delivery of an upload inserts the same `(bucket, key, sequencer)`; Postgres's unique index makes it wait for a concurrent first transaction and fail if that one committed, so each upload's rows are added once. A rejected file still commits its import row, so its duplicate is skipped too. Memory holds one chunk, one line, one batch of at most 5000 lines and the report lines, whatever the file's size. The result is sent after the commit, so a reader of the result finds the import and the rows already there.

### Complexity

- Time: per file — one pass over its lines, and one statement per 5000 lines
- Space: per batch — one chunk, one batch, and a line per bad row for the report

### Trade-offs

The visibility extension keeps a long file from being delivered a second time while it loads. Without it, a single consumer still works, since it receives nothing while it loads, but a second copy of the service would receive the same event after 3 seconds and wait on the claim, holding a connection, and the dead-letter count would tick up on a file that is merely slow. The cost is a request a second while a file loads.

The result is sent after the commit, as its own step, so a crash between the two leaves an import that is never announced: its event comes back, finds the import done, and is deleted. The fix is a transactional outbox: write the announcement into a table in the same transaction, and send it from there, retrying until it is sent. It is not built here, and the follow-ups ask about it.

One transaction per file is right for files of this size. For a file of many gigabytes, it holds a long transaction open, which keeps Postgres from cleaning up dead rows meanwhile; loading into a staging table in parts and switching it in at the end keeps the guarantee with shorter transactions.

The report lines are held in memory until the end, which is small for a file with a few bad rows. A mostly bad file of half a million rows would hold half a million short lines; a multipart upload to S3 as the file is read would keep that flat too.

### Pitfalls and edge cases

**Wrong approaches.** Each fails a hidden or visible case, and the failure names what it did. The first two were run against the real stack; the others follow from what the cases send.

| What it does | Why it is wrong | What catches it |
|--------------|-----------------|-----------------|
| Deletes the event as soon as it is received, then loads | A load that fails, or a process that dies, has already given the event up, so the file never loads | `h1`, where the event arrives before its file: `import_result step 2 POST http://aws:5000/: capture import_result from body.Messages.0.Body: the body has no body.Messages`. `v6` and `h22`, whose events never reach the dead-letter queue. `h25`, where the event is gone after the restart: `body: expected 2 elements, got 1` |
| Reads the whole body with `transformToString()`, or collects every chunk before splitting lines | The bulk file is 160 MB and the app has 128 MiB, so the app is killed for memory | `h17`: `AppExited`, exit code 137, and the remaining cases are `not_run` |
| Upserts a whole batch without summing a SKU's lines first | Postgres refuses the statement, `ON CONFLICT DO UPDATE command cannot affect row a second time`, so the file never loads | `v2`, whose file lists one SKU twice |
| Keeps no record of which uploads were loaded, or keys it by the SQS message id | A duplicate is a second message with its own id, so it loads again | `v5`: `no_import_result` receives a second result |
| Keys the record by the file's key alone | A new upload of the same key is skipped as a duplicate | `h20`: no result for the second upload |
| Records the upload in a transaction of its own before loading | After a crash halfway, the event comes back to an upload already marked done, and the second upload never loads | `h25` |
| Retries a failing event with no limit: no redrive policy, or a message sent back to the queue | The event cycles forever and never reaches the dead-letter queue | `v6`, `h22`: `capture dead_letter from body.Messages.0.Body` after 20 seconds |
| Makes a failed event visible again at once | Under the redrive policy, it spends its three receives in a moment and is dead-lettered before its file arrives | `h1`, from level 3 on |
| Treats a test event as malformed, or tries to load a removal | Each fails and is left on the queue, to be retried until it is dead-lettered | `v7`, `h32`: `upload-events` still holds the event, in flight |
| Loads a `.part` key | It loads a half-written file, then the finished one on top | `v8`: the `.part` has an import, and its result comes first |
| Accepts only `ObjectCreated:Put` | A renamed file arrives as `ObjectCreated:Copy`, and a large one as `ObjectCreated:CompleteMultipartUpload` | `v8`, `h31` |
| Reads the key from the event as it is | `north+depot` is `north depot` in the bucket, and reading the encoded key fails with `NoSuchKey` until the event is dead-lettered | `h30` |
| Decodes each chunk with `chunk.toString()` | A byte order mark stays in front of the header, and a character split across two chunks comes out broken | `h15`: the file is rejected for `invalid_header` |

**Edge cases.**

- A file with only its header is loaded with 0 rows (`h7`); an empty file has no header and is rejected (`h14`).
- An empty line in the middle of a file is a row with one field, `wrong_column_count`; a line break at the very end is not a row (`h6`, `h10`).
- Exactly half bad is not mostly bad (`h12`); a row is reported once, for its first broken rule (`h11`).
- A description of exactly 300 characters and a quantity of exactly 100000 load; 301 and 100001 do not, and neither do `+5`, `1.0` and `007` (`h10`).
- A file with nothing bad gets no report (`h16`); a rejected file is still recorded and announced, and its duplicate is skipped (`h23`).
- The bulk file repeats 100 SKUs over 550000 rows, so a batch of 5000 lines writes 100 rows, and the whole file takes 110 statements; it loads in a few seconds here. One statement per row would take 550000 round trips against the case's 40 seconds.
- The restart in `h25` keeps the data: the bulk file is in the stock twice afterwards, once from `h17` and once from the upload `h24` sent, whether the restart landed before or after that load committed. An app that commits as it goes, or marks the upload done before loading, shows it only when the restart lands in the middle of the load, which is where it lands here.
- A file deleted after it was loaded keeps what it loaded, and its removal event is deleted without a result (`h32`).
