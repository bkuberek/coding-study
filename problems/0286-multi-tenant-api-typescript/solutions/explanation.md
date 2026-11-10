# Multi-Tenant API (TypeScript): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | per request | per request | default answer: every query names the caller's organization, every table answers only for the organization its transaction serves, and that setting lives exactly as long as the request's transaction |

## How the project grows level by level

| Level | New requirement | What the code adds |
|-------|-----------------|--------------------|
| 1 | Every read and write scoped to the caller's organization, with 404 for anyone else's ids | `authenticate` in `src/auth.ts`, `src/projects.ts` and `src/tasks.ts`, each query naming `tenant_id`, and `src/requests.ts` |
| 2 | Postgres enforces the scope, through a search whose query names no organization | `0002_row_level_security.sql`, and `asTenant` in `src/db.ts`, which every request now runs in |
| 3 | Members, roles, and bodies that cannot set what they should not | `src/members.ts`, `isAdmin`, and request readers that copy only the fields a request takes |
| 4 | Comments in a new table, closed from its first moment | `0003_comments.sql` with its policy, `src/comments.ts`, and `searchComments` |

## Approach: reference (Scope twice: every query by the caller's organization, every table by a policy, the organization set per transaction)

### Intuition

In a shared database, isolation is a property of every query. The app can keep it by naming the organization in every `WHERE`, and level 1 does exactly that. But a property that holds only while every developer remembers it on every query fails the first time someone writes a report, a search or an export in a hurry. Nothing in the app notices, since the query works; it just answers for everyone.

Row-level security moves the rule into the database, beside the data. A policy on a table is a `WHERE` that Postgres adds to every query on it, for every role it applies to, so a query that forgets the organization still sees only one. The policy needs to know which organization the transaction serves, and the app tells it at the start of each transaction with `SET LOCAL app.tenant_id`. The two layers back each other: the app's filters make the intent visible in the code, and the policies make a forgotten filter harmless. The search endpoint is the proof, since its query names no organization at all and answers correctly anyway.

The setting is where the subtle bug lives. A connection pool reuses connections across requests, and a plain `SET` lasts for the connection's life, so it outlives the request. Sent through `pool.query`, it may even land on a different connection from the query that follows. `SET LOCAL` ends with its transaction, so each request takes one connection, opens a transaction, sets the organization, does its work and commits, and the connection goes back to the pool serving nobody.

Existence is information. Answering 403 for another organization's id tells the caller that the id is real, which lets them enumerate customers. Looking every id up within the caller's organization makes the answer for "someone else's" and "nobody's" the same 404, without a special case.

The rest is about who decides. The organization comes from the key, ids from the database, a task's project from its path and a role from an admin's request; a body supplies only the fields a request takes. And a new table starts open, because the baseline grants every table to the app, so its policy belongs in the migration that creates it.

### Say it out loud

"Every request authenticates first: the key gives me the organization and the user. Then I run the whole request in one transaction on one pooled connection, and the first statement is `set_config('app.tenant_id', $1, true)`, which is `SET LOCAL` with a parameter. Every table with an organization's rows has row-level security and a policy comparing `tenant_id` to that setting, for reads and for writes, and my app connects as a role that owns no table and has no `BYPASSRLS`, so the policies apply.

"I still put `tenant_id` in every query, so the intent is in the code, and every lookup of an id happens inside the caller's organization, so another organization's id is a plain 404. The search query names no organization, and the policy alone scopes it. Inserts take the organization from the caller; bodies are read field by field, so `tenant_id` or `role` in a body does nothing. Admin actions look the row up first and then check the role, read fresh in the transaction. A new table gets its policy in the same migration, and its foreign key names the organization so it cannot point across."

### Algorithm

1. Read the key from `Authorization: Bearer <key>` and look it up in `api_keys`, the one table without a policy: no key, or an unknown one, is 401.
2. Match the route. Take one connection from the pool, `BEGIN`, and `set_config('app.tenant_id', <organization>, true)`.
3. Look up every id in the path with `WHERE id = $1 AND tenant_id = $2`: nothing found is 404.
4. For an admin's action, read the caller's role from `users` in the same transaction: a member is 403.
5. Read the body's own fields with their rules: anything wrong is 400, anything else is ignored.
6. Run the statement, with `tenant_id` from the caller on inserts, and answer. `COMMIT`, or `ROLLBACK` on an error, and release the connection.

### Design

| File | Holds |
|------|-------|
| `migrations/0002_row_level_security.sql` | Row-level security and a `tenant_isolation` policy, with `USING` and `WITH CHECK`, on `tenants`, `users`, `projects` and `tasks` |
| `migrations/0003_comments.sql` | `comments`, with a foreign key to tasks by `(task_id, tenant_id)` that cascades, an index by task, and its policy, in one migration |
| `src/db.ts` | The pool, and `asTenant`, which runs a request's work in one transaction on one connection with the organization set locally |
| `src/auth.ts` | `authenticate`, from the key, and `isAdmin`, read inside the transaction |
| `src/requests.ts` | The statement's field rules, each reading only its own fields |
| `src/projects.ts`, `src/tasks.ts`, `src/members.ts`, `src/comments.ts` | The routes, each lookup and statement naming the caller's organization |
| `src/search.ts` | The two searches, whose queries name no organization |
| `src/server.ts` | The route table: authenticate, then `asTenant` around the matched route |

`asTenant` is the only place that touches the setting, and every route runs inside it, so no request can run a query for no organization or for the previous caller's. `api_keys` stays outside the policies on purpose: it is read before the organization is known, only by the secret itself.

The reference checks in the order of the statement, 401, 404, 403, 400, so each lookup comes before the role and the body. A task's project and a comment's task are looked up in the caller's organization before the insert, and the composite foreign keys refuse a cross-organization link even if a later route forgot the lookup.

### Correctness

Every row of `users`, `projects`, `tasks` and `comments` names its organization, and every query `tracker_app` runs on them passes through a policy that keeps only the rows whose `tenant_id` equals the transaction's setting. `tracker_app` neither owns those tables nor bypasses row-level security, so no query of the app escapes that filter, whatever its text. The setting is set with `LOCAL` as the first statement of each request's transaction, on the connection that runs the rest of it, and Postgres drops it when that transaction ends, so a request reads the setting it set and no other. `WITH CHECK` refuses an insert or update whose row would belong to another organization, and inserts take `tenant_id` from the authenticated caller. An id outside the caller's organization is invisible to every lookup, so the answer is 404 whether the row exists elsewhere or not. A comment's key names its task and organization together, and key checks ignore policies, so without that a comment could point at a task it cannot see; with it, it cannot.

### Complexity

- Time: per request — each lookup is by primary key, lists and searches read one organization's rows; the policy adds a comparison to each row read
- Space: per request — the rows answered; one pooled connection held for the transaction

### Trade-offs

The reference filters twice: the policies alone would answer every case. Keeping `tenant_id` in the app's queries costs a parameter per query, makes the intent readable, and keeps the app correct if the policies are ever dropped or a table is migrated without one. Relying on the policies alone is shorter and leaves one source of truth; many teams do that, and then lint for queries that bypass the request's transaction.

A transaction per request holds a connection for the whole request, including time spent in the app between statements. With a pool of 10 and bursts of 32, requests queue for connections, which is fine here and worth measuring when requests do slow work, such as calling another service, in the middle.

The setting is plain text the app sets, so anything that can run SQL as `tracker_app` can claim any organization. That is the boundary this design accepts: the policies protect against the app forgetting, not against the app being taken over. A role per organization, or a setting derived from a signed token by a function the app cannot bypass, would protect against more, at a cost in roles or code.

A schema or a database per organization isolates more strongly and makes deleting a customer easy, but every migration then runs once per organization and the pool splits by organization. One schema with row-level security scales to many small organizations with one migration and one pool.

### Pitfalls and edge cases

**Wrong approaches.** Each fails a hidden case, and the failure names what it did. Parallel cases send their burst at once, behind a barrier, and repeat three times from a fresh database, so a leak that shows now and then still fails. None of these are stored as solutions. The first two were run by hand on a real stack, as the reference with its policies left out, and as the reference with a plain `SET` through the pool: the first passed 70 of 78 cases and the second 73, every single request included.

| What it does | Why it is wrong | What catches it |
|--------------|-----------------|-----------------|
| Filters by organization in the app only, with no policy | Correct for every query that remembers, and wide open on the one that does not | `v6`, `h30` to `h33`: `body: unexpected element {"id": "t-4", "project": "p-3", "title": "Shoot the launch photos", ...}`, and `v12`, `h60`, `h65` for comments: `step 2 GET /search/comments: body: expected 0 elements, got 1` |
| Sets the organization with a plain `SET`, through `pool.query`, then runs the queries through the pool | Each `pool.query` takes whichever connection is free, which still holds whatever organization was set on it last. One request at a time, the pool hands back the same connection, so it looks right | `v7`, `h36`, `h37`, `h38`, `h69`, each on its first run: `32 requests at once: expected 32 to answer 200; 13 answered 200 and 19 answered 404`, since a read served as the other organization finds nothing; the writes also answer 500 when the policy refuses the row |
| Connects as `tracker_owner`, or gives `tracker_app` `BYPASSRLS` | Owners and bypassing roles skip every policy | `v6`, `h30`, as for no policy at all |
| Looks an id up across organizations and answers 403 when it is another's | The 403 tells the caller that the id exists | `v2`, `h4`, `h6`, `h52`: `status: expected 404, got 403` |
| Inserts a task with the project id from the path and the caller's organization, without looking the project up | With a key on the project alone, the task joins another organization's project; with the baseline's key, the insert fails with a 500 | `h5`, `h27`, `h28` |
| Spreads the body into the insert or update | `tenant_id`, `id`, `role` or `project` in the body land in the row; with the policies, Postgres refuses the row and the answer is a 500 | `v9`, `v10`, `h47` to `h51` |
| Checks the role before looking the id up | A member asking about another organization's id hears 403 and learns it exists | `h52`, `h54` |
| Reads the caller's role once, with the key, and keeps it | A role an admin changed applies only to later keys | `h58` |
| A level 4 table without a policy, or with the policy in a later migration | The baseline's default privileges grant it to the app at once, open to every organization | `v12`, `h60`, `h65`: the comment search answers `alder`'s comment to `birch`, `expected 0 elements, got 1` |
| A comment's foreign key on the task id alone, with no lookup of the task | Key checks ignore policies, so a comment can point at a task its organization cannot see | `h61`, `h68` |
| Comments that do not go with their task | Deleting a task fails on the key, or leaves comments behind | `h66` |

**Edge cases.**

- An id nobody has and another organization's id answer the same 404 (`h9`, `v2`), and that check comes before the body's (`h28`).
- A key sent without `Bearer`, and a key nobody holds, are 401 (`h12`, `h13`).
- `PATCH /tasks/{id}` with `done: false` changes only `done`, and one with neither field is 400 (`h21`, `h23`).
- A name of 100 characters fits and one of 101 does not (`h18`, `h19`).
- `PATCH /me` needs a name, so a body with only a role is 400, and an admin who makes themselves a member is refused from the next request (`h57`, `h58`).
- The organization grading adds has its own key, and every list, search and lookup treats it as the others (`h10`, `h11`, `h27`, `h31`, `h42`).
