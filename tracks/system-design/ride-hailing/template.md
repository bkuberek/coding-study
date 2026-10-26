# Ride Hailing: Notes

## Requirements

<!-- Location data versus trip state, city partitioning, matching objective, price lock, out of scope. -->

## Estimates

<!-- Location updates/s, geo index size, requests and quotes at peak, ETA calls, history storage. -->

## API

<!-- Driver connection frames, quotes, trip creation and actions with versions. -->

## Data model

<!-- Geo index, dispatch state, trips and events, quotes, surge, location stream. -->

## High-level design

<!-- Location ingestion, quoting, trip creation, the dispatch loop, downstream events. -->

## Deep dives

<!-- Geo index; dispatch without double assignment; trip state machine; surge; consistency by data type. -->

## Failure modes

<!-- Dispatch failover, index loss, connectivity loss, regional incident, slow maps, demand spikes, payment failure. -->

## Trade-offs

<!-- Greedy versus batched, grid choice, in-memory versus durable, city shards, where to be consistent. -->

## Observability and cost

<!-- Matching and freshness metrics, the zero-tolerance detectors, cost drivers. -->

## Evolution

<!-- Pooled rides, scheduled rides, deliveries, forecasting. -->
