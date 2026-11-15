# Metrics and Monitoring: Notes

## Requirements

<!-- What scales (series or samples), the critical path, push or pull, retention, out of scope. -->

## Estimates

<!-- Samples/s, size per tier, ingester memory, alert and dashboard query rates. Challenge the retention policy? -->

## API

<!-- Write, query, metadata, rules, silences, usage. -->

## Data model

<!-- Series identity, inverted index, chunks and compression, blocks, rollups, alert state. -->

## High-level design

<!-- Agents, gateway, ingesters, object storage, compactor, query path, rules and alert manager, meta-monitoring. -->

## Deep dives

<!-- Cardinality and tenancy; storage; downsampling and percentiles; alert evaluation; query protection. -->

## Failure modes

<!-- Overload, ingester loss, storage slowness, cardinality explosion, region outage, clock skew. -->

## Trade-offs

<!-- Push versus pull, durable log, exactness versus cost, retention versus cost. -->

## Observability and cost

<!-- Meta-metrics; cost drivers and chargeback. -->

## Evolution

<!-- Exemplars and traces, native histograms, global view, SLOs. -->
