# Multi-Tenant API (TypeScript)

## Statement

A project tracker sells to many organizations and serves all of them from one Postgres database. Every project, task and member row carries the organization it belongs to, its tenant, and each organization must see only its own rows. Not by a 403 that admits the row exists, and not through the one query somebody forgot to filter, a pooled connection that still remembers the previous request, or a body that names a field the client should never set.

Build the tracker's API in levels. It scopes every read and write to the caller's organization, makes Postgres enforce that with row-level security so a query that forgets still cannot leak, refuses the fields and actions a caller has no right to, and adds a table that is closed from the moment it exists. `cstudy` runs your app and its database in a Docker sandbox and judges it by what it answers over HTTP, including requests that name another organization's ids and bursts of requests from several organizations at the same moment. The tracker, its organizations and its people are invented.

## Input

HTTP requests with JSON bodies, each carrying an API key as `Authorization: Bearer <key>`. Level 1 has projects and tasks: `GET` and `POST /projects`, `GET` and `DELETE /projects/{id}`, `GET` and `POST /projects/{id}/tasks`, and `GET`, `PATCH` and `DELETE /tasks/{id}`. Each level says what it adds.

## Output

JSON, always with `Content-Type: application/json`. A refusal is `{"error": "<code>"}`, with the codes each level names. Your app reads its port from `PORT` and listens on all interfaces inside the container (`0.0.0.0`), and `GET /health` answers 200, with no key, once it is ready.

## Project

`cstudy start` copies the service into `projects/multi-tenant-api-typescript/`, and `cstudy dev` runs it with its database. Node runs the files by stripping their types, so write no `enum`, no `namespace` and no constructor parameter properties, and import your own files with their `.ts` extension.

- `src/server.ts`: the routes, and where the server starts. It answers `GET /projects` from the database already, for every organization at once, and 501 to the rest of level 1.
- `src/auth.ts`: `authenticate`, which finds the organization and the user of a key in `api_keys`.
- `src/search.ts`: `GET /search/tasks`, which level 2 is about. Its query names no organization, and must keep it that way.
- `src/answers.ts`: what a route answers, and `src/db.ts`: the connection pool, from `DATABASE_URL`.
- `migrations/`: the schema, as plain SQL files that node-pg-migrate applies in name order. `0001_baseline.sql` is the problem's and stays as it is; add yours after it, `0002_...sql` and on. Each file starts with `-- Up Migration`, and node-pg-migrate runs each in a transaction of its own and records it in `pgmigrations`.
- `scripts/reset.ts`: puts the database back as it was after your migrations, before a case that starts fresh. You should not need to change it.
- `tests/`: your tests, run by `cstudy test`.
- `.env`: what your app reads, written by `cstudy start` from the problem's settings. Your app's environment already holds it.

Two Postgres roles share the database. `tracker_owner` owns every table: migrations, `scripts/reset.ts` and grading connect as it, through `OWNER_DATABASE_URL`. `tracker_app` owns none, cannot bypass row-level security, and is what your app connects as, through `DATABASE_URL`. The baseline creates it and grants it reading and writing on every table, those to come included. An owner skips row-level security, so an app that connects as `tracker_owner` defeats level 2, and its cases say so.

`cstudy test` starts a sandbox, applies the migrations, runs your tests beside the app, and then the visible cases of your open levels. `cstudy submit` grades every case of the open levels, hidden ones included, and opens the next level when they all pass. Each submission grades the earlier levels again, so a later change must keep their answers. To look at the data yourself while `cstudy dev` runs, `docker ps` shows its database container, whose name ends in `-db-1`, and `docker exec -it <that name> psql -U tracker_owner -d tracker` opens a shell on it; `SET ROLE tracker_app;` then shows what your app sees.

### The data you start with and the data you do not see

`0001_baseline.sql` creates `tenants`, `users`, `api_keys`, `projects` and `tasks`. Each row of the last four names its organization in `tenant_id`; `api_keys` is read by the key alone, before the organization is known, so it says whose key it is. Ids are text: the seeded rows use short ones, and a new row gets whatever id the database's default picks. A task's foreign key to its project names both the project and the organization, so a task cannot point at another organization's project.

| Organization | Key | User | Role |
|--------------|-----|------|------|
| `alder`, Alder Studio | `key-ada` | `u-ada`, Ada | admin |
| `alder` | `key-ari` | `u-ari`, Ari | member |
| `birch`, Birch Works | `key-bea` | `u-bea`, Bea | admin |
| `birch` | `key-ben` | `u-ben`, Ben | member |

| Project | Organization | Its tasks |
|---------|--------------|-----------|
| `p-1`, Spring launch | `alder` | `t-1` Write the launch email, `t-2` Book the launch venue (done) |
| `p-2`, Office move | `alder` | `t-3` Order standing desks |
| `p-3`, Spring catalog | `birch` | `t-4` Shoot the launch photos, `t-5` Price the spring range |

When `cstudy submit` grades, it applies the baseline, then adds an organization you never see, with its own keys, members, projects and tasks, and only then applies your migrations. Ids and keys that start with `x-` are reserved for those rows. Your app must find its keys in the database, and your policies must hold for its rows as for the others. Grading also applies your migrations to an empty database, which must work too.

A case that starts fresh gets the database as it was right after your migrations, and your app started again.

## Level 1: Scoped reads and writes

Every request but `/health` carries a key. The key says who calls, and the caller's organization is the only one that exists for that request: a list holds only its rows, and an id of another organization's row is answered exactly as an id nobody has, 404. A 403 there would tell the caller that the row exists, which is already a leak.

| Request | Answer |
|---------|--------|
| `GET /projects` | 200 with the organization's projects, in any order: `[{"id": "p-1", "name": "Spring launch"}, ...]` |
| `POST /projects` with `{"name": "Budget review"}` | 201 with the new project, its id picked by the database |
| `GET /projects/{id}` | 200 with the project |
| `DELETE /projects/{id}` | 200 with the project, which goes with its tasks |
| `GET /projects/{id}/tasks` | 200 with the project's tasks, in any order: `[{"id": "t-1", "project": "p-1", "title": "Write the launch email", "done": false}, ...]` |
| `POST /projects/{id}/tasks` with `{"title": "Send the invites"}` | 201 with the new task, not done |
| `GET /tasks/{id}` | 200 with the task |
| `PATCH /tasks/{id}` with `{"title": "...", "done": true}` | 200 with the task changed. It takes `title`, `done` or both |
| `DELETE /tasks/{id}` | 200 with the task, which is gone |

| Field | Rule |
|-------|------|
| `name` | Text of 1 to 100 characters |
| `title` | Text of 1 to 200 characters |
| `done` | `true` or `false` |

| Request | Status | Body |
|---------|--------|------|
| No `Authorization: Bearer <key>`, or a key nobody holds | 401 | `{"error": "unauthorized"}` |
| An id in the path that the caller's organization does not have, whether another organization has it or nobody does | 404 | `{"error": "not_found"}` |
| A body that is not a JSON object, a field missing or breaking its rule, or a `PATCH` that changes neither field | 400 | `{"error": "invalid_request"}` |

A request is checked in the order of this table, so another organization's id is 404 even with a broken body.

### Example 1

<!-- case: v1 -->

Ada's key is `alder`'s, so `birch`'s project is not there.

### Example 2

<!-- case: v2 -->

`p-3` exists, in `birch`. For `alder` it does not.

### Example 3

<!-- case: v3 -->

A new task in `alder`'s project, read back by the id the first answer gave.

### Example 4

<!-- case: v4 -->

No key, so no organization to answer for.

### Example 5

<!-- case: v5 -->

Bea, of `birch`, tries to close `alder`'s task by its id, and it is unchanged.

## Level 2: Row-level security

Every query of level 1 names the caller's organization. The day one query forgets, it leaks, and nothing in the app notices. Make Postgres refuse it too: enable row-level security on every table that holds an organization's rows, `tenants`, `users`, `projects` and `tasks`, with a policy that lets a transaction see and write only the rows of the organization it serves. The app says which one at the start of each transaction, in a setting of its own:

```sql
SET LOCAL app.tenant_id = 'alder';
-- the same, with a parameter: SELECT set_config('app.tenant_id', $1, true);
```

A policy reads it back with `current_setting('app.tenant_id', true)`, which is NULL or empty where nobody set it, and so matches no row. Policies apply to `tracker_app` because it owns no table and lacks `BYPASSRLS`; they would not apply to `tracker_owner`.

`LOCAL` matters. The pool hands each request whichever connection is free, and a plain `SET` lasts as long as the connection, not the request: the next request on it starts as the previous caller, and a `SET` sent through `pool.query` may land on one connection while the query lands on another. `SET LOCAL` ends with its transaction, so run each request's statements in one transaction, on one connection taken from the pool.

`GET /search/tasks?q=launch` is in the starter, and stays as it is but for what it runs on: its query names no organization, on purpose. It stands for the query somebody forgets to scope, and it must answer only the caller's tasks, those whose title holds `q` whatever its case, in any order, in the shape of a task. `q` is 1 to 100 characters, or the answer is 400 `invalid_request`.

The cases send bursts of up to 32 requests at the same moment, from several organizations, and each answer must be its caller's.

### Example 1

<!-- case: v6 -->

`t-4` holds "launch" too, but it is `birch`'s.

### Example 2

<!-- case: v7 -->

Twenty requests at once, the even ones from Ada for `t-1` and the odd ones from Bea for `t-4`. A request served as the other organization finds nothing, and answers 404.

## Level 3: Mass assignment and roles

Members can be listed, and can rename themselves; only an admin changes a role.

| Request | Answer |
|---------|--------|
| `GET /members` | 200 with the organization's users, in any order: `[{"id": "u-ada", "name": "Ada", "role": "admin"}, ...]` |
| `PATCH /me` with `{"name": "Ari Kim"}` | 200 with the caller, renamed. `name` is required, with the rule of level 1 |
| `PATCH /members/{id}` with `{"role": "admin"}` | 200 with the user, now of that role, `admin` or `member`. Admins only |

`DELETE /projects/{id}` is for admins only too. A member who asks for either is refused, 403 `{"error": "forbidden"}`, but only about an id of their own organization: any other id is 404, as at level 1. A role applies from the next request on.

A body sets only the fields its request takes. Anything else in it, `tenant_id`, `id`, `role`, `project` or `author` among them, is ignored, and the request is answered as if it were not there: the organization comes from the key, ids from the database, a task's project from its path, and a role only from an admin's `PATCH /members/{id}`.

| Request | Status | Body |
|---------|--------|------|
| A member asking for an admin's action on an id of their organization | 403 | `{"error": "forbidden"}` |

A request is now checked for its key (401), its ids (404), the caller's role (403), and then its body (400).

### Example 1

<!-- case: v8 -->

Ari is a member, so `p-1` stays.

### Example 2

<!-- case: v9 -->

The project names `birch` in its body, and is `alder`'s anyway.

### Example 3

<!-- case: v10 -->

Ari renames themselves, and stays a member whatever the body says about the role.

## Level 4: Comments, closed from the start

Tasks get comments, in a table your migration adds. The baseline grants every new table to `tracker_app`, so a table without a policy is open to every organization from the moment it exists: give it its policy in the same migration that creates it. That is the classic hole of row-level security, and the one cases check for.

| Request | Answer |
|---------|--------|
| `POST /tasks/{id}/comments` with `{"body": "Draft is in the shared folder"}` | 201 with the comment: `{"id": "...", "task": "t-1", "author": "u-ada", "body": "Draft is in the shared folder"}`. The author is the caller. `body` is text of 1 to 1000 characters |
| `GET /tasks/{id}/comments` | 200 with the task's comments, in any order |
| `GET /search/comments?q=launch` | 200 with the comments whose body holds `q` whatever its case, in any order, with the rule for `q` of `/search/tasks`. Its query names no organization either |

A comment belongs to its task's organization, and deleting a task deletes its comments, as deleting a project deletes its tasks and theirs. The status codes and their order are those of level 3.

### Example 1

<!-- case: v11 -->

Ada comments on `t-1`, and the comment, read back, names her as its author.

### Example 2

<!-- case: v12 -->

Bea's comment holds "launch" too, but it is `birch`'s.

## Constraints

- Postgres 17, through `DATABASE_URL` as `tracker_app`, with node-pg-migrate's plain SQL migrations, run as `tracker_owner`. The baseline migration stays as it is.
- `/search/tasks` and `/search/comments` name no organization in their queries.
- Bursts of up to 32 requests at once, from several organizations; a case has 10 s for all its requests.
- Every answer of a case that repeats must be right on every run: a leak that shows one time in three still fails.
- Grading applies your migrations to a database that already holds an organization you never see, and to an empty one.

## Follow-ups

- The policies read a setting the app itself sets. What stops a bug, or an injected SQL statement, from setting another organization's id, and how would a signed token or a role per organization change that?
- One organization grows to half the rows. What does row-level security cost on its queries, and which index keeps the policy's filter cheap?
- A support engineer must read one organization's data to answer a ticket. How would you grant that without `BYPASSRLS`, and leave a trail?
- A large customer asks for its own database. What changes in the app, the migrations and the pool if some organizations get a schema or a database of their own?
- A background job reindexes every organization's tasks. Which role does it run as, and how does it stay inside one organization at a time?
- An organization leaves and wants its data deleted. How would you prove that every row it owned is gone, including rows a later table added?

## Hints

### Hint 1

At level 1, every query takes the caller's organization: `WHERE id = $1 AND tenant_id = $2`. An insert takes its `tenant_id` from the caller, never from the body.

### Hint 2

Look an id up within the caller's organization before anything else, and answer 404 when it is not there. Never look it up across organizations and then compare: that is the code that ends in a 403.

### Hint 3

A task's project comes from the path. Check that the project is the caller's before inserting, since without that check the key on the project would be the only thing refusing another organization's project.

### Hint 4

A policy is one statement per table: `CREATE POLICY ... USING (tenant_id = current_setting('app.tenant_id', true)) WITH CHECK (...)`, after `ALTER TABLE ... ENABLE ROW LEVEL SECURITY`. `USING` filters what is read, updated and deleted; `WITH CHECK` refuses a row written into another organization.

### Hint 5

`pool.connect()` gives you one connection to run `BEGIN`, `set_config('app.tenant_id', $1, true)`, your statements and `COMMIT` on, then `release()` it. Write that once, as a function that takes the organization and the work, and send every request through it, the search included.

### Hint 6

Read a body's fields one by one into a new object. Spreading the body into an insert or an update is how a client sets `tenant_id` or `role`.

### Hint 7

For level 4, write the table, its foreign key to the task by `(task_id, tenant_id)` as the baseline does for tasks, `ENABLE ROW LEVEL SECURITY` and the policy in one migration. Then `SET ROLE tracker_app` in `psql` and select from it without setting `app.tenant_id`: it should show nothing.
