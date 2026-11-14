# Postgres Job Queue

A service generates reports in the background, through a queue it keeps in Postgres: producers enqueue jobs, and workers claim them, run them, and say how it went. This is the first version, which only takes jobs in. You build the rest of the queue, which must hand each job to one worker however many ask at once.

`cstudy` runs this service and its database in a Docker sandbox: your app sees this folder and nothing above it, and has no network beyond its stack.

## Running it

| Command | What it does |
|---------|--------------|
| `cstudy dev` | Applies the migrations and runs your app with its database, in the foreground, and prints its URL. Ctrl-C stops it |
| `cstudy test` | Runs your tests beside the app, then the visible cases of your open levels |
| `cstudy submit` | Grades every case of your open levels, and opens the next level when they pass |

Your app reads `PORT` and listens on all interfaces inside the container (`0.0.0.0`). `/health` answers 200 once it is ready. `DATABASE_URL` is where Postgres answers, and `CLOCK_NOW` is what time it is: the clock is frozen, so `src/clock.ts` reads it.

## Layout

| Path | Holds |
|------|-------|
| `src/server.ts` | The routes, and where the server starts |
| `src/clock.ts` | `now()`, the frozen clock, and `timestamp()`, which writes a time as the answers do |
| `src/db.ts` | The connection pool |
| `migrations/` | Plain SQL migrations, applied in name order by node-pg-migrate. `0001_baseline.sql` is the problem's; add yours after it |
| `scripts/reset.ts` | Puts the database back as your migrations left it, before a case that starts fresh |
| `tests/` | Your tests |
| `.env` | What your app reads, written by `cstudy start`. Its environment already holds it |

The lock file is what the install uses, exactly. Add a dependency from a shell of your own and keep the lock with it.
