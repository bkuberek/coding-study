# CSV Upload Ingestion

Suppliers upload delivery files to an S3 bucket, and S3 puts an event for each upload on an SQS queue. This is the start of the service that consumes those events, loads each file into Postgres, and reports the rows it cannot load.

`cstudy` runs this service with Postgres and with S3 and SQS emulated locally, in a Docker sandbox: your app sees this folder and nothing above it, and has no network beyond its stack.

## Running it

| Command | What it does |
|---------|--------------|
| `cstudy dev` | Makes the buckets and queues, applies the migrations and runs your app, in the foreground, and prints its URL. Ctrl-C stops it |
| `cstudy test` | Runs your tests beside the app, then the visible cases of your open levels |
| `cstudy submit` | Grades every case of your open levels, and opens the next level when they pass |

Your app reads `PORT` and listens on all interfaces inside the container (`0.0.0.0`). `/health` answers 200 once it is ready. It runs with a memory limit of 128 MiB.

| Variable | What it names |
|----------|---------------|
| `DATABASE_URL` | Postgres |
| `AWS_ENDPOINT_URL`, `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | The emulator, which accepts any keys |
| `UPLOAD_BUCKET`, `REPORT_BUCKET` | `uploads`, where files arrive, and `upload-reports`, where reports go |
| `UPLOAD_QUEUE_URL`, `RESULT_QUEUE_URL`, `DEAD_LETTER_QUEUE_URL` | `upload-events`, `import-results` and `upload-events-dlq` |

## Layout

| Path | Holds |
|------|-------|
| `src/server.ts` | The routes, and where the app starts its consumer |
| `src/consumer.ts` | The loop that receives upload events |
| `src/aws.ts` | The S3 and SQS clients, and the buckets and queues |
| `src/db.ts` | The connection pool |
| `migrations/` | Plain SQL migrations, applied in name order by node-pg-migrate |
| `scripts/setup.ts` | Makes the buckets and queues, then applies the migrations, before your app starts |
| `tests/` | Your tests |
| `.env` | What your app reads, written by `cstudy start`. Its environment already holds it |

The lock file is what the install uses, exactly. Add a dependency from a shell of your own and keep the lock with it.
