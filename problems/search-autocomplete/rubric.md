# Search Autocomplete: Rubric

## Requirements and scope

- [ ] Frames the problem as an offline pipeline plus a read-only lookup path.
- [ ] Separates the three freshness needs: long-term ranking, trending within 15 minutes, removals within 5 minutes.
- [ ] Notes that autocomplete must fail without breaking search.
- [ ] Addresses session consistency (no flicker between index versions).

## Estimates

- [ ] Derives about 70,000 requests/s average and 200,000/s peak from searches, debounce and keystrokes.
- [ ] Sizes the index (gigabytes to low tens of gigabytes per locale) and concludes it fits in one machine's memory.
- [ ] Uses that conclusion to choose replication over sharding.

## API and data model

- [ ] Defines a suggest endpoint with locale and an index version, and sets cache headers.
- [ ] Keeps server responses unpersonalized so the CDN and browser can cache them.
- [ ] Describes client behavior: debounce, cancelling stale requests, reusing results for longer prefixes.
- [ ] Models the query log, daily aggregates, index snapshots, trending overlay and blocklist.

## High-level design

- [ ] Shows the query log feeding both a batch build and a streaming trending job.
- [ ] Publishes versioned index snapshots that serving nodes load and swap atomically.
- [ ] Applies the blocklist at serving time, independent of the build.

## Deep dives

- [ ] Compares at least two index structures (trie with top-k per node, sorted array, FST, search-engine suggester) and picks one for the latency budget.
- [ ] Explains the build cost of precomputing top-k per prefix and caps prefix depth.
- [ ] Ranks with time decay and counts distinct users rather than raw searches, with a minimum-users floor for privacy.
- [ ] Merges a trending overlay at query time to meet the 15-minute freshness requirement.
- [ ] Breaks down the 150 ms budget (network, CDN, service) and caches the shortest prefixes aggressively.
- [ ] Handles personalization without losing cacheability (client-side merge, or a server lookup with a strict timeout).

## Failure modes and trade-offs

- [ ] Guards against a bad index with validation, canary rollout and instant rollback.
- [ ] Defends against manipulation of suggestions (bots, coordinated typing).
- [ ] Discusses hot prefixes and why prefix sharding would create hot shards.
- [ ] States the freshness versus complexity trade-off of batch plus overlay.

## Operations and evolution

- [ ] Names quality metrics (click-through on suggestions, keystrokes saved) as well as latency and cache hit rate.
- [ ] Monitors snapshot age, overlay age and blocklist propagation.
- [ ] Mentions typo tolerance, rich suggestions or learned ranking as next steps.
