# Members in Python

`cstudy` runs this service in a Docker sandbox, beside a Postgres database at `db` and a Redis cache at `cache`: your app sees this folder and nothing above it, and has no network beyond its stack.

- Run it and its tests: `cstudy test`
- It reads `PORT`, `DATABASE_URL` and `REDIS_URL`, and listens on all interfaces inside the container (`0.0.0.0`). `/health` answers 2xx once it is ready.
- `scripts/migrate.py` runs first and applies each new file in `migrations/`, in name order. Add a migration as a new file; never edit one that has run.
- `.env` lists the variables it reads.
