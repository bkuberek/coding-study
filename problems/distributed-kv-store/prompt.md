# Distributed Key-Value Store

## Question

Design a distributed key-value store that internal teams use as a building block: session data, shopping carts, feature flags per user, idempotency records. It runs in one region across three availability zones. Design the store itself, not an application on top of a managed one.

## Functional requirements

- `put(key, value)`, `get(key)` and `delete(key)`. Keys are up to 256 bytes; values up to 1 MB, most under 10 KB.
- Consistency is chosen per request: `ONE`, `QUORUM` or `ALL`.
- Optional time to live per key.
- A conditional put (compare-and-set on a version) for the few callers that need it, such as idempotency records.
- Concurrent writes to the same key must never be silently lost for callers that ask to see conflicts (carts); other callers accept last-writer-wins.

## Non-functional requirements

- p99 latency within the region: under 10 ms for reads and under 20 ms for writes at `QUORUM`.
- Always writable: writes succeed during the loss of any single node, and of a whole availability zone.
- Durability: a write acknowledged at `QUORUM` survives the loss of any single node.
- Add or remove capacity without downtime; machines may differ in size.
- Operable by a small team: failures and repairs are automatic in the common case.

## Scale

- 100 TB of data before replication; 10 billion keys.
- 2 million operations per second at peak, 70% reads.
- Some keys are hot: a popular feature flag can take 100,000 reads per second.
