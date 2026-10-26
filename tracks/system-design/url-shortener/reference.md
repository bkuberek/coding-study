# URL Shortener: Reference

## Requirements

Clarify before designing:

- **Two very different paths.** Create is low volume and can tolerate 300 ms; redirect is 100 times hotter, latency critical and must survive almost anything. Design and deploy them separately.
- **What "never redirects to the wrong destination" implies.** Codes are immutable once issued: a code is never reused, even after expiry, and the destination of a code never changes. That makes the link record write-once (apart from `status` and `expires_at`), which is what makes aggressive caching and asynchronous replication safe.
- **Analytics are best effort but bounded.** "At most 0.1% loss, 5 minutes lag" rules out writing a counter in the redirect path and rules out fire-and-forget UDP; it asks for a buffered, at-least-once pipeline with deduplication.
- **Out of scope unless asked:** link editing (changing destinations), QR codes, per-customer custom domains. Mention custom domains as an evolution because it changes the key.

## Estimates

| Quantity | Calculation | Result |
|----------|-------------|--------|
| Creates | 200 M / 2.6 M s per month | ~80/s average, ~400/s peak |
| Redirects | 100 x creates | ~7,700/s average, ~40,000/s peak |
| Links stored | 200 M x 12 months x 5 years | 12 billion |
| Link record | code 8 B, URL ~150 B, owner, timestamps, status, index overhead | ~500 B |
| Link storage | 12 B x 500 B | ~6 TB per full copy; ~18 TB with 3 replicas per region |
| Hot cache | ~100 M recently clicked links x 500 B | ~50 GB per region, a handful of cache nodes |
| Click events | 7,700/s x ~200 B | ~1.5 MB/s, ~130 GB/day raw |
| Redirect egress | 40,000/s x ~400 B response | ~16 MB/s peak, negligible |

Code length: 62^7 is 3.5 trillion, so 12 billion links fill 0.34% of the space and a random guess hits a real link about 1 time in 290. 62^8 (218 trillion) makes guessing 60 times harder for one extra character, and collisions on insert become negligible. Choose 8 characters for generated codes.

Conclusion from the numbers: storage and throughput are modest. The hard parts are latency under skew, uniqueness across regions, propagation of disables and lossless analytics, not scale.

## API

```text
POST /v1/links                       Idempotency-Key: <uuid>
  {"long_url": "https://...", "alias": "spring-sale", "expires_at": "2026-12-31T00:00:00Z"}
  201 {"code": "Ab3dE9xQ", "short_url": "https://sho.rt/Ab3dE9xQ", "expires_at": "..."}
  409 alias already taken; 422 invalid or blocked URL; 429 creation rate limit

GET /{code}
  302 Location: <long_url>, Cache-Control: private, no-store
  404 unknown code; 410 expired or disabled

GET   /v1/links?cursor=<opaque>&limit=50     the caller's links, newest first
PATCH /v1/links/{code}  {"status": "disabled"}  owner or trust-and-safety
GET   /v1/links/{code}/stats?from=2026-03-01&to=2026-03-31&group_by=country
```

Use 302 (or 307), not 301: browsers cache a 301 indefinitely, which would hide clicks from analytics and make a disabled link keep working in every browser that has seen it. The idempotency key makes a retried create return the same code instead of minting a second one.

## Data model

| Store | Key | Fields |
|-------|-----|--------|
| `links` (key-value or wide-column store) | `code` | `long_url`, `owner_id`, `created_at`, `expires_at`, `status` (`active`, `disabled`), `is_custom`, store-native TTL set to `expires_at` plus a grace period |
| `links_by_owner` (secondary index or table) | `owner_id`, sort by `created_at` desc | `code` |
| `idempotency_keys` | `(owner_id, key)` with 24 h TTL | `code`, request hash |
| `click_events` (log, partitioned by `code`) | `event_id` | `code`, `ts`, `country`, `referrer_domain`, `is_bot` |
| `clicks_daily` (columnar analytics store) | `(code, day, country, referrer_domain)` | `clicks` |

A key-value store fits: every redirect is a point lookup by code, there are no joins, and the store must scale horizontally with conditional writes (put-if-absent). A sharded relational database would also work at 6 TB; the deciding features are conditional insert, TTL and multi-region replication.

## High-level design

```text
create:  client --> API service --> code generator --> links store (primary region)
                                                         | async replication (~1 s)
redirect: viewer --> geo DNS / anycast LB --> redirect service --> in-process LRU
                                                    |            --> regional cache --> links store replica
                                                    +--> click buffer --> event log --> stream aggregator
                                                                                          --> clicks_daily <-- stats API
abuse:   links created --> URL scanner (blocklists) --> PATCH status=disabled --> invalidation fan-out
```

- **Redirect service**: stateless, deployed in all three regions behind geo DNS. Lookup order: in-process LRU (top few hundred thousand codes, seconds-long TTL), regional cache (Redis or Memcached, cache-aside), regional replica of `links`. Checks `status` and `expires_at` on every hit, so expiry needs no cache invalidation.
- **API service**: validates the URL, applies per-account rate limits, generates or reserves the code with a conditional write in the primary region, writes `links_by_owner`, and enqueues the URL for scanning.
- **Click pipeline**: the redirect service appends an event to an in-memory buffer and returns immediately; a background sender batches events to the log. A stream job deduplicates by `event_id`, filters bots and aggregates into `clicks_daily` every minute.

## Deep dives

### Code generation

| Option | Pros | Cons |
|--------|------|------|
| Counter plus base62 | No collisions, short codes | Sequential and enumerable; needs a coordinated counter (or ranges handed to each server) |
| Counter passed through a keyed permutation (for example a 64-bit block cipher) | Unique and non-sequential without collision checks | Key management; still needs the counter |
| Hash of the long URL, truncated | Deduplicates identical URLs | Collisions must be handled anyway; two customers shortening the same URL need different codes for separate analytics |
| Random 8 characters plus conditional insert | No coordination, unguessable, trivially multi-region | One extra write attempt on rare collisions |
| Pre-generated key pool | Fast create, no collision on the hot path | A separate service with its own durability and key-loss story |

Recommendation: random codes from a cryptographic RNG with a put-if-absent write, retried on collision (probability at most 0.0055% at end of life). Custom aliases use the same conditional write after checks against a reserved-word list and a profanity filter.

### Read path: latency and skew

- 40,000/s at peak is small for a cache cluster, but half of it targets 1% of links, so single cache shards would run hot. The in-process LRU absorbs the head of the distribution with no network hop; the regional cache handles the body.
- **Negative caching**: unknown codes are cached for 30 s so scanners cannot push misses through to the store; scanning IPs are rate limited on 404s.
- **Single-flight** on cache misses so a newly viral link causes one store read per server, not thousands.
- **CDN caching of redirects** is tempting but costs analytics (clicks served at the edge are invisible unless edge logs are ingested) and makes the 1-minute disable harder. At 40,000/s the origin is cheap enough; keep the CDN for TLS termination and anycast and revisit only if traffic grows 10 times.

### Uniqueness across regions and read-after-create

- Multi-region active-active stores usually resolve concurrent writes with last-writer-wins, which would let two regions grant the same custom alias. Route every create to one primary region: creates are 400/s and the 300 ms budget absorbs a cross-region hop. Random generated codes could be created anywhere, but one write path keeps the design simple.
- A link created in Europe and clicked from the US a second later may not have replicated yet. On a miss, the redirect service queries the primary region before returning 404, and only caches the negative result after that check. Misses are rare, so the extra hop is cheap.

### Click analytics without slowing redirects

- Never write analytics synchronously in the redirect path: a slow analytics store would become a redirect outage.
- Bounded in-memory buffer, batched sends with retries to a replicated log; on prolonged log unavailability, spill to local disk. That meets the 0.1% loss budget except for hard crashes of a redirect server, which lose at most one batch (about 1 second of that server's clicks).
- At-least-once delivery plus deduplication by `event_id` in the aggregator gives exact counts.
- Classify bots and link-preview fetchers (chat apps unfurl links) separately; customers care about human clicks.
- Country comes from a GeoIP lookup at the redirect service; the referrer domain from the `Referer` header, which is often absent.

### Expiry, disable and deletion

- Expiry is checked at read time from the cached record, so expired links stop at once with no invalidation; the store TTL deletes rows later, but the code stays reserved (a tombstone) so it is never reissued.
- Disable must take effect within 1 minute everywhere: the status change is written in the primary region, replicated, and published as an invalidation event that every region's redirect fleet consumes to drop the code from both cache tiers. Short TTLs on both tiers (30 s in process, 60 s in the regional cache) are the backstop if an invalidation is missed; with this skew, hot links still hit the cache almost every time.

## Failure modes

| Failure | Effect | Mitigation |
|---------|--------|------------|
| Regional cache cluster down | 40,000/s fall through to the store | Provision the store's read capacity for full cache loss, or shed load with priority to hot links; in-process LRU still absorbs the head |
| Primary region down | Creates fail | Creates are 99.9%: fail over the write path to a standby region with a fenced promotion; redirects keep working from replicas |
| Replication lag spike | New links 404 in other regions | Fallback read to the primary on miss |
| Event log down | Analytics delayed | Buffer and spill to disk; redirects unaffected |
| Malicious link | Phishing via a trusted domain | Scan at create, disable path with invalidation fan-out, interstitial warning pages for suspicious domains |
| Hot new link (campaign launch) | Cache stampede | Single-flight, in-process LRU, pre-warming when a customer schedules a campaign |

## Trade-offs

- **302 versus 301**: 302 keeps analytics and disable working at the cost of every click reaching the service.
- **Random codes versus counters**: random codes trade a rare retry for no coordination and no enumeration.
- **Single write region versus active-active writes**: simpler uniqueness and consistency for a low-volume path; costs create availability during a primary-region outage.
- **Consistency**: creates are strongly consistent in the primary region (conditional write); redirects are eventually consistent across regions, which is safe because records are write-once, with an explicit fallback for the only visible anomaly (read-after-create).
- **Origin versus edge redirects**: accurate analytics and fast disables now, versus lower latency and cost at much higher traffic.

## Observability and cost

- Redirect p50/p99 per region, cache hit ratio per tier (expect above 95% combined), 404 rate (a spike means scanning), fallback-to-primary rate (a proxy for replication lag), collision retry rate, event-log producer errors and buffer depth, aggregator lag (the 5-minute analytics SLO), time from disable to last redirect served.
- Cost is dominated by the always-on redirect fleet in three regions and the analytics store, not link storage (about 18 TB per region). Raw click events are kept for 30 days for reprocessing (about 4 TB), aggregates indefinitely.

## Evolution

- **Custom domains** (`go.customer.com/x`): the key becomes `(domain, code)`, and TLS certificates must be provisioned per domain.
- **Editable destinations** break the write-once assumption: cache TTLs and invalidation become correctness-critical.
- **Edge redirects** at much higher traffic, with edge logs shipped into the click pipeline.
- **Privacy**: deletion of click data per customer, IP truncation before storage.
