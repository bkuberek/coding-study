# Ride Hailing: Reference

## Requirements

Clarify before designing:

- **Two very different kinds of data.** Driver locations are high volume, short lived and loss tolerant (a new one arrives in 4 seconds). Trip state is low volume and must be correct (no double assignment, no lost request, the confirmed price). Use different consistency models for each and say so.
- **Geography shards the problem.** Matching is local to a city; almost nothing needs a global view. That gives natural partitioning and failure isolation.
- **Matching objective**: nearest driver by ETA for each request (greedy), or best overall assignment across requests (batched). Ask which the business wants; both are valid.
- **Price lock**: the quote shown is binding for a short time, so pricing must be signed or stored, not recomputed at the end.
- **Out of scope**: payments internals, routing and ETA computation, pooled rides, scheduled rides, fraud.

## Estimates

| Quantity | Calculation | Result |
|----------|-------------|--------|
| Location updates | 2 M drivers / 4 s | 500,000/s globally, ~25,000/s in the largest city; ~50 MB/s at ~100 B each |
| Geo index size | 2 M drivers x ~100 B | ~200 MB globally: tiny; partition for locality and isolation, not size |
| Trips | 20 M/day | ~230/s average; 1,000 requests/s at peak, 50/s in the largest city |
| Quotes | 10 per request | ~10,000/s at peak |
| ETA calls for matching | ~10-20 candidates per request | ~10,000-20,000/s at peak |
| Raw location history | 500,000/s x 100 B x 86,400 | ~4.3 TB/day; keep in cheap storage briefly |
| Trip traces kept long term | 20 M trips x 300 points (20 min at one per 4 s) x 100 B | ~600 GB/day (fare disputes, safety, ETA training) |

Location ingestion is the volume problem; correctness of dispatch and trip state is the hard problem.

## API

```text
driver app <-> gateway (persistent connection)
  up:   location {driver_id, lat, lng, heading, speed, accuracy, device_ts, seq}
  up:   status {available | offline}
  down: offer {offer_id, trip_id, pickup, rider_rating, expires_at}
  up:   offer_response {offer_id, accept | decline}

rider app
  POST /v1/quotes {pickup, destination, product}
    200 {quote_id, price, surge_multiplier, pickup_eta, expires_at, signature}
  POST /v1/trips {quote_id, signature}          Idempotency-Key: <uuid>
    201 {trip_id, state: "requested"}
  GET  /v1/trips/{id}  + subscription for state changes and driver location
  POST /v1/trips/{id}/cancel {expected_version}

driver trip actions
  POST /v1/trips/{id}/arrived | start | complete {expected_version, location}
```

Every state-changing call carries the version the client last saw; a stale version gets 409 and the current state.

## Data model

| Data | Store | Key | Fields |
|------|-------|-----|--------|
| Live driver locations | in-memory geo index, sharded by city | `driver_id`; cell -> set of drivers | lat, lng, cell, status, updated_at, seq; expires after 30 s without updates |
| Driver dispatch state | owned by the city's dispatch shard | `driver_id` | `available`, `offered(trip_id, expires_at)`, `on_trip(trip_id)`, version |
| Trips | strongly consistent database, partitioned by city | `trip_id` | rider, driver, state, version, pickup, destination, quote, timestamps |
| Trip events | append-only, same transaction as the trip update | `(trip_id, seq)` | from state, to state, actor, ts |
| Outbox | same transaction | `id` | event for payments, notifications, analytics |
| Quotes | signed token (no storage), or a short-TTL store | `quote_id` | price, surge, route summary, expiry |
| Surge | in-memory per city, refreshed every 1-2 min | `cell_id` | multiplier, computed_at |
| Location stream | event log, partitioned by city | `driver_id` | every update, for tracking, surge, ETAs and history |

## High-level design

```text
driver app --> gateway --> location service --> city geo index (latest only, in memory)
                                            --> location stream --> trip tracking --> rider app
                                                                --> surge job (supply per cell)
                                                                --> history (object storage)
rider app --> API --> quote service (route estimate from maps + surge for the pickup cell) --> signed quote
          --> trip service: create trip "requested" (durable) --> dispatch queue (per city)
dispatch shard (one owner per city, standby replica):
     candidates = available drivers in nearby cells --> rank by ETA (maps)
     reserve driver (available -> offered) --> send offer --> wait up to 10 s
     accept --> trip service: requested -> driver_assigned (conditional) --> notify rider
     decline / timeout --> release driver, next candidate
trip service --> trip events + outbox --> payments (on completion), notifications, analytics
```

## Deep dives

### Location ingestion and the geo index

- Index drivers by cell on a hexagonal grid (H3 at a resolution around 0.7 km² per cell) or by geohash. Hexagons have uniform neighbor distances, so a k-ring of cells approximates a radius well; geohash cells vary in shape and need neighbor handling at cell edges. Quadtrees adapt to density but need rebalancing as drivers move continuously.
- Most updates leave a driver in the same cell, so an update is usually an overwrite of the driver's record; only a cell change moves the driver between two sets.
- Keep only the latest location in memory, not durably: if a node dies, the index rebuilds itself from the next 4 seconds of updates. Durable history goes to the location stream instead.
- Drop out-of-order updates using the device sequence number, and filter GPS noise (map matching, accuracy thresholds) before it reaches matching.
- Partition by city; drivers and riders near a city boundary query the neighboring shard for cells near the edge.

### Dispatch without double assignment

- One dispatch shard owns each city's driver dispatch state: a single writer, so reserving a driver is an in-memory compare-and-set (`available -> offered(trip)`), not a distributed lock. A standby replicates the state and takes over with a fencing token if the owner fails.
- The offer expires after 10 seconds; the reservation is released on decline, timeout or expiry, so a driver is never stuck as offered.
- Accept is a conditional transition: the trip moves `requested -> driver_assigned` only if the trip is still requested and the driver still holds this offer. A rider cancelling at the same moment races on the same conditional write; whichever commits first wins and the other gets a conflict.
- A confirmed request is never dropped: the trip is persisted before matching starts, and a sweeper re-queues trips that stay `requested` longer than a few seconds without an active offer (for example after a dispatch failover).
- Greedy versus batched matching: greedy offers each request the best driver now and is simplest; batching requests for 1-2 seconds and solving an assignment problem lowers total pickup time across the city at the cost of a little latency. Start greedy, add batching for dense cities.

### Trip state machine

```text
requested --> driver_assigned --> driver_arrived --> in_progress --> completed
    |               |                   |
    +-- cancelled <-+-------------------+   (by rider or driver, with cancellation rules)
```

- Every transition is a conditional update on `(state, version)` plus a trip event and an outbox row in one transaction. Downstream systems (payments, notifications, receipts) consume the outbox, so a completed trip always produces exactly one charge request, deduplicated by trip id.
- Timeouts (driver never arrives, rider no-show) are durable timers that fire transitions, not in-memory sleeps.
- Trip state lives in a strongly consistent store partitioned by city; at 1,000 requests/s globally this is easy for a modest cluster per region.

### Surge pricing

- Every 1-2 minutes per cell, compare demand (requests and quotes) with supply (available drivers) over a sliding window and map the ratio to a multiplier.
- Smooth in time (exponential moving average) and space (blend with neighboring cells) so prices do not jump between adjacent streets or minutes; apply caps where regulation requires them.
- The quote carries a signature over price, surge, route and expiry, so trip creation can trust it without recomputing; the rider pays what they saw if they confirm before expiry.
- The surge job is asynchronous: if it lags, quotes use the last multiplier, never block.

### Consistency by data type

| Data | Model | Why |
|------|-------|-----|
| Driver locations | Eventually consistent, latest wins by sequence | Loss tolerant, replaced every 4 seconds |
| Driver dispatch state | Single writer per city | Prevents double assignment without distributed locks |
| Trips | Strongly consistent, conditional writes | Money and safety depend on it |
| Surge | Eventually consistent, minutes stale is fine | Advisory input to quotes |

## Failure modes

| Failure | Effect | Mitigation |
|---------|--------|------------|
| Dispatch shard owner fails | Matching stops in one city | Standby takes over with a fencing token; the sweeper re-queues waiting trips |
| Geo index node lost | Drivers invisible briefly | Rebuilt from updates within seconds |
| Driver app loses connectivity mid-trip | No live location | Trip continues; the app buffers locations and events and syncs on reconnect; the fare uses the trace |
| Regional incident | API unreachable for some users | Apps keep trip state locally; drivers can complete trips offline and the trip service reconciles later; cities fail over to another region |
| Maps or ETA service slow | Matching latency | Fall back to straight-line distance with a speed factor for ranking |
| Demand spike (stadium empties) | Too few drivers | Surge pricing, queueing requests at the venue, offering farther drivers |
| Payment fails at completion | Charge pending | Asynchronous retries keyed by trip id; never blocks completing the trip |

## Trade-offs

- **Greedy versus batched matching**: latency and simplicity versus city-wide efficiency.
- **Hexagonal grid versus geohash versus quadtree**: uniform neighbors versus simple string prefixes versus adaptive density.
- **In-memory versus durable locations**: speed and cost versus durability the data does not need.
- **City shards versus global services**: locality and isolation versus handling cross-city trips (airports between cities), which need explicit boundary handling.
- **Strong consistency only where it matters**: trips and dispatch state are consistent; everything else is eventually consistent and cheap.

## Observability and cost

- Request-to-offer and request-to-assignment latency, offer acceptance rate, unfulfilled request rate per city, location freshness (age of the newest update per driver, p99), double-assignment detector (must stay at zero), trip transition conflicts, sweeper re-queues, surge distribution per city, ETA error (predicted versus actual pickup).
- Cost: gateways and location ingestion (500,000 updates/s), the location stream and history storage, and ETA computation for matching. Sample location history after a retention period and keep full traces only for trips.

## Evolution

- Pooled rides: matching becomes a routing problem with detour constraints.
- Scheduled rides and reservations: dispatch ahead of time with commitments.
- Deliveries on the same dispatch platform with different matching rules.
- Learned ETAs and demand forecasting to move drivers before spikes.
