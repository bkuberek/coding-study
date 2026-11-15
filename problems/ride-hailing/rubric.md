# Ride Hailing: Rubric

## Requirements and scope

- [ ] Separates loss-tolerant location data from correctness-critical trip and dispatch state.
- [ ] Uses geography (city) as the partitioning and isolation boundary.
- [ ] Asks whether matching optimizes per request or across requests.
- [ ] Treats the confirmed price as binding (price lock).
- [ ] Names what is out of scope (payments internals, routing, pooling, fraud).

## Estimates

- [ ] Derives 500,000 location updates/s globally and the largest city's share.
- [ ] Shows the geo index is small and partitioned for locality, not size.
- [ ] Estimates requests, quotes and ETA calls per second at peak.
- [ ] Sizes location history versus trip traces and decides what to keep.

## API and data model

- [ ] Uses persistent connections for driver locations and offers.
- [ ] Defines quote, create trip (idempotent) and trip actions with expected versions.
- [ ] Models live locations in an in-memory geo index with expiry for stale drivers.
- [ ] Models trips with state, version, events and an outbox.
- [ ] Makes quotes verifiable (signed token or stored with expiry).

## High-level design

- [ ] Shows location ingestion feeding both the geo index and a location stream.
- [ ] Persists the trip before matching starts.
- [ ] Shows the dispatch loop: candidates, ETA ranking, reservation, offer, timeout, next candidate.
- [ ] Sends completion to payments through an outbox, deduplicated by trip id.

## Deep dives

- [ ] Compares a hexagonal grid, geohash and quadtree for the geo index.
- [ ] Keeps only latest locations in memory and explains why rebuilding from updates is enough.
- [ ] Prevents double assignment with a single writer per city or a conditional write, with fencing on failover.
- [ ] Resolves the cancel-versus-accept race with a conditional transition.
- [ ] Guarantees no request is lost (durable trip plus a sweeper).
- [ ] Draws the trip state machine with timeouts as durable timers.
- [ ] Computes surge per cell with smoothing in time and space and caps.
- [ ] Discusses greedy versus batched matching.

## Failure modes and trade-offs

- [ ] Covers dispatch shard failover, geo index loss and maps service slowness.
- [ ] Lets trips in progress complete during connectivity loss or a regional incident.
- [ ] Handles sudden local demand spikes.
- [ ] States the consistency model per data type.

## Operations and evolution

- [ ] Names key metrics: request-to-assignment latency, acceptance rate, unfulfilled requests, location freshness, double assignments.
- [ ] Identifies location ingestion and ETA computation as cost drivers.
- [ ] Explains what pooled rides or deliveries would change.
