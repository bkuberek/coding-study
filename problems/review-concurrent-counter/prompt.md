# Review: Concurrent Counter Service

## Context

You work on the public API server of a SaaS platform, written in Go. Customers are billed per API call. Until now, billing was computed overnight from access logs; this pull request moves metering into the server so usage reaches billing within a minute.

Facts about the codebase that are not visible in the diff:

- The server runs as 40 instances, each serving about 5,000 requests per second from many goroutines. It is deployed several times a day.
- `handlers.API` authenticates every `/v1/` request and stores the tenant in the request context; handlers read it with `auth.TenantFrom(ctx)`.
- Paths under `/internal/` are normally served by a separate admin listener on port 9090 that is only reachable from the corporate network.
- `storage.NewUsageStore(db)` already exists. `EnsureTenant` inserts a usage row for the tenant if it is missing; `AddUsage` runs `UPDATE usage SET units = units + $2 WHERE tenant = $1` against Postgres.

## Pull request

**Add in-process usage metering**

> Records one billable unit per request in memory and flushes the totals to the usage table every 10 seconds, so billing no longer waits for the nightly log job. Adds `/internal/usage` so support can see pending usage for a tenant. Tested locally with `go test ./...`.

## Task

Review the change as you would a teammate's pull request, in about 30 minutes. For each issue, give its location, its severity (blocker, major, minor or nit), what goes wrong and the change you would ask for. Ask about intent where the right fix depends on it. End with your overall verdict.
