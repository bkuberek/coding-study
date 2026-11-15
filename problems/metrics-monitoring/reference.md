# Metrics and Monitoring: Reference

## Requirements

Clarify before designing:

- **The scaling unit is the series, not the sample.** Memory, index size and query cost grow with the number of distinct label combinations; cardinality limits are a core feature, not an afterthought.
- **The alerting path is the most critical path.** It must keep working when dashboards, long-term storage or a whole region are down; design it with the fewest dependencies.
- **Push or pull**: the prompt says agents send data, so ingestion is push from host agents (which may themselves scrape local processes). Pull is a valid alternative to discuss.
- **Retention costs money per tier**: compute each tier's size before accepting the retention policy as given.
- **Out of scope**: logs, traces, anomaly detection; exemplars that link metrics to traces are an evolution.

## Estimates

| Quantity | Calculation | Result |
|----------|-------------|--------|
| Ingest rate | 200 M series / 10 s | 20 M samples/s |
| Raw tier | 20 M/s x 86,400 s x ~1.4 B per compressed sample | ~2.4 TB/day, ~36 TB for 15 days |
| 1-minute tier | 200 M series x 1,440 points/day x 4 aggregates x ~2 B | ~2.3 TB/day, ~210 TB for 90 days |
| 1-hour tier | 200 M x 24 x 4 x ~2 B | ~38 GB/day, ~28 TB for 2 years |
| Ingester memory | ~2 KB per active series (labels, open chunks, index) x 200 M x replication 3 | ~1.2 TB of RAM |
| Alert evaluations | 50,000 rules / 30 s | ~1,700 queries/s, all over recent data |
| Dashboard queries | 2,000 viewers x 20 panels / 30 s | ~1,300 queries/s, mostly the same recent windows |

The 1-minute tier is six times larger than the raw tier, because four aggregates per minute compress far worse than raw samples. That is worth raising with the stakeholders: 5-minute rollups for 90 days (~41 TB), or 1-minute rollups only for 30 days, cover the same investigations at a fifth of the cost.

Compressed samples average about 1.4 bytes because timestamps arrive at regular intervals (delta-of-delta encoding stores almost nothing) and consecutive values are similar (XOR encoding of floats), as in the Gorilla paper.

## API

```text
POST /v1/write          protobuf, snappy-compressed batches
  [{labels: {__name__: "http_requests_total", service: "checkout", region: "eu-1", code: "500"},
    samples: [(ts, value), ...]}, ...]
  204, or 429 with Retry-After (tenant over its limits), or 400 for samples too old or too far in the future

GET /v1/query_range?expr=sum by (service)(rate(http_requests_total{code=~"5.."}[5m]))&start=&end=&step=30s
GET /v1/labels, /v1/label/{name}/values, /v1/series?match=...      metadata for query builders

PUT /v1/rules/{group}   [{alert: "CheckoutErrors", expr: "...", for: "5m", labels: {severity: "page"}, annotations: {...}}]
PUT /v1/silences         {matchers, starts_at, ends_at, created_by, comment}
GET /v1/tenants/{team}/usage     active series, samples/s, top label cardinalities, limits
```

## Data model

| Data | Representation |
|------|----------------|
| Series identity | metric name plus sorted label set, hashed to a 64-bit series id |
| Inverted index (per block) | `label=value -> sorted list of series ids` (postings); a query intersects postings lists |
| Samples | per series, compressed chunks of about 120 samples (timestamps delta-of-delta, values XOR) |
| Head block | the last ~2 hours in ingester memory, protected by a write-ahead log |
| Persistent blocks | immutable 2-hour blocks (index plus chunks) in object storage, compacted into larger blocks |
| Rollup blocks | per series and interval: min, max, sum, count (enough for averages and rates; histograms keep bucket sums) |
| Alert state | `(rule, label set) -> inactive / pending since / firing since` |
| Notification log | which alert groups were sent to which receivers, for deduplication |

## High-level design

```text
host agent (scrape local processes, batch, disk buffer)
   --> ingestion gateway (auth, per-tenant rate and series limits, timestamp sanity)
   --> durable log, partitioned by series hash (decouples ingestion from storage, allows replay)
   --> ingesters (head block in memory + WAL, 3 replicas per series)
         --> every 2 h: flush blocks to object storage
compactor: merge blocks, build rollups, enforce retention per tier
store gateways: serve historical blocks (cached index and chunks)
query frontend: split by time, results cache, per-tenant limits
   --> queriers: recent data from ingesters + history from store gateways, merge and deduplicate
rule evaluators (sharded by rule group, 2 replicas) --> query recent data from ingesters
   --> alert manager cluster (group, deduplicate, inhibit, silence, route) --> pager, chat
meta-monitoring: a small independent stack watching this one, plus a dead man's switch to an external pager
```

- Ingestion, storage and query scale independently: ingesters by active series, store gateways by history queried, queriers by query load.
- Object storage holds everything older than two hours: cheap, durable and replicated by the provider, so the platform keeps only the head block replicated itself.

## Deep dives

### Cardinality and multi-tenancy

- A label holding user ids or request ids turns one metric into millions of series, each costing memory in every ingester replica. Enforce per-tenant limits on active series and per-metric limits at the gateway: existing series keep flowing, new series beyond the limit are rejected and counted.
- Give teams a cardinality view: their top metrics and labels by series count, so they fix it themselves.
- Churn from short-lived containers creates 20 million new series a day; each costs index space in every block it touches. Keep pod-level labels off high-volume metrics where service-level aggregation is enough, and aggregate at the agent when possible.

### Time-series storage

- Append-only, time-ordered, mostly recent reads: an in-memory head with a write-ahead log, then immutable compressed blocks, fits better than a general-purpose database storing one row per sample.
- Queries select series through the inverted index (`service="checkout" AND code=~"5.."` intersects postings lists), then decode only the chunks in the time range.
- Compaction merges small blocks into day-sized ones, reducing index lookups for long ranges.

### Downsampling and retention

- The compactor builds rollups from raw blocks. Store min, max, sum and count, so averages, maxima and rates can be computed at any lower resolution.
- Percentiles cannot be averaged: the average of hourly p99s is not the p99 of the day. Keep histogram bucket counts in rollups and compute percentiles from summed buckets.
- The query engine picks the resolution from the range and step: raw for recent windows, rollups beyond, so a 90-day panel reads about 2,000 hourly points per series instead of 777,600 raw samples.
- Retention is deleting whole blocks past each tier's age: cheap and immediate.

### Alert evaluation

- Rule groups are spread across evaluators by consistent hashing; each group runs on two evaluators for high availability, and the alert manager deduplicates their notifications.
- Rules read only from ingesters (the last hour), so alerting does not depend on object storage, store gateways or the query frontend.
- `for: 5m` requires the condition to hold across consecutive evaluations, which suppresses flapping; pending and firing state is checkpointed so an evaluator restart does not re-page or forget an incident.
- Evaluate slightly behind real time (for example 30 seconds) so late samples are not mistaken for absence, and alert explicitly on absent data where silence would be dangerous.
- Encourage symptom-based alerts on service-level objectives with multi-window burn rates; they page less and catch more than cause-based thresholds.
- The alert manager groups related alerts (one page for 40 failing pods), applies inhibition (a region-down alert suppresses the per-service alerts it causes) and honors silences.

### Query performance and protection

- The frontend splits a long query into day-aligned pieces, runs them in parallel and caches results per piece; 2,000 people watching the same dashboards mostly hit the cache.
- Per-query limits (series touched, samples decoded, time range) and per-tenant concurrency stop one expensive query from starving everyone.

## Failure modes

| Failure | Effect | Mitigation |
|---------|--------|------------|
| Ingestion overload | Samples delayed or rejected | Agents buffer to disk for hours and retry with backoff; the gateway sheds low-priority tenants or metric classes first and returns 429 |
| Ingester crash | Head data on that node lost | Write-ahead log replay, or replay from the durable log; two other replicas keep serving |
| Object storage slow | Historical queries slow | Alerting and recent dashboards unaffected (served by ingesters) |
| One tenant's cardinality explosion | Memory pressure for all | Per-tenant series limits enforced before data reaches ingesters |
| Region outage | Monitoring of that region | Run the alerting path per region and cross-monitor regions; the dead man's switch pages through an external service if the platform itself goes quiet |
| Agent clock skew | Samples in the wrong place | Reject samples outside a window around server time, count rejections per agent |
| Evaluator crash | Missed evaluations | The replica keeps evaluating; checkpointed state restores on restart |

## Trade-offs

- **Push versus pull**: push suits short-lived jobs and crossing network boundaries; pull gives automatic up/down detection and central control of scrape rates. Agents that scrape locally and push centrally get some of both.
- **Durable log in the write path**: replay and decoupling at the cost of another system, more latency and cost; the alternative is replicating writes directly to ingesters.
- **Exactness versus cost**: approximate percentiles (histograms, sketches) and rollups are cheaper and accurate enough for operations.
- **Consistency**: queries are eventually consistent across replicas; deduplicating replica results at query time is cheaper than coordinating writes.
- **Retention versus cost**: as computed above, resolution of the middle tier dominates storage cost.

## Observability and cost

- Meta-metrics: samples ingested and rejected (by reason and tenant), active series per tenant, ingestion-to-queryable lag, query latency by range, rule evaluation duration and missed evaluations, notification delivery latency and failures, agent buffer depth.
- Cost: ingester RAM (about 1.2 TB for the head) and the rollup tiers dominate; object storage is cheap per terabyte. Charge teams back by active series; it is the number that drives cost and the one they control.

## Evolution

- Exemplars linking metric samples to traces, and correlation with logs.
- Native or sparse histograms with automatic bucket boundaries.
- A global query view across regions.
- SLO management built on the same rules engine.
