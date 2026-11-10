# Price Cache and Rate Limits

A shop's public price API sits in front of a slow pricing engine. This is the start of it: for now every request asks the engine, and nothing stops a client from asking as often as it likes.

`cstudy` runs this service, its store and the engine in a Docker sandbox: your app sees this folder and nothing above it, and has no network beyond its stack.

## Running it

| Command | What it does |
|---------|--------------|
| `cstudy dev` | Runs your app with its store and the engine, in the foreground, and prints its URL. Ctrl-C stops it |
| `cstudy dev --scenario pricing=outage` | The same, with the engine misbehaving, by a name from its `API.md` |
| `cstudy test` | Runs your tests beside the app, then the visible cases of your open levels |
| `cstudy submit` | Grades every case of your open levels, and opens the next level when they pass |

Your app reads `PORT` and listens on all interfaces inside the container (`0.0.0.0`). `/health` answers 200 once it is ready. `REDIS_URL` is where the store answers: Valkey, which speaks Redis's protocol. `PRICING_URL` is where the engine answers.

## Layout

| Path | Holds |
|------|-------|
| `src/server.ts` | The routes, and where the server starts |
| `src/pricing.ts` | The engine's client |
| `src/store.ts` | The store's client, which every route shares |
| `scripts/bootstrap.ts` | Checks that the store answers, before your app starts |
| `scripts/reset.ts` | Empties the store before a case that starts fresh |
| `tests/` | Your tests, with `tests/pricingScenario.ts` to set the engine's visible scenario and count its calls |
| `vendors/pricing/API.md` | The engine's contract, for reading |
| `.env` | What your app reads, written by `cstudy start`. Its environment already holds it |

The lock file is what the install uses, exactly. Add a dependency from a shell of your own and keep the lock with it.
