# Tool-Calling Agent Loop

An online shop's support staff ask a help desk assistant questions, and a chat model answers them by calling the shop's tools: search the help center, look up an order, open a ticket, issue a refund. This is the start of the service around the model. For now it asks the model once and returns what it says.

`cstudy` runs this service in a Docker sandbox: your app sees this folder and nothing above it, and has no network beyond its stack. The model is a scripted stand-in, so nothing here reaches a real one.

## Running it

| Command | What it does |
|---------|--------------|
| `cstudy dev` | Runs your app with the model and the shop's systems, in the foreground, and prints its URL. Ctrl-C stops it |
| `cstudy dev --scenario kb=outage` | The same, with the help center misbehaving, by a name from its `API.md` |
| `cstudy test` | Runs your tests beside the app, then the visible cases of your open levels |
| `cstudy submit` | Grades every case of your open levels, and opens the next level when they pass |

Your app reads `PORT` and listens on all interfaces inside the container (`0.0.0.0`). `/health` answers 200 once it is ready.

## What it reads

| Variable | Holds |
|----------|-------|
| `PORT` | The port to listen on |
| `MODEL_URL`, `MODEL_API_KEY`, `MODEL_NAME` | Where the model answers, the key it takes and the model to ask. The key is a fake |
| `KB_URL`, `ORDERS_URL`, `HELPDESK_URL` | Where the help center, the order system and the helpdesk answer |
| `MAX_STEPS`, `TOKEN_BUDGET`, `TOOL_TIMEOUT_MS` | What one question may spend, and how long a tool may take |

## Layout

| Path | Holds |
|------|-------|
| `src/server.ts` | The routes, and where the server starts |
| `src/agent.ts` | `runAgent`: answers one question with the model and the tools |
| `src/model.ts` | `chat`: one request to the model, and the shapes of its messages |
| `src/tools.ts` | `TOOLS`: every tool, with its parameters' JSON Schema and what it calls |
| `src/prompt.ts` | `SYSTEM_PROMPT` and its canary. The model is scripted against them, so keep both |
| `src/roles.ts` | The staff roles a request can carry |
| `tests/` | Your tests, with `tests/mockControl.ts` to set a scenario and read what a system received |
| `vendors/*/API.md` | The model's and each system's contract, for reading |
| `.env` | What your app reads, written by `cstudy start`. Its environment already holds it |

The lock file is what the install uses, exactly. Add a dependency from a shell of your own and keep the lock with it.
