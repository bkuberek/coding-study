# SSRF-Safe Webhook Dispatcher

Customers register webhook URLs and this service sends them events. This is the start of the dispatcher that delivers them, and that must never let a customer's URL point it at your own network.

`cstudy` runs this service in a Docker sandbox: your app sees this folder and nothing above it, and has no network beyond its stack.

## Running it

| Command | What it does |
|---------|--------------|
| `cstudy dev` | Runs your app with its mock servers, in the foreground, and prints its URL. Ctrl-C stops it |
| `cstudy dev --scenario customer-hooks=slow` | The same, with a server misbehaving, by a name from its `API.md` |
| `cstudy test` | Runs your tests beside the app, then the visible cases of your open levels |
| `cstudy submit` | Grades every case of your open levels, and opens the next level when they pass |

Your app reads `PORT` and listens on all interfaces inside the container (`0.0.0.0`). `/health` answers 200 once it is ready. `RESOLVER_URL` is where `src/network.ts` asks for names.

## Layout

| Path | Holds |
|------|-------|
| `src/server.ts` | The routes, and where the server starts |
| `src/network.ts` | The sandbox's internet: `lookup` for a name's addresses, and `originFor` for where a connection to an address goes |
| `tests/` | Your tests, with `tests/mockControl.ts` to set a mock server's visible scenario and read what it received |
| `vendors/<name>/API.md` | What each mock server does, for reading |
| `.env` | What your app reads, written by `cstudy start`. Its environment already holds it |

The lock file is what the install uses, exactly. Add a dependency from a shell of your own and keep the lock with it.
