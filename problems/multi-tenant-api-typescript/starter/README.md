# Multi-Tenant API

Many organizations share one project tracker and one Postgres database. This is the start of its API, which must never let one organization see, change or learn of another's rows.

`cstudy` runs this service and its database in a Docker sandbox: your app sees this folder and nothing above it, and has no network beyond its stack.

## Running it

| Command | What it does |
|---------|--------------|
| `cstudy dev` | Applies the migrations and runs your app with its database, in the foreground, and prints its URL. Ctrl-C stops it |
| `cstudy test` | Runs your tests beside the app, then the visible cases of your open levels |
| `cstudy submit` | Grades every case of your open levels, and opens the next level when they pass |

Your app reads `PORT` and listens on all interfaces inside the container (`0.0.0.0`). `/health` answers 200 once it is ready. `DATABASE_URL` connects as `tracker_app`, the role your app uses; `OWNER_DATABASE_URL` connects as `tracker_owner`, which migrations and `scripts/reset.ts` use, and which your app must not.

## Layout

| Path | Holds |
|------|-------|
| `src/server.ts` | The routes, and where the server starts |
| `src/auth.ts` | Who is calling, from the API key |
| `src/search.ts` | `GET /search/tasks`, whose query names no organization and must keep it that way |
| `src/answers.ts` | What a route answers |
| `src/db.ts` | The connection pool |
| `migrations/` | Plain SQL migrations, applied in name order by node-pg-migrate. `0001_baseline.sql` is the problem's; add yours after it |
| `scripts/reset.ts` | Puts the database back as your migrations left it, before a case that starts fresh |
| `tests/` | Your tests |
| `.env` | What your app reads, written by `cstudy start`. Its environment already holds it |

The lock file is what the install uses, exactly. Add a dependency from a shell of your own and keep the lock with it.
