# Members in Python: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | per request | per request | Always |

## Approach: reference (Reference)

### Intuition

The members live in the database and are read on each request; the plan is one more column, added by a migration that keeps every row.

### Algorithm

1. Read a member or its plan with one query per request.
2. Count a visit with `INCR` in the cache.
3. Add the plan column with `ALTER TABLE ... ADD COLUMN ... DEFAULT 'flex'`.

### Design

- `src/server.py`: the routes, one connection per request.
- `migrations/0002_plans.sql`: the plan column, added in place so existing members keep their rows.
- A connection pool and a cache of members cannot be graded over HTTP: they belong here.

### Correctness

The migration alters the table instead of recreating it, so a member loaded before it ran is still there after.

### Complexity

- Time: per request — one query or one cache call
- Space: per request — one row

### Trade-offs

A connection per request is slow under load, and simple to get right.

### Pitfalls and edge cases

Dropping and recreating the table passes every visible case, since only the seeded members are there; a member loaded before the migration is lost.
