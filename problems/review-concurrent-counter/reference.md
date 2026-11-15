# Review: Concurrent Counter Service: Reference

Verdict: request changes. The two blockers can crash or stall every instance under normal load, and several majors under-bill, double-bill or leak data. The direction (in-process aggregation, periodic flush) is sound; the synchronization and lifecycle need rework. A good review leads with the crash, proposes one coherent fix for the locking (below) instead of a dozen line comments, and asks whether billing needs exactly-once flushes.

A shape to suggest for the core:

```go
func (c *Counter) Record(tenant string, n int64) {
	c.mu.Lock()
	c.counts[tenant] += n
	c.mu.Unlock()
}

func (c *Counter) Flush(ctx context.Context) error {
	c.mu.Lock()
	pending := c.counts
	c.counts = make(map[string]int64, len(pending))
	c.mu.Unlock()
	// Write pending outside the lock, with a timeout and an idempotent batch id;
	// merge failed tenants back into c.counts under the lock.
}
```

## Blocker

- `counter.go:45` `Record`: `c.counts[tenant] += n` writes the map without holding the lock. With thousands of goroutines calling `Record`, the Go runtime aborts the whole process with `fatal error: concurrent map writes` (or `concurrent map read and map write` against `Flush`); this is not a recoverable panic. Every write to `counts` must happen under `mu.Lock()`. Ask the author to run the tests with `go test -race`, which reports it immediately.
- `counter.go:72-86` `Flush`: holds the write lock for the whole loop of `AddUsage` database calls. For as long as the flush runs (one round trip per tenant, every 10 s), every request blocks in `Record` waiting for the lock. The flush uses `context.Background()` (`counter.go:65`), so a slow or hung database blocks every API request on the instance indefinitely: a database incident becomes a full API outage. Swap the map under the lock and do the I/O after releasing it; give the flush a deadline (for example 5 s).

## Major

- `counter.go:32-43` `Record`: check-then-act. Two goroutines that see a new tenant at the same time both call `EnsureTenant`, and the second `c.counts[tenant] = 0` overwrites increments recorded in between, so usage is lost (under-billing after every restart, when every tenant is new). Remove the existence check from the hot path entirely: create the tenant row lazily in the flush, or make `AddUsage` an upsert (`INSERT ... ON CONFLICT (tenant) DO UPDATE SET units = usage.units + EXCLUDED.units`).
- `counter.go:50` `Pending`: value receiver `func (c Counter)` copies the struct, including the mutex. The read lock is taken on the copy, so it protects nothing (a data race with `Record`), and if the copy is made while `Flush` holds the lock, the copied mutex is already locked and `RLock` blocks forever. `go vet` reports this (`Pending passes lock by value`). Use a pointer receiver; consider adding `go vet` to CI.
- `counter.go:60` `Snapshot`: returns the internal map itself. The read lock is released on return, and `UsageHandler` then encodes the map while `Record` writes it: another `concurrent map iteration and map write` crash path. Return a copy built under the lock.
- `http.go:11` `Middleware`: bills the tenant named in the client-supplied `X-Tenant-ID` header. Any caller can bill another customer or bill nobody (an empty header becomes tenant `""`). The middleware also wraps the whole mux, before `handlers.API` authenticates. Record usage after authentication, from `auth.TenantFrom(r.Context())`, for example as middleware inside `handlers.API`.
- `http.go:12-15`: a metering failure (for example `EnsureTenant` failing during a database blip) returns 500 and drops the customer's request. Metering should never make the API less available than it was: record in memory, log and count errors, alert on them.
- `main.go` `/internal/usage`: mounted on the public listener, so anyone on the internet can read every tenant's name and pending usage. Mount it on the admin listener like the other `/internal/` routes, and require authentication.
- `counter.go:63-69` lifecycle: the flush goroutine is started in the constructor and never stopped, and nothing flushes on shutdown. Every deploy (several a day, 40 instances) drops up to 10 seconds of billable usage per instance, and `log.Fatal(server.ListenAndServe())` gives no chance to flush. Add `Run(ctx)` / `Close(ctx)`, call it from a graceful shutdown on `SIGTERM` (`server.Shutdown` then a final flush).
- `counter.go:80-83` partial and ambiguous failures: `AddUsage` increments a counter, so a call that commits but times out on the way back is retried on the next flush and billed twice; one failing tenant also stops the flush of every tenant after it in map order. Ask whether billing needs exactly-once: if yes, write each flush as one batch with an idempotency id (or insert usage events keyed by `(instance, flush_seq, tenant)` and sum them); either way, continue past individual failures.

## Minor

- `counter.go:83`: flushed tenants are reset to 0 instead of deleted, so the map (and `Snapshot` output) grows with every tenant ever seen by the instance. Delete after a successful flush; the swap-the-map approach does this for free.
- `counter_test.go:30`: waits for the background loop with `time.Sleep(11 * time.Second)`. That makes the suite slow and still racy (the fake store's map is written by the flush goroutine and read by the test with no synchronization). Call `Flush` directly in tests and inject the interval.
- `counter_test.go`: only sequential calls are tested. Add a test with many goroutines calling `Record` concurrently with `Flush`, run under `-race`, asserting the total is exact. That test would have caught both blockers.
- `UsageHandler`: errors from `Encode` are ignored and there is no `Content-Type: application/json`.

## Nit

- `counter.go:64`: prefer `time.NewTicker` with `defer ticker.Stop()` inside a loop that also selects on `ctx.Done()`; it is what makes the shutdown above possible.
- `counter.go:24-28`: starting a goroutine in a constructor surprises callers and tests; make the loop explicit (`go counter.Run(ctx)` in `main`).
- `10 * time.Second` appears in a comment and in code; make it a named option.
- `counter.go:38`, `counter.go:81`: wrap errors with context, `fmt.Errorf("add usage for %q: %w", tenant, err)`.
- With the full `Lock` in `Record`, the `RWMutex` buys nothing; a plain `sync.Mutex` is clearer. Sharding the map or per-tenant `atomic.Int64` values is an option only if profiling shows lock contention.
