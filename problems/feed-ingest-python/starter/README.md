# Feed Ingest

A loyalty program gets a file of purchases from its shops. This is the start of the service that turns those files into clean rows in Postgres and works out what each member earned.

`cstudy` runs this service in a Docker sandbox, beside a Postgres database at `db` and a partner's API at `bonus-partner`: your app sees this folder and nothing above it, and has no network beyond its stack.

## Running it

| Command | What it does |
|---------|--------------|
| `cstudy dev` | Runs your app with Postgres and the partner, in the foreground, and prints its URL. Ctrl-C stops it |
| `cstudy dev --scenario bonus-partner=outage` | The same, with the partner misbehaving, by a name from its `API.md` |
| `cstudy test` | Runs your tests beside the app with pytest, then the visible cases of your open levels |
| `cstudy submit` | Grades every case of your open levels, and opens the next level when they pass |

Your app reads `PORT`, `DATABASE_URL` and `BONUS_URL`, and listens on all interfaces inside the container (`0.0.0.0`). `/health` answers 200 once it is ready.

## Layout

| Path | Holds |
|------|-------|
| `src/server.py` | The routes, and where the server starts. `GET /purchases` works already, and `PUT /feeds/{name}` answers 501 |
| `src/db.py` | `connect()` and `query()`, for Postgres through `pg8000` |
| `migrations/` | The schema, as plain SQL. `scripts/migrate.py` applies each new file in name order before your app starts. Add yours as `0002_...sql` and on, and never edit one that has run |
| `scripts/reset.py` | Puts the database back between cases. It works for any tables you add, so leave it as it is |
| `tests/` | Your tests, with two fixtures in `tests/conftest.py`: `app` asks your app, and `partner.set_scenario` sets the partner's visible scenario |
| `vendors/bonus-partner/API.md` | The partner's contract, for reading |
| `.env` | What your app reads, written by `cstudy start`. Its environment already holds it |

It runs on Python 3.13 and its standard library, with `pg8000` to talk to Postgres and pytest for the tests. `uv.lock` is what the install uses, exactly. Add a dependency from a shell of your own and keep the lock with it.
