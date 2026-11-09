# Coworking Availability

A coworking space sells hot desks it counts itself and meeting rooms from outside vendors. This is the start of the one API that says what can be booked on a day.

`cstudy` runs this service in a Docker sandbox: your app sees this folder and nothing above it, and has no network beyond its stack.

## Running it

| Command | What it does |
|---------|--------------|
| `cstudy dev` | Runs your app with its vendors, in the foreground, and prints its URL. Ctrl-C stops it |
| `cstudy dev --scenario room-vendor=outage` | The same, with a vendor misbehaving, by a name from its `API.md` |
| `cstudy test` | Runs your tests beside the app with pytest, then the visible cases of your open levels |
| `cstudy submit` | Grades every case of your open levels, and opens the next level when they pass |

Your app reads `PORT` and listens on all interfaces inside the container (`0.0.0.0`). `/health` answers 200 once it is ready.

## Layout

| Path | Holds |
|------|-------|
| `src/server.py` | The routes, and where the server starts |
| `src/desks.py` | `DeskInventory`: the daily counts |
| `data/desks.json` | The seeded counts, per day |
| `tests/` | Your tests, with two fixtures in `tests/conftest.py`: `app` asks your app, and `vendors.set_scenario` sets a vendor's visible scenario |
| `vendors/<name>/API.md` | Each vendor's contract, for reading |
| `.env` | What your app reads, written by `cstudy start`. Its environment already holds it |

It runs on Python 3.13 and its standard library, with pytest for the tests. `uv.lock` is what the install uses, exactly. Add a dependency from a shell of your own and keep the lock with it.
