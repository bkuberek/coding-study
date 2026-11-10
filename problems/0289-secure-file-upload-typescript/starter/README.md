# Secure File Upload

Users upload attachments and avatars, and this service stores them and serves them back. This is its start: it stores and serves, and trusts everything an upload says.

`cstudy` runs this service in a Docker sandbox: your app sees this folder and nothing above it, and has no network beyond its stack.

## Running it

| Command | What it does |
|---------|--------------|
| `cstudy dev` | Runs your app with its mock server, in the foreground, and prints its URL. Ctrl-C stops it |
| `cstudy dev --scenario scanner=outage` | The same, with the scanner misbehaving, by a name from its `API.md` |
| `cstudy test` | Runs your tests beside the app, then the visible cases of your open levels |
| `cstudy submit` | Grades every case of your open levels, and opens the next level when they pass |

Your app reads `PORT` and listens on all interfaces inside the container (`0.0.0.0`). `/health` answers 200 once it is ready.

| Variable | What it is |
|----------|------------|
| `CSTUDY_DATA_DIR` | The folder your app keeps files in. It survives restarts in `cstudy dev`, and each test or graded run starts with an empty one |
| `MAX_BODY_BYTES` | The most an upload's request body may hold |
| `QUOTA_BYTES` | The most each user may keep |
| `SCANNER_URL`, `SCANNER_API_KEY` | The malware scanner, from level 3 |
| `LINK_SIGNING_KEY` | The key that signs shared links, from level 4 |

## Layout

| Path | Holds |
|------|-------|
| `src/server.ts` | The routes, and where the server starts |
| `tests/` | Your tests, with `tests/mockControl.ts` to set the scanner's visible scenario and read what it received |
| `vendors/scanner/API.md` | What the scanner does, for reading |
| `.env` | What your app reads, written by `cstudy start`. Its environment already holds it |

The lock file is what the install uses, exactly. Add a dependency from a shell of your own and keep the lock with it.
