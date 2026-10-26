# Distributed Rate Limiter: Reference

## Requirements

Clarify before designing:

- **Two purposes, two policies.** Plan enforcement (what a customer paid for) tolerates small errors and should fail open; backend protection and abuse prevention (login, SMS) must fail closed. Make the failure mode a property of each rule.
- **Accuracy budget.** "At most about 5% over" is what allows approximate algorithms, local batching and asynchronous global counting. Ask for it explicitly; an exact global limiter would cost a cross-region round trip per request.
- **Rule shapes.** Short windows with bursts (per second) and long quotas (per day) need different algorithms.
- **Where the limiter runs.** In the gateway process (a library) or as a separate service; the 2 ms budget decides this.
- **Out of scope:** concurrency limits (in-flight requests) and adaptive load shedding; mention them as evolution.

## Estimates

| Quantity | Calculation | Result |
|----------|-------------|--------|
| Checks | 1 M requests/s, one call per request covering all its rules | 1 M counter-store calls/s; ~400,000/s in the largest region |
| Counter store shards | ~50,000 scripted calls/s per shard, 2x headroom | ~16 primary shards in the largest region, plus replicas |
| Counter memory | 2 M active subjects x ~3 rules x ~100 B | ~600 MB: memory is not the constraint, operations per second are |
| Sliding log alternative | 1 M/s x 60 s window x ~80 B per entry | ~5 GB and a sorted-set operation per request for a per-minute rule; impossible for per-day rules |
| Latency | same-zone round trip 0.2-0.5 ms, cross-zone ~1 ms, cross-region 30-150 ms | Only a same-region counter store fits 2 ms; global limits cannot be checked inline |
| Per gateway | 1 M / 300 | ~3,300 requests/s per node |

The numbers point to: a regional, sharded in-memory counter store reached in one round trip, and an asynchronous mechanism for global quotas.

## API

Gateway-facing (an in-process library or sidecar):

```text
check(subjects: {api_key, user_id, ip, org_id}, route: "POST /v1/messages", cost: 1)
  -> {allowed: bool, rule_id, limit, remaining, reset_seconds, retry_after_seconds}
```

Caller-facing headers on every response, following the IETF RateLimit header fields draft, and `Retry-After` on 429:

```text
HTTP/1.1 429 Too Many Requests
Retry-After: 3
RateLimit-Policy: "burst";q=200;w=1, "daily";q=1000000;w=86400
RateLimit: "burst";r=0;t=3
```

Operator API:

```text
PUT /v1/rules/{rule_id}
  {"match": {"plan": "pro", "route": "POST /v1/messages"}, "subject": "api_key",
   "algorithm": "token_bucket", "rate_per_second": 100, "burst": 200,
   "scope": "regional", "failure_mode": "open", "mode": "shadow"}
PUT /v1/overrides/{subject_id}/{rule_id}  {"rate_per_second": 2000, "burst": 4000}
```

## Data model

| Store | Key | Value |
|-------|-----|-------|
| Rules (relational, source of truth) | `rule_id` | match, subject, algorithm, parameters, scope, failure mode, mode (`enforce`, `shadow`), version |
| Overrides (key-value, cached in gateways) | `(subject_id, rule_id)` | custom parameters |
| Token bucket state (in-memory store) | `rl:{<subject>}:<rule_id>` | hash `{tokens, updated_ms}`, TTL = time to refill completely |
| Window counter (in-memory store) | `rl:{<subject>}:<rule_id>:<window_start>` | integer, TTL = 2 windows |
| Global quota usage | `(subject, rule_id, day)` per region | count, last sync time |

The `{<subject>}` hash tag places all of a subject's counters on one shard, so one script call evaluates every rule for that subject atomically.

## High-level design

```text
client --> LB --> gateway node
                   |- rule cache (versioned snapshot, last known good)
                   |- override cache (TTL 60 s)
                   |- local lease cache for hot keys
                   |- fallback local limiter (used only when the store is unreachable)
                   +--> regional counter store (sharded in-memory, same zone), one script call
                   +--> backend (if allowed)

rule service (DB) --> config distribution (push + poll) --> gateways, within 30 s
gateways --> decision log (sampled) --> analytics: shadow-rule results, top throttled keys
regional quota aggregator <--> global quota service (async, every few seconds)
```

- The limiter is a library inside the gateway, calling the counter store directly: one network hop. A separate limiter service would add a second hop and its own tail latency to every request.
- One server-side script per subject reads, refills and decrements all applicable buckets and returns the most restrictive decision, so check-and-consume is atomic and costs one round trip.

## Deep dives

### Algorithm choice

| Algorithm | State | Behavior | Use |
|-----------|-------|----------|-----|
| Fixed window counter | 1 integer | Up to 2x the limit across a window boundary | Cheap daily quotas where boundary bursts do not matter |
| Sliding window log | 1 entry per request | Exact | Small limits only (login attempts per account) |
| Sliding window counter | 2 integers | Weights the previous window by its overlap; small error under roughly uniform traffic | Per-minute and per-hour limits |
| Token bucket | tokens + timestamp | Steady rate with bounded bursts | Per-second limits with bursts: the default |
| GCRA | 1 timestamp | Equivalent to a leaky bucket meter, no refill loop | Same as token bucket with less state |

Recommendation: token bucket (or GCRA) for rate-with-burst rules, sliding window counter for minute and hour rules, fixed windows aligned to the customer's billing day for daily quotas.

### Atomicity and time

- A naive read-then-write from the gateway races: two gateways read 1 remaining token and both admit. Do the whole check in one server-side script (or `INCR` then compare for window counters).
- Take time from one clock: the counter store's clock inside the script, so 300 gateways with skewed clocks do not refill buckets inconsistently.
- Idle keys expire by TTL, so memory tracks active subjects only.

### Hot keys and the latency budget

- One key at 50,000 requests/s would saturate the shard that owns it. **Token leasing**: a gateway that sees a hot key reserves a batch of tokens (for example 20) in one call and admits locally until the batch is spent or 100 ms pass. Calls for that key drop from 50,000/s to about 2,500/s.
- Leased tokens are already deducted centrally, so leasing never over-admits; it can under-admit by the unused leases outstanding, which is why leases are small and short-lived.
- Keep the store in the same zone as the gateways where possible, pipeline connections, and set a 5 ms client timeout so a slow shard cannot blow the request budget.

### Global limits across regions

| Option | Accuracy | Latency | Verdict |
|--------|----------|---------|---------|
| One global counter store | Exact | +30-150 ms per request | Rejected |
| Split the limit per region (limit / 3) | Unfair when traffic is uneven across regions | None | Acceptable only for evenly spread traffic |
| Regional counts plus asynchronous sync | Overshoot of at most rate x sync interval x regions | None | Chosen for daily quotas |
| Quota leasing from a global allocator | No overshoot; regions borrow chunks | Only when a chunk runs out | Chosen when overshoot is unacceptable |

For a 1 M/day quota at 1,000 requests/s with a 5 s sync, worst-case overshoot is about 15,000 requests (1.5%), inside the 5% budget.

### Failure modes and fallback

- Counter store shard unreachable or over its timeout: fail-open rules switch to the local fallback limiter (limit divided by the number of gateways, a rough but bounded approximation); fail-closed rules reject with 503 rather than 429, so callers do not think they exceeded a quota. A circuit breaker stops gateways from waiting on a dead shard.
- Rules service down: gateways keep the last known good snapshot; a new gateway that has never loaded rules starts in a conservative default.
- A bad rule (limit set to 0 for everyone): shadow mode first, staged rollout of rule changes, and a fast rollback to the previous snapshot version.

## Trade-offs

- **Accuracy versus latency**: central counters per request are accurate within a region; leasing and local fallback trade accuracy for latency and availability.
- **Availability versus correctness**: the limiter is an AP component for plan enforcement (fail open) and a CP one for abuse protection (fail closed); the rule decides.
- **Library versus service**: a library saves a hop and a dependency but couples gateway releases to limiter logic; the server-side script keeps the algorithm in one place either way.
- **Regional versus global**: most limits are regional because global exactness costs a cross-region round trip; global quotas accept bounded overshoot.

## Observability and cost

- Decisions per rule and outcome (allowed, rejected, shadow-rejected), limiter latency p99, store CPU and calls per shard (hot shards), lease hit rate, fallback activations, rule snapshot version per gateway (stale gateways), measured overshoot against limits from sampled decision logs.
- Customer-facing: 429 rate per customer; a large customer suddenly throttled is a support incident before it is a metric.
- Cost is small: about 16 small in-memory shards with replicas per large region. The expensive part is operational: rule governance and debugging "why was I throttled", so log the rule id with every rejection.

## Evolution

- Concurrency limits (in-flight requests), which need release on completion and a TTL for leaked slots.
- Cost-weighted limits, where an expensive endpoint consumes more tokens.
- Adaptive limits driven by backend health (load shedding), and weighted fairness between tenants.
- Quotas tied to billing, with usage exported to invoicing.
