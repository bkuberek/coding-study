# Fix the Flaws (TypeScript)

## Statement

You join a team that runs a small notes service. People sign up, keep private notes, search them, and download the team's shared files. It works, and people rely on it. A security review has just come back, and its findings read like tickets: what is wrong and what it lets someone do, never how to fix it. Your job is to close each finding without breaking anything the service already does.

This is practice for a code-review or security-fix round, where you get working code that someone else wrote, find its holes and close them while it keeps working. Each level is one part of the review. `cstudy` runs the service in a Docker sandbox and grades it over HTTP with two kinds of cases. The request a finding describes must now be refused, or do no harm. Normal use must keep working, so a fix that switches a feature off fails. The service, its users and its review are invented.

## Input

HTTP requests, listed under [The service](#the-service). Every request except `GET /health`, `POST /users` and `POST /login` carries `Authorization: Bearer <token>`, with a token that `POST /login` gave.

## Output

JSON with `Content-Type: application/json`, except a shared file's bytes. An error is `{"error": "<code>"}`, with the status and code the tables below name. Your app reads its port from `PORT`, listens on all interfaces inside the container (`0.0.0.0`), and `GET /health` answers 200 once it is ready. What it prints, standard output and error together, is the service's log.

## Project

`cstudy start` copies the service into `projects/fix-the-flaws-typescript/`, and `cstudy dev` runs it. Node runs the files by stripping their types, so write no `enum`, no `namespace` and no constructor parameter properties, and import your own files with their `.ts` extension.

- `src/server.ts`: the routes, the session check, the request log and error answers.
- `src/users.ts`: signing up, signing in, the caller's profile and the administrator's list of users.
- `src/notes.ts`: writing, reading, deleting and searching notes.
- `src/attachments.ts`: downloads from `attachments/`.
- `src/db.ts`: the SQLite database, `notes.db` in `CSTUDY_DATA_DIR`, through Node's built-in `node:sqlite`.
- `src/http.ts`: the error a handler throws, and the JSON body it reads.
- `attachments/`: the team's shared files.
- `tests/`: your tests, run by `cstudy test`, with `tests/client.ts` to sign users up and write notes.
- `.env`: what your app reads, written by `cstudy start`. Your app's environment already holds it.

`ADMIN_PASSWORD` is the password of `admin`, the one administrator, whom the service creates on its first start. The database survives restarts in `cstudy dev`, and each test or graded run starts with an empty one.

`cstudy test` starts a sandbox, runs your tests beside the app, and then the visible cases of your open levels. `cstudy submit` grades every case of the open levels, hidden ones included, and opens the next level when they all pass. Each submission grades the earlier levels again, so a later fix must keep their answers.

### The service

| Request | Answer |
|---------|--------|
| `GET /health` | 200 with `{"status": "ok"}` |
| `POST /users` with `{"username": "ana", "password": "notes-pass-1234"}` | 201 with the new account: `{"id": "2", "username": "ana", "display_name": "ana", "role": "member"}`. A username is 1 to 32 of `a` to `z`, `0` to `9`, `-` and `_`, and a password at least 8 characters. The display name starts as the username |
| `POST /login` with `{"username": "ana", "password": "notes-pass-1234"}` | 200 with `{"token": "<48 hex digits>"}`, a new session |
| `GET /me` | 200 with the caller's account, as `POST /users` shows it |
| `PATCH /me` with `{"display_name": "Ana Lima"}` | 200 with the caller's account, its display name changed: 1 to 64 characters |
| `GET /admin/users` | For an administrator, 200 with every account, in the order they were made |
| `POST /notes` with `{"title": "Groceries", "body": "Milk, eggs"}` | 201 with the note: `{"id": "7", "title": "Groceries", "body": "Milk, eggs"}`. A title is 1 to 200 characters, and a body any string |
| `GET /notes/{id}` | 200 with the note |
| `DELETE /notes/{id}` | 204, with no body |
| `GET /notes?q=<text>` | 200 with the caller's notes whose title holds the text, in any case of ASCII letters, oldest first: `[{"id": "7", "title": "Groceries"}]`. Without `q`, all of the caller's notes |
| `GET /attachments/{name}` | 200 with the bytes of the shared file of that name in `attachments/`, as `application/octet-stream`. A name with a space or another character a URL cannot hold arrives percent-encoded, as in `onboarding%20checklist.txt` |

Ids are strings of digits. Accounts are counted up from 1, and so are notes, across every user.

| Status | Body | When |
|--------|------|------|
| 400 | `{"error": "invalid_request"}` | A body that is not a JSON object, or a field that breaks its rule |
| 401 | `{"error": "invalid_credentials"}` | `POST /login` with a wrong username or password |
| 401 | `{"error": "unauthenticated"}` | A request that needs a session, without `Authorization: Bearer <token>` or with a token that is no session |
| 403 | `{"error": "forbidden"}` | `GET /admin/users` from a member |
| 404 | `{"error": "not_found"}` | A note or a shared file that does not exist, or a route the service does not have |
| 409 | `{"error": "username_taken"}` | `POST /users` with a username already taken |
| 500 | `{"error": "internal_error"}` | Anything the service did not expect |

## Level 1: Notes that are not yours

**Finding.** Any signed-in user can read any note. Ben asks for `GET /notes/7`, and the service answers with Ana's note. `DELETE /notes/7` from Ben deletes it the same way.

**Impact.** Notes are private, and they are not. Ids are counted up from 1, so one user can walk every id and read, or delete, every note in the service.

**Expected.** A note belongs to the user who wrote it. To anyone else it answers exactly as a note that does not exist: 404, so nobody learns which ids are taken. Its owner still reads and deletes it as before.

### Example 1

<!-- case: v1 -->

The owner reads back the note they wrote.

### Example 2

<!-- case: v2 -->

`v2-ben` asks for `v2-ana`'s note by its id, and gets the answer a missing note gets.

## Level 2: Names and fields from the request

**Finding 1.** `GET /attachments/{name}` downloads files from outside `attachments/`. `GET /attachments/../package.json` answers the service's own `package.json`.

**Impact.** Any signed-in user can download any file the service can read, its source and settings included.

**Expected.** Only a file directly inside `attachments/` can be downloaded, however its name is written. Any other name answers 404. Every file in `attachments/` still downloads, a name with a space included.

**Finding 2.** The account endpoints copy what a request's body holds into the account. A member who sends `PATCH /me` with `{"display_name": "Eve", "role": "admin"}` becomes an administrator, and `GET /admin/users` then lists every account to them.

**Impact.** Any user can give themselves an administrator's rights.

**Expected.** A user sets their username and password when they sign up, and their display name after that, and nothing else. A new account is always a member, and every other field of a body is ignored wherever an account is written. The administrator still lists every account.

### Example 1

<!-- case: v3 -->

A shared file, by its name.

### Example 2

<!-- case: v4 -->

`../package.json` climbs out of `attachments/`, so it is not a shared file.

### Example 3

<!-- case: v5 -->

A user changes their display name, and their account shows it.

### Example 4

<!-- case: v6 -->

The name changes, and the role in the same body changes nothing.

## Level 3: Text that becomes a query

**Finding.** The search builds its SQL from the text it is given. A search for `' OR '1'='1` answers every note in the service, everyone's. A search for a name such as `O'Brien` answers 500.

**Impact.** Any signed-in user can read every note through the search, and with a little more of the same, change what any query does.

**Expected.** A search finds the caller's notes whose title holds the text, whatever characters the text holds, quotes included, and nothing else.

### Example 1

<!-- case: v7 -->

`grocer` is found in two titles, in either case.

### Example 2

<!-- case: v8 -->

No title of `v8-ana`'s holds `' OR '1'='1`, so the answer is empty. `v8-ben`'s note is not in it.

## Level 4: Logs and errors

**Finding 1.** The service's log holds session tokens.

**Impact.** A token is as good as a password until it is gone, and sessions here never end. Whoever can read the log, now or from any copy of it, can act as any user who signed in.

**Expected.** No session token ever appears in what the service prints.

**Finding 2.** Error answers carry the exception's message and its stack trace: file paths, line numbers and what the code was doing.

**Impact.** Every error tells a stranger how the service is built and where to push next.

**Expected.** An error's body is exactly `{"error": "<code>"}`, with the status and code from [The service](#the-service). What went wrong inside may go to the log, which only the team reads.

### Example 1

<!-- case: v9 -->

`v9-ana` signs up and signs in. Nothing the service prints may hold the token it answered.

### Example 2

<!-- case: v10 -->

The body stops halfway, so it is not JSON. The answer names the code, and nothing else.

## Constraints

- Everything listed under [The service](#the-service) keeps working as it is described, for every user.
- Keep the service's routes, its database and its answers' shapes. The fixes belong in the code that handles a request.
- A refusal answers like a resource that does not exist wherever the finding asks for 404, so no answer tells which ids or files exist.

## Follow-ups

- A session never ends here. How would you expire one, and let a user end all of theirs, and what would the database keep for it?
- The database keeps each token as it is. If someone copied `notes.db`, what could they do with it, and what would you keep instead?
- Nothing slows down guessing a password at `POST /login`. What would you count, per what, and what would you answer?
- The service has a dozen routes. In one with two hundred, how would you make sure that no route forgets to check who owns what it touches?
- In a search, `%` and `_` still match any text and any character. When does that matter, and how would you search for them as they are written?
- How would you show a reviewer that each fix is complete, rather than that one request now fails?

## Hints

### Hint 1

Read the code that handles each request in a finding, and ask the same question every time: where does a value from the request reach something that matters, and what checks it on the way?

### Hint 2

A note is the caller's when its `owner_id` is the caller's id. A query can ask for both at once, so that another user's note is simply not found, by every query that takes a note's id.

### Hint 3

A check on a name only means something on the name that is used. Decode it first, resolve the path it leads to, and then check that the path is a file directly inside the folder. `resolve` and `dirname` from `node:path` do the work.

### Hint 4

Copy the fields a user may set out of the body one by one, rather than the body into the account. Look for every place that writes an account.

### Hint 5

`db.prepare(sql).all(...values)` binds each `?` of the SQL to a value. Text bound that way is only ever a value: no character in it can change what the query means.

### Hint 6

Look for every line that prints, and ask what it prints. A request's headers hold the token too, and an error's message and stack belong in the log, not in the answer.
