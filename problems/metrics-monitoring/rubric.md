# Metrics and Monitoring: Rubric

## Requirements and scope

- [ ] Identifies series cardinality, not sample rate, as the main scaling dimension.
- [ ] Treats the alerting path as the most critical one and minimizes its dependencies.
- [ ] Discusses push versus pull ingestion.
- [ ] Names what is out of scope (logs, traces, anomaly detection).

## Estimates

- [ ] Derives 20 M samples/s and the compressed size per sample.
- [ ] Sizes each retention tier separately.
- [ ] Notices the 1-minute tier dominates storage and proposes a cheaper policy to stakeholders.
- [ ] Sizes ingester memory from active series and replication.
- [ ] Estimates alert-evaluation and dashboard query rates.

## API and data model

- [ ] Defines batched write, range query, metadata, rules and silences endpoints, with 429 for tenants over limits.
- [ ] Identifies series by name plus sorted labels and uses an inverted index of label postings.
- [ ] Stores samples in compressed chunks (delta-of-delta timestamps, XOR values) and explains why compression works.
- [ ] Stores rollups as min, max, sum and count, and histograms as bucket counts.

## High-level design

- [ ] Shows agents, an ingestion gateway with limits, ingesters with a head block and WAL, object storage for blocks, a compactor and queriers.
- [ ] Includes a query frontend with splitting, caching and limits.
- [ ] Separates rule evaluators and an alert manager that groups, deduplicates, inhibits and silences.
- [ ] Adds meta-monitoring and a dead man's switch outside the platform.

## Deep dives

- [ ] Enforces per-tenant and per-metric series limits and gives teams a cardinality view.
- [ ] Addresses churn from short-lived containers.
- [ ] Explains why percentiles cannot be averaged across rollups and how histograms solve it.
- [ ] Chooses query resolution from range and step.
- [ ] Runs rule evaluation from recent data only, with replicas, checkpointed state and a `for` duration.
- [ ] Handles late data and absent data in alert rules.
- [ ] Prefers symptom-based, SLO burn-rate alerts.

## Failure modes and trade-offs

- [ ] Handles overload with agent buffering, prioritized shedding and backpressure.
- [ ] Covers ingester crash recovery (WAL or log replay) and object-storage slowness.
- [ ] Keeps alerting working during a regional outage (per-region alerting, cross-monitoring).
- [ ] Discusses the durable log in the write path and exactness versus cost.

## Operations and evolution

- [ ] Names meta-metrics: rejected samples by reason, active series per tenant, ingestion lag, missed evaluations, notification latency.
- [ ] Identifies ingester RAM and rollup tiers as cost drivers and proposes chargeback by active series.
- [ ] Mentions exemplars, trace correlation or native histograms as next steps.
