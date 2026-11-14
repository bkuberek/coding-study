# LLM Gateway

Every team in the company calls language models through this one gateway, which holds the keys and talks to the providers. This is its start: it passes a whole answer on from the primary provider, and nothing more.

`cstudy` runs this service in a Docker sandbox: your app sees this folder and nothing above it, and has no network beyond its stack. The providers are mock servers, and the keys in `.env` are fakes that reach no real provider.

## Running it

| Command | What it does |
|---------|--------------|
| `cstudy dev` | Runs your gateway with its providers, in the foreground, and prints its URL. Ctrl-C stops it |
| `cstudy dev --scenario primary=outage` | The same, with a provider misbehaving, by a name from its `API.md` |
| `cstudy test` | Runs your tests beside the app, then the visible cases of your open levels |
| `cstudy submit` | Grades every case of your open levels, and opens the next level when they pass |

Your app reads `PORT` and listens on all interfaces inside the container (`0.0.0.0`). `/health` answers 200 once it is ready. `curl -N` prints a stream as it arrives.

| Variable | Holds |
|----------|-------|
| `PRIMARY_LLM_URL`, `PRIMARY_LLM_KEY` | Where the primary provider is, and its fake key |
| `SECONDARY_LLM_URL`, `SECONDARY_LLM_KEY` | Where the secondary provider is, and its fake key |

## Layout

| Path | Holds |
|------|-------|
| `src/server.ts` | The routes, and where the server starts |
| `src/primary.ts` | The primary provider's client, for whole answers |
| `tests/` | Your tests, with `tests/providerScenario.ts` to set a provider's visible scenario from one |
| `vendors/<name>/API.md` | Each provider's contract, for reading |
| `.env` | What your app reads, written by `cstudy start`. Its environment already holds it |

The lock file is what the install uses, exactly. Add a dependency from a shell of your own and keep the lock with it.
