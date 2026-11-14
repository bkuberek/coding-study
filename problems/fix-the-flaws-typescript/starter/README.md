# Fix the Flaws

A small notes service for a team: people sign up, keep private notes, search them, and download the team's shared files. It works. A security review found problems in it, and the statement lists them, level by level.

`cstudy` runs this service in a Docker sandbox: your app sees this folder and nothing above it, and has no network beyond its stack.

## Running it

| Command | What it does |
|---------|--------------|
| `cstudy dev` | Runs your app in the foreground and prints its URL. Ctrl-C stops it |
| `cstudy test` | Runs your tests beside the app, then the visible cases of your open levels |
| `cstudy submit` | Grades every case of your open levels, and opens the next level when they pass |

Your app reads `PORT` and listens on all interfaces inside the container (`0.0.0.0`). `/health` answers 200 once it is ready. Its output, standard output and error together, is the service's log.

| Variable | What it is |
|----------|------------|
| `CSTUDY_DATA_DIR` | The folder that holds the database, `notes.db`. It survives restarts in `cstudy dev`, and each test or graded run starts with an empty one |
| `ADMIN_PASSWORD` | The password of `admin`, the one administrator, created on the first start |

## Layout

| Path | Holds |
|------|-------|
| `src/server.ts` | The routes, the session check, the request log and error answers |
| `src/users.ts` | Signing up, signing in, the caller's profile and the administrator's list of users |
| `src/notes.ts` | Writing, reading, deleting and searching notes |
| `src/attachments.ts` | Downloads from `attachments/` |
| `src/db.ts` | The SQLite database, through Node's built-in `node:sqlite` |
| `src/http.ts` | The error a handler throws, and the JSON body it reads |
| `attachments/` | The team's shared files |
| `tests/` | Your tests, with `tests/client.ts` to sign users up and write notes |
| `.env` | What your app reads, written by `cstudy start`. Its environment already holds it |

The lock file is what the install uses, exactly. Add a dependency from a shell of your own and keep the lock with it.
