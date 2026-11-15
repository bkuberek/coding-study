# Search Autocomplete: Reference

## Requirements

Clarify before designing:

- **Read-only at serving time.** Suggestions are computed offline from the query log; the serving path only looks up a prefix. That makes this a data-pipeline problem plus a very fast read path, not a write-heavy system.
- **Freshness has three speeds**: the long-term ranking (days), trending queries (15 minutes) and removals (5 minutes). Each needs its own mechanism.
- **Session consistency**: pin a session to one index version so suggestions do not flicker between versions as the shopper types.
- **Personalization scope**: only the shopper's own recent searches; no collaborative "people like you" ranking in scope.
- **Failure isolation**: autocomplete is an enhancement; the search box must work without it.

## Estimates

| Quantity | Calculation | Result |
|----------|-------------|--------|
| Requests | 100 M x 10 searches x 6 requests | 6 B/day, ~70,000/s average, ~210,000/s peak |
| Query log | 1 B searches x ~100 B | ~100 GB/day |
| Index strings | 50 M queries x ~25 B | ~1.25 GB |
| Prefix nodes | ~250 M distinct prefixes (shared, depth capped at 25 characters) | |
| Top-10 per prefix | 250 M x (10 x 4 B query ids + ~20 B node) | ~15 GB per large locale |
| Serving nodes | ~20,000 requests/s per node; 40% of requests served by CDN or browser cache | ~126,000/s at the origin: ~7 nodes of load, ~15-20 nodes with headroom across zones and regions |

Conclusion: the whole index for a locale fits in memory on one machine, so replicate it to every serving node instead of sharding it; there is no fan-out on the read path.

## API

```text
GET /v1/suggest?q=iph&locale=en-US&v=<index_version>
  200 {"version": "2026-03-14T02:00Z+t0915",
       "suggestions": [{"text": "iphone 15 case", "kind": "query"}, ...]}
  Cache-Control: public, max-age=300 (prefixes up to 3 characters), max-age=60 otherwise
```

- The response is not personalized, so the CDN and browser can cache it; the client merges the shopper's recent searches on top.
- `v` pins the session to an index version; the service serves that version while it is still loaded, otherwise the newest.
- Clients debounce (100 ms), cancel in-flight requests when a new keystroke arrives, and reuse results: if `iph` returned fewer than 10 suggestions, `ipho` can be filtered locally.

## Data model

| Data | Store | Shape |
|------|-------|-------|
| Query log | event log, then data lake | `(ts, locale, normalized_query, user_hash, clicked_suggestion, result_count)` |
| Daily aggregates | data lake | `(locale, normalized_query, day, searches, distinct_users)` |
| Index snapshot | object storage, loaded into memory | prefix structure -> top-10 `(query_id, score)`; `query_id -> display text` |
| Trending overlay | small in-memory map, replaced every few minutes | prefix -> top-k trending `(query_id, score)` |
| Blocklist | replicated config, pushed to nodes | normalized terms and patterns |
| Recent searches | key-value store, keyed by user id (or the browser's local storage) | last 50 queries |

## High-level design

```text
browser (debounce, cache, merge recent searches)
   --> CDN (caches unpersonalized prefixes)
   --> suggest service (index snapshot + trending overlay + blocklist, all in memory)

search service --> query log --> stream job (5-min windows) --> trending overlay --> suggest nodes
                            --> data lake --> daily build (decay scoring, filters, top-k per prefix)
                                          --> validation --> snapshot in object storage --> canary --> all nodes
```

- **Suggest service**: stateless apart from read-only snapshots. A lookup walks the prefix to its node, merges the precomputed top-10 with the overlay's entries for the same prefix, drops blocked terms and returns.
- **Daily build**: aggregates 30+ days of counts with exponential decay, normalizes and deduplicates, filters, builds the prefix structure and publishes a versioned snapshot.
- **Trending job**: counts queries in sliding 5-minute windows, compares with each query's baseline and emits a small overlay of risers.

## Deep dives

### Index structure

| Option | Lookup | Build | Memory |
|--------|--------|-------|--------|
| Trie with top-k stored at every node | O(prefix length) | Propagate each query's score to its ancestors, keep k best | Largest; mitigate with a depth cap and compact node layout |
| Sorted array of queries plus binary search | O(log n) to find the range | Sort | Smallest, but top-k over a range needs a precomputed range-max structure |
| Finite state transducer | O(prefix length) | Sorted input, minimized automaton | Very compact; shares suffixes as well as prefixes |
| Search engine completion suggester or edge n-grams | Engine-dependent | Engine-managed | Operationally convenient, less control over latency |

Recommendation: a compact trie (or FST) with precomputed top-10 per node, capped at 25 characters (deeper prefixes reuse the deepest node's list, filtered). Precomputing makes the hot path a pointer walk, which is what the 20 ms budget wants.

### Ranking and normalization

- Score = sum over days of distinct searchers x decay^age (half-life of about a week). Counting distinct users rather than raw searches stops one bot or one obsessive shopper from promoting a query.
- Normalize case, whitespace and accents; keep the most common display form ("iPhone 15 case").
- Drop queries below a minimum number of distinct users: a privacy floor (no suggestion leaks one person's search) and a quality floor.
- Signal for later tuning: suggestion click-through rate and keystrokes saved.

### Freshness: batch plus overlay

- Daily full rebuild for the long-term ranking; it is simple, reproducible and easy to validate.
- A streaming job produces a trending overlay every few minutes; the service merges it at query time. The overlay is small (thousands of prefixes), so it is cheap to push to every node.
- Removals bypass both: the blocklist is pushed to nodes directly and applied on every response, so an urgent removal takes effect in minutes without a rebuild. CDN entries for affected prefixes are purged.

### Latency budget

- 150 ms end to end: network round trip 30-80 ms, CDN hit avoids the origin entirely, the service spends well under 1 ms on the lookup; the rest is serialization and queuing.
- The one-character and two-character prefixes are a small set and the hottest; cache them at the CDN for minutes and even ship them with the page.
- Personalization must not cost latency: merging recent searches on the client keeps the server response cacheable. If the server merges instead, the history lookup gets a 5 ms timeout and is skipped on timeout.

### Index rollout and session consistency

- Build, validate (size within expected bounds, no blocked terms, golden prefixes still return expected suggestions), canary on a few nodes, then roll out. Keep the previous two snapshots loaded or on local disk for instant rollback.
- Nodes keep the old snapshot loaded until sessions pinned to it (by `v`) age out, typically one search.

## Failure modes

| Failure | Effect | Mitigation |
|---------|--------|------------|
| Bad index build (offensive or broken suggestions) | Brand damage at scale | Validation gates, canary, rollback, blocklist applied at serving time |
| Trending job lagging | Trends appear late | Base index unaffected; alert on overlay age |
| Coordinated manipulation (bots typing a query) | Spam suggestions | Distinct-user counting, bot filtering, rate of growth anomaly checks, manual blocklist |
| Suggest service down or slow | No suggestions | Client gives up after its timeout; search works normally |
| Node out of memory during snapshot swap | Node crash | Load the new snapshot memory-mapped from local disk, swap a pointer, unmap the old one |

## Trade-offs

- **Replicated full index versus sharding by prefix**: replication avoids fan-out and hot shards (`a` and `s` are far hotter than `x`) at the cost of RAM on every node; shard only when one locale outgrows a machine.
- **Precomputed top-k versus computing at query time**: fast, predictable lookups at the cost of build time and memory; ranking changes require a rebuild or an overlay.
- **CDN caching versus personalization**: keeping server responses unpersonalized makes them cacheable; personalization moves to the client.
- **Freshness versus simplicity**: a daily batch alone is simple; the overlay adds a streaming job but meets the 15-minute requirement without a full streaming index.

## Observability and cost

- Latency p50/p99 at the service and from real-user monitoring, CDN hit rate by prefix length, snapshot age and version per node, overlay age, blocklist propagation time, empty-result rate, suggestion click-through rate, keystrokes saved per search.
- Cost: a modest serving fleet whose size is set by RAM per node and requests per second; the CDN absorbs the hottest prefixes. The daily build is a few hours of batch compute over about 3 TB (30 days of logs).

## Evolution

- Typo tolerance: fuzzy matching within edit distance 1 using a Levenshtein automaton over the FST.
- Rich suggestions: categories ("in Electronics") and products, which need a second index and blending.
- Learned ranking on click-through data, with the precomputed list as candidate generation.
- More locales and regional variants; per-region trending.
