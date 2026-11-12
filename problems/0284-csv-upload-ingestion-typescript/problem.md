# CSV Upload Ingestion (TypeScript)

## Statement

A wholesaler's suppliers send a delivery file with every truck: a CSV with one row per product line, saying how many of each item arrived. Each supplier uploads its file to an S3 bucket, and S3 puts an event for each upload on an SQS queue. A service takes those events off the queue, reads each file, checks every row, and adds what arrived to the stock it keeps in Postgres.

That is a few lines of code on a quiet day. Then a supplier uploads a file of 160 MB, bigger than the service's memory. Another sends a file that is mostly garbage. The queue delivers the same event twice, as SQS may. An event names a file that will never be there and fails forever. The service is restarted halfway through a long file. And the bucket sends events for things that are not finished uploads at all.

Build the ingestion service in levels. `cstudy` runs your app with Postgres and with S3 and SQS emulated locally, in a Docker sandbox, and judges it by what your API answers, by what lands in the buckets and the queues, and by what does not. The wholesaler, its suppliers and their products are invented.

## Input

Events on the queue `upload-events`, one S3 event per message, as S3 writes them:

```json
{"Records": [{"eventVersion": "2.1", "eventSource": "aws:s3", "awsRegion": "us-east-1",
  "eventTime": "2027-03-01T09:00:00.000Z", "eventName": "ObjectCreated:Put",
  "s3": {"s3SchemaVersion": "1.0", "bucket": {"name": "uploads", "arn": "arn:aws:s3:::uploads"},
         "object": {"key": "deliveries/v1/2027-03-01.csv", "sequencer": "0001"}}}]}
```

Real events carry more, such as the object's size and ETag; your service needs the bucket, the key and the sequencer. S3 gives every upload of a key a new sequencer, so an upload is its bucket, key and sequencer together, and the same event delivered twice names the same three.

Each event names a delivery file in the bucket `uploads`. Its first line is the header, and each line after it is a row:

```text
sku,description,quantity
BOLT-M6,Hex bolt M6 x 30 mm,1200
NUT-M6,Hex nut M6,800
```

No field is quoted, and no field holds a comma. A line may end with `\n` or `\r\n`, and the last line may have no line break after it.

## Output

Over HTTP, JSON with `Content-Type: application/json`:

- `GET /products/{sku}`: 200 with `{"sku": "BOLT-M6", "description": "Hex bolt M6 x 30 mm", "quantity": 1200}`. The quantity is what every loaded row of that SKU added up to, and the description is the one its last loaded row gave. A SKU no row brought is 404 `{"error": "unknown_sku"}`.
- `GET /imports?key=<key>`: 200 with every import of that key, oldest first, and `[]` if there is none: `[{"key": "deliveries/v1/2027-03-01.csv", "status": "loaded", "rows": 3, "loaded": 3, "rejected": 0}]`. Without `key` it is 400 `{"error": "invalid_request"}`.

On the queue `import-results`, once an upload's import is recorded, one message whose body is the import with its bucket: `{"bucket": "uploads", "key": "deliveries/v1/2027-03-01.csv", "status": "loaded", "rows": 3, "loaded": 3, "rejected": 0}`. The next system in the warehouse waits for it, and so do the cases.

Your app reads its port from `PORT`, listens on all interfaces inside the container (`0.0.0.0`), and answers `GET /health` with 200 once it is ready.

## Project

`cstudy start` copies the service into `projects/csv-upload-ingestion-typescript/`, and `cstudy dev` runs it with Postgres and the emulator. Node runs the files by stripping their types, so write no `enum`, no `namespace` and no constructor parameter properties, and import your own files with their `.ts` extension.

- `src/server.ts`: the routes, and where the app starts its consumer. It answers `GET /products/{sku}` already, and 501 to `GET /imports`.
- `src/consumer.ts`: the loop that receives events from `upload-events`, one at a time. It logs each event and leaves it on the queue.
- `src/aws.ts`: the S3 and SQS clients of the AWS SDK for JavaScript, set up for the emulator, and every bucket and queue the problem names.
- `src/db.ts`: the connection pool, from `DATABASE_URL`.
- `migrations/`: the schema, as plain SQL files that node-pg-migrate applies in name order. `0001_products.sql` creates `products`; add yours after it, `0002_...sql` and on, each starting with `-- Up Migration`.
- `scripts/setup.ts`: run before your app starts. It makes the buckets `uploads` and `upload-reports`, the queues `upload-events`, with a visibility timeout of 3 seconds, and `import-results`, and applies the migrations.
- `tests/`: your tests, run by `cstudy test`.
- `.env`: what your app reads, written by `cstudy start` from the problem's settings. Your app's environment already holds it.

`cstudy test` starts a sandbox, runs `scripts/setup.ts`, runs your tests beside the app, and then the visible cases of your open levels. `cstudy submit` grades every case of the open levels, hidden ones included, and opens the next level when they all pass. Each submission grades the earlier levels again, so a later change must keep their answers.

### How the cases drive S3 and SQS

The cases play the suppliers and S3 itself. A case puts a file into `uploads`, then puts S3's event for it on `upload-events`, as S3 would. It waits for your result on `import-results` and then asks your API. It may read your report from `upload-reports`, and look at what is left on `upload-events` and `upload-events-dlq`. Your app deletes an event only once its result is announced, so after a result, a case waits 2 seconds for no other result before it looks at `upload-events`. While it waits for a result, it gives up after 10 seconds, or 40 for the bulk file. Before it waits, it asks your `/health`, so an app that died is reported as exited, with its exit code; 137 means it was killed for using more than its memory.

The emulator checks no signature, so the cases send it plain HTTP with an `Authorization` header that only names the service and the region. Your app signs its requests with the SDK as it would against AWS.

To look around yourself while `cstudy dev` runs, `docker ps` shows the emulator's container, whose name ends in `-aws-1`, and `docker exec -it <that name> python` gives you Python and boto3 beside it, at `http://127.0.0.1:5000`.

### Your app's memory

Your app runs with a memory limit of 128 MiB. Node, with the SDK and `pg` loaded, takes about 45 of them at rest, and an app that streams the bulk file peaks around 80. A file that does not fit has to be read as a stream: a chunk at a time, each one used and let go before the next.

## Level 1: Load an upload

Receive each event from `upload-events`, read the file it names from S3, and load its rows: each row adds its quantity to its SKU's stock, and sets the SKU's description. Record the import, announce it on `import-results`, and only then delete the event from the queue.

An event can arrive before its file is there to read, and reading it then fails with `NoSuchKey`. That upload is not done: leave the event on the queue. Every event your app received and did not delete comes back once the queue's visibility timeout of 3 seconds runs out, and by then the file is there.

At this level every row of every file is good. A file with a header and no rows is loaded, with 0 rows.

### Example 1

<!-- case: v1 -->

Three rows load. The case keeps the result it received and reads it back, to check its fields.

### Example 2

<!-- case: v2 -->

Two lines of one product add up, and the second line's description is the product's.

## Level 2: Bad rows and big files

Now rows can be bad. A row is checked against these rules, in this order, and is reported for the first one it breaks:

| Rule | Error |
|------|-------|
| It has exactly 3 fields | `wrong_column_count` |
| `sku` is 1 to 32 characters, of `A` to `Z`, `0` to `9` and `-`, and does not start with `-` | `invalid_sku` |
| `description` is 1 to 300 characters | `invalid_description` |
| `quantity` is a whole number from 1 to 100000, written with digits alone and no leading zero | `invalid_quantity` |

A bad row loads nothing. The import counts its `rows`, every line after the header, an empty one included; how many of them `loaded`; and how many were `rejected`.

If more than half of a file's rows are bad, the file is mostly bad, and none of it loads: its status is `rejected`, with `loaded` 0. Exactly half is not more than half.

If the first line is not exactly `sku,description,quantity`, the file is rejected without reading further, with `rows`, `loaded` and `rejected` all 0. An empty file has no header. A byte order mark at the very start, as spreadsheet programs write, is not part of the header.

Whenever a file has a bad row or a bad header, write a report to the bucket `upload-reports`, under the same key as the file: a CSV with the header `line,error` and one line per bad row, giving its line number in the file, where the header is line 1, and its error. A bad header gives the one line `1,invalid_header`. A file with nothing bad gets no report.

A rejected file is still an import: record it, announce it, and delete its event, since reading it again would reject it again.

A hidden case loads a delivery file of 160 MB with 550000 rows, more than your app's memory. Read it as a stream, and write its rows in batches: a round trip to Postgres for each row is too slow for it.

### Example 1

<!-- case: v3 -->

Two of five rows are bad: line 3 has no description, and line 4's SKU is in lower case.

### Example 2

<!-- case: v4 -->

Three of four rows are bad, so the good one does not load either.

## Level 3: Twice, never, and halfway

SQS delivers every message at least once, which means sometimes twice. Three things now go wrong on purpose:

- **The same event twice.** An upload loads once, is recorded once and is announced once, however many times its event arrives, at once or later. A new upload of the same key has a new sequencer, and is a new import that adds again.
- **An event that fails forever.** An event whose file never arrives, or a message that is not an S3 event at all, fails every time. After its third receive, it must be in the dead-letter queue `upload-events-dlq`, and not on `upload-events`. Make that queue in `scripts/setup.ts`, and give `upload-events` a redrive policy that moves a message there after 3 receives, `maxReceiveCount` 3; then your app need do nothing but leave a failing event alone. The dead-letter queue's URL is in `DEAD_LETTER_QUEUE_URL`.
- **A crash halfway.** One case uploads the bulk file a second time, and the next restarts your app while it loads, keeping your data as the crash left it. The event comes back, and the second upload loads once, whole: the stock holds the bulk file exactly twice, once for each upload, with nothing left over from the load the crash cut short.

A failed event must come back by itself: do not make it visible again early, or it spends its 3 receives in a moment and lands in the dead-letter queue before its file arrives.

### Example 1

<!-- case: v5 -->

The event arrives twice. One import, one result, and the drill bits counted once.

### Example 2

<!-- case: v6 -->

The file never arrives. The case waits for the event in the dead-letter queue, then checks that `upload-events` holds nothing, visible or in flight.

## Level 4: Only finished uploads

The bucket sends events that are not a finished upload, and loading them is a mistake. Each of these is nothing to load: delete it, record nothing and announce nothing.

| Event | Why there is nothing to load |
|-------|------------------------------|
| A message whose body has `"Event": "s3:TestEvent"` and no `Records` | S3 sends one when a bucket's notifications are set up |
| An `eventName` that does not start with `ObjectCreated:`, such as `ObjectRemoved:Delete` | A file was deleted; what it loaded stays loaded |
| A key that ends in `.part` | An upload tool writes `name.part` while it uploads, then copies it to `name` and deletes `name.part` |

Every `ObjectCreated:` event is a finished upload, the `ObjectCreated:Copy` of a renamed file and the `ObjectCreated:CompleteMultipartUpload` of a large one included.

S3 writes the key in an event URL-encoded, as in a query string: a space as `+` and a `+` as `%2B`. Decode it before you read the file, and record the import under the decoded key.

### Example 1

<!-- case: v7 -->

A test event, then an upload. The test event is gone from the queue, and the upload loads.

### Example 2

<!-- case: v8 -->

The upload tool writes `.part`, copies it to its name and deletes the `.part`. Only the finished file loads.

## Constraints

- Node 24 with 128 MiB of memory; Postgres 17 through `DATABASE_URL`, with node-pg-migrate's plain SQL migrations; S3 and SQS through the AWS SDK for JavaScript v3, at `AWS_ENDPOINT_URL`.
- The bulk file: 160 MB, 550000 rows, loaded within 40 seconds.
- `upload-events` has a visibility timeout of 3 seconds; a case waits at most 10 seconds for a result, or 40 for the bulk file.
- Every case runs on the same database, one after the other. A case's SKUs start with its own id, so cases do not share products; the bulk file's SKUs start with `BULK-`, and only the bulk cases use them.

## Follow-ups

- Your app may die after committing an import and before announcing it. The event comes back, finds the import done, and announces nothing. How would you make the announcement as certain as the commit?
- Ten copies of your service now read the same queue. What in your design already holds, and what would you change so that two of them never load one file at once?
- A file of 50 GB takes an hour to load, in one transaction. What does that transaction cost Postgres while it runs, and how would you load it in parts and still never count a row twice?
- The report of a mostly bad bulk file would hold half a million lines. Where would you keep it while the file loads?
- A supplier uploads the corrected file under the same key a minute after the broken one. Both events arrive, in either order. Which should win, and how does the sequencer help?
- What would you alert on, so that someone hears about the dead-letter queue before a supplier calls?

## Hints

### Hint 1

`GetObject` answers with `Body`, a Node stream. `for await (const chunk of body)` gives it to you a chunk at a time, and asks for the next chunk only when your loop does. Collecting every chunk first, or calling `transformToString()`, holds the whole file.

### Hint 2

Split chunks into lines yourself, keeping the part after the last `\n` for the next chunk. A `TextDecoder` with `{stream: true}` keeps a character whose bytes two chunks split, and drops a byte order mark for you.

### Hint 3

One transaction per file makes a crash harmless: whatever the file loaded before the crash is rolled back, and the event, never deleted, brings the whole file back. Delete the event only after the commit.

### Hint 4

A table of imports with a unique key on bucket, key and sequencer, inserted at the start of the file's transaction, is the rule "once per upload". A second delivery of the same event waits on that key while the first loads, then finds it taken.

### Hint 5

`INSERT ... SELECT * FROM unnest($1::text[], $2::text[], $3::bigint[])` writes a whole batch in one statement. With `ON CONFLICT (sku) DO UPDATE`, a statement may change a row only once, so sum each SKU's quantities within the batch first.

### Hint 6

A `SAVEPOINT` before the rows lets you take them back with `ROLLBACK TO SAVEPOINT` once you find the file mostly bad, and still record its import in the same transaction.
