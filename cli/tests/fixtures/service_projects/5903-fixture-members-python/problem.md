# Members in Python

## Statement

A coworking space keeps its members in Postgres and counts their visits in Redis. Build the small service that answers for both, and change its schema without losing a member.

## Input

HTTP requests on `/members/{id}`, `/members/{id}/plan` and `/visits/{id}`.

## Output

JSON. Your app reads its port from `PORT`, the database from `DATABASE_URL` and the cache from `REDIS_URL`, listens on all interfaces inside the container (`0.0.0.0`), and `/health` answers 2xx once it is ready.

## Project

`src/server.py` starts the service. `scripts/migrate.py` runs first and applies each new file in `migrations/` in name order, recording what it applied; `migrations/0001_baseline.sql` is the baseline. Members with an id of 900 or more are reserved: the grader loads its own there, into the baseline, before your migrations run, so a migration must carry existing members forward.

## Level 1: Find a member

`GET /members/{id}` answers the member, and an id nobody has is a 404 with `{"error": "no such member"}`. `POST /visits/{id}` counts a visit in the cache and answers the count.

### Example 1

<!-- case: v1 -->
A member: `GET /members/1` answers 200 with `{"id": 1, "name": "Ada"}`.

### Example 2

<!-- case: v2 -->
A first visit: `POST /visits/1` answers 200 with `{"member": 1, "visits": 1}`.

## Level 2: Plans

Every member has a plan, `flex` unless it changed. `GET /members/{id}/plan` answers it, and `PUT /members/{id}/plan` with `{"plan": "..."}` changes it. Add the column in a new migration.

### Example 1

<!-- case: v3 -->
A plan: `GET /members/1/plan` answers 200 with `{"id": 1, "plan": "flex"}`.

### Example 2

<!-- case: v4 -->
A change: after `PUT /members/2/plan` with `{"plan": "fixed"}`, `GET /members/2/plan` answers 200 with `{"id": 2, "plan": "fixed"}`.

## Constraints

- Never edit a migration that has run: add a new one.

## Hints

### Hint 1

`ALTER TABLE` keeps the rows a table holds; dropping it does not.

### Hint 2

The Redis protocol is small enough to speak over a socket.
