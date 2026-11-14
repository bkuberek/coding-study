# RAG Service with Citations

A team's help assistant answers questions from its internal documents and says where each answer came from. This is the start of it: the routes are there, and every one of them answers 501.

`cstudy` runs this service, its database and the two model services in a Docker sandbox: your app sees this folder and nothing above it, and has no network beyond its stack.

## Running it

| Command | What it does |
|---------|--------------|
| `cstudy dev` | Applies the migrations and runs your app with its database and the model services, in the foreground, and prints its URL. Ctrl-C stops it |
| `cstudy dev --scenario chat=rate_limited_then_ok` | The same, with a service misbehaving, by a name from its `API.md` |
| `cstudy test` | Runs your tests beside the app, then the visible cases of your open levels |
| `cstudy submit` | Grades every case of your open levels, and opens the next level when they pass |

Your app reads `PORT` and listens on all interfaces inside the container (`0.0.0.0`). `/health` answers 200 once it is ready. `DATABASE_URL` is where Postgres answers, with pgvector installed. `EMBEDDINGS_URL` and `CHAT_URL` are where the model services answer, and `LLM_API_KEY` is the key they expect.

## Layout

| Path | Holds |
|------|-------|
| `src/server.ts` | The routes, and where the server starts |
| `src/providers.ts` | The model services' clients, the model names and the system prompt |
| `src/db.ts` | The connection pool |
| `migrations/` | Plain SQL migrations, applied in name order by node-pg-migrate. `0001_vector.sql` turns pgvector on; add yours after it |
| `scripts/reset.ts` | Puts the database back as your migrations left it, before a case that starts fresh |
| `tests/` | Your tests, with `tests/corpus.ts`, the documents the visible cases put, and `tests/providerScenario.ts`, to set a service's scenario and read what it was sent |
| `vendors/embeddings/API.md`, `vendors/chat/API.md` | The model services' contracts, for reading |
| `.env` | What your app reads, written by `cstudy start`. Its environment already holds it |

The lock file is what the install uses, exactly. Add a dependency from a shell of your own and keep the lock with it.
