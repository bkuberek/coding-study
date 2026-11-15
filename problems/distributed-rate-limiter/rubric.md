# Distributed Rate Limiter: Rubric

## Requirements and scope

- [ ] Distinguishes plan enforcement from backend and abuse protection, and makes fail-open versus fail-closed a per-rule choice.
- [ ] Asks for the accuracy budget and uses it to justify approximation.
- [ ] Recognizes that per-second burst limits and per-day quotas need different algorithms.
- [ ] Decides where the limiter runs (library, sidecar or service) from the 2 ms latency budget.

## Estimates

- [ ] Converts 1 M requests/s into counter-store calls per second and a shard count.
- [ ] Shows memory is small (hundreds of megabytes) and operations per second are the real constraint.
- [ ] Uses round-trip latencies (same zone, cross zone, cross region) to rule out an inline global counter.

## API and data model

- [ ] Defines the check call with its inputs (subjects, route, cost) and outputs (allowed, remaining, reset, retry after).
- [ ] Returns 429 with `Retry-After` and limit headers, and returns a different status when a fail-closed rule cannot be evaluated.
- [ ] Models rules with algorithm, parameters, scope, failure mode and a shadow mode.
- [ ] Keys counters so all of a subject's rules live on one shard (hash tag) with TTL-based cleanup.

## High-level design

- [ ] Places an in-process or sidecar limiter in the gateway with a regional sharded in-memory counter store.
- [ ] Distributes rules to gateways with versioned snapshots and last-known-good behavior, meeting the 30 s propagation target.
- [ ] Logs decisions (sampled) for shadow rules and for debugging rejections.

## Deep dives

- [ ] Compares fixed window, sliding log, sliding window counter and token bucket (or GCRA) with their state cost and boundary behavior.
- [ ] Makes check-and-consume atomic (server-side script or atomic increment), not read-then-write from the gateway.
- [ ] Uses a single clock source to avoid skew between gateways.
- [ ] Handles a hot key with token leasing or local batching, and explains why deducted leases under-admit rather than over-admit.
- [ ] Designs global quotas with asynchronous regional sync or quota leasing and bounds the overshoot with numbers.

## Failure modes and trade-offs

- [ ] Specifies behavior when a counter shard is slow or down: timeout, circuit breaker, local fallback limiter, fail-closed rules.
- [ ] Protects against a bad rule with shadow mode, staged rollout and rollback.
- [ ] States the CAP position: available and approximate for plan limits, consistent and closed for abuse limits.

## Operations and evolution

- [ ] Names the key metrics: decisions per rule, limiter latency, per-shard load, fallback activations, measured overshoot, rejections per customer.
- [ ] Makes "why was I throttled" answerable (rule id in logs and headers).
- [ ] Mentions concurrency limits, cost-weighted limits or adaptive load shedding as next steps.
