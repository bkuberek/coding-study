# Distributed Key-Value Store: Reference

## Requirements

Clarify before designing:

- **CAP position**: "always writable, even during a zone loss" makes this an AP store in the Dynamo tradition: leaderless replication, quorums, conflict resolution. Strong guarantees (compare-and-set) become an explicit, slower path rather than the default.
- **What `QUORUM` promises**: read-your-writes when the read and write quorums overlap, not linearizability. Say this precisely; interviewers probe it.
- **Conflict semantics per table**: last-writer-wins for most data, conflicts surfaced to the caller (siblings or CRDTs) for carts. Mixing both on one key is unsafe, so the mode belongs to the table.
- **Operational requirements are design requirements**: automatic failure handling, online rebalancing, heterogeneous machines.
- **Out of scope**: secondary indexes, range scans, multi-key transactions, multi-region replication (mention as evolution).

## Estimates

| Quantity | Calculation | Result |
|----------|-------------|--------|
| Raw data | 100 TB x replication factor 3 | 300 TB |
| Nodes | 4 TB usable per node at ~50% fill (compaction needs headroom) | ~150 nodes, 50 per zone |
| Client ops | 2 M/s: 1.4 M reads, 0.6 M writes | |
| Replica ops | reads x 2 (one data read, one digest) + writes x 3 | ~4.6 M/s, ~31,000 per node |
| Write bandwidth | 0.6 M/s x ~2 KB written on average (small session and flag updates dominate) x 3 replicas | ~3.6 GB/s cluster, ~24 MB/s per node, ~10x that on disk after compaction |
| Cross-zone traffic | 2 of every 3 replica writes cross a zone | ~200 TB/day, a billed line item in most clouds |
| Bloom filters | 10 B keys x 3 / 150 nodes x 10 bits | ~250 MB per node |
| Hot key | 100,000 reads/s over 3 replicas | ~33,000/s on each of 3 nodes: needs caching, not just more nodes |

## API

```text
get(key, consistency=QUORUM)          -> [(value, context)]   one entry normally, several siblings in conflict mode
put(key, value, context?, consistency=QUORUM, ttl?)
delete(key, context?, consistency=QUORUM)                     writes a tombstone
cas(key, expected_version, value)     -> {applied: bool, current_version}   consensus path
```

- `context` carries the version (a version vector in conflict mode) read earlier; writing it back tells the store which versions this write supersedes.
- A token-aware client library hashes the key, knows the ring and sends the request straight to a replica, saving a hop.

## Data model

| Concept | Shape |
|---------|-------|
| Record | `key -> (value, version, ttl, tombstone)`; version is a hybrid logical clock timestamp (LWW tables) or a version vector (conflict tables) |
| Table | name, conflict mode (`lww`, `siblings`, `crdt`), replication factor, default consistency, compaction strategy |
| Ring | token ranges -> nodes, with virtual nodes; replica placement one per zone |
| Hints | `(target_node, key, mutation)` stored on the coordinator while a replica is down, bounded to a few hours |
| On-disk (per node) | commit log -> memtable -> immutable sorted string tables (SSTables) with bloom filters and a sparse index |

## High-level design

```text
client library (token aware)
   --> coordinator (any node; normally a replica of the key)
         --> preference list: N = 3 replicas, one per zone, from the ring
         --> write: send to all 3, ack after W; hint for any unreachable replica
         --> read:  data read from the fastest replica + digest reads; on mismatch resolve and read-repair
every node: storage engine (LSM), gossip membership, failure detector,
            hinted handoff replay, scheduled anti-entropy repair (Merkle trees)
control plane: ring changes (add, remove, replace node), placement, configuration
```

- Leaderless: every replica accepts writes for its ranges. There is no failover step, which is what keeps the store writable through failures.
- Gossip spreads membership and node state; the ring itself changes only through explicit operations, so a flapping node never triggers data movement.

## Deep dives

### Partitioning and placement

- Consistent hashing with virtual nodes: each physical node owns many small token ranges, so adding a node takes a little from every other node and load spreads evenly. Bigger machines get more vnodes.
- Fixed partitions are the alternative: split the hash space into, say, 16,384 partitions once and move whole partitions between nodes. Rebalancing and repair become per-partition operations, which is easier to operate; the partition count must be chosen up front.
- Place the three replicas of every range in three different zones. Then any failures confined to one zone, including a whole-zone outage, leave two replicas of every range and `QUORUM` keeps working.
- A single hot key cannot be split by partitioning. Cache it: a client-side or coordinator cache with a short TTL turns 100,000 reads/s into a few hundred per second on the replicas, at the cost of staleness, which flags tolerate.

### Replication and quorums

- With N = 3, W = 2 and R = 2, every read quorum overlaps every write quorum, so a `QUORUM` read sees the latest `QUORUM` write that completed before it.
- That is not linearizability: a write that reached only one replica and then "failed" may be seen by one read and not by the next. Blocking read repair narrows this; full linearizability needs consensus.
- `ONE` is faster and more available but can read stale data and acknowledges writes held by a single replica.
- Sloppy quorums (writing to a substitute node outside the preference list) add availability beyond what zone-aware strict quorums give, but they break the overlap guarantee. With zone-aware placement, strict quorums already survive a zone loss, so keep quorums strict by default.
- Durability: each replica appends to its commit log and fsyncs in groups every few milliseconds. A `QUORUM` write lives on two machines in two zones, so losing any single node loses nothing.

### Conflict resolution

| Mode | Mechanism | Cost | For |
|------|-----------|------|-----|
| Last-writer-wins | Highest hybrid logical clock timestamp wins | Concurrent writes silently lose one; clock skew can drop a later write | Sessions, flags, caches |
| Siblings | Version vectors detect concurrency; reads return all concurrent versions; the client merges and writes back with the context | Application merge logic, sibling growth if clients do not merge | Carts |
| CRDTs | Counters, sets and maps that merge deterministically | Limited data types, metadata overhead | Counters, carts as observed-remove sets |

- Deletes are tombstones. They must reach every replica before being purged, or a replica that missed the delete resurrects the value during repair. Purge tombstones only after a grace period longer than the maximum time between full repairs (for example 10 days).

### Membership, failure detection and repair

- Gossip: every second each node exchanges state with a few random peers; information reaches all 150 nodes in a handful of rounds.
- A phi-accrual failure detector marks a node down for routing based on heartbeat arrival statistics, adapting to network jitter instead of using a fixed timeout.
- Temporary failures: coordinators store hints and replay them when the node returns (hinted handoff), bounded to a few hours to cap hint storage.
- Permanent failures: an operator or automation replaces the node, and the replacement streams its ranges from the surviving replicas.
- Anti-entropy: replicas build Merkle trees over each token range and compare them; only differing subranges are streamed. Run a full repair cycle within the tombstone grace period.
- Read repair fixes divergence on keys that are read, cheaply, as a side effect.

### Storage engine

- Log-structured merge tree: sequential writes to the commit log and memtable, flushed to immutable SSTables, merged by compaction. Writes are cheap; reads may touch several SSTables, and bloom filters skip most of them.
- Compaction strategy per table: size-tiered for write-heavy data (low write amplification, more space and read amplification), leveled for read-heavy data (fewer SSTables per read, more rewriting), time-window for TTL data (whole files expire and are dropped).
- Large values (up to 1 MB) inflate compaction cost; store them in separate value logs, or cap them and point to object storage.

### Compare-and-set

- A conditional write must agree with concurrent conditional writes, which leaderless quorums cannot guarantee. Run a Paxos round per key among the replicas (prepare, read, propose, commit): about four round trips, so several times the latency of a normal write.
- Restrict CAS to tables that use it exclusively; a plain LWW write racing a CAS on the same key would break the CAS guarantee.

## Failure modes

| Failure | Effect | Mitigation |
|---------|--------|------------|
| One node down | Its ranges have 2 of 3 replicas | Quorums continue; hints, then repair |
| Whole zone down | Every range has 2 of 3 replicas | Zone-aware placement keeps `QUORUM` working; hint storage and repair afterwards |
| Slow node (bad disk, garbage collection) | p99 spikes | Coordinators route data reads to the fastest replicas and send a speculative read when a replica exceeds its usual p99 |
| Network partition between zones | Minority side cannot reach quorum | Callers on that side can drop to `ONE` explicitly; divergence repaired later |
| Clock skew with LWW | A later write loses | Hybrid logical clocks, alert on skew, siblings for data that cannot tolerate it |
| Compaction falling behind | Read latency and disk usage grow | Throttle and prioritize compaction, alert on SSTables per read, keep disk headroom |
| Tombstones purged before repair | Deleted data reappears | Grace period longer than the repair cycle, alert on repair lag |

## Trade-offs

- **AP leaderless versus CP consensus per range** (Raft groups per range, as in stores built for strong consistency): leaderless gives write availability and no failover pause; Raft gives linearizability, simpler reasoning and CAS on every write, at the cost of leader-based latency and unavailability during elections.
- **Last-writer-wins versus version vectors**: simplicity versus never losing a concurrent update.
- **Virtual nodes versus fixed partitions**: smoother automatic balance versus simpler operations.
- **Tunable consistency**: the caller trades latency and availability against freshness per request; the default must be safe (`QUORUM`).

## Observability and cost

- Per node and per table: read and write p99 (coordinator and replica), pending hints, dropped mutations, repair progress and Merkle mismatch rate, compaction backlog, SSTables touched per read, tombstones scanned per read, disk usage and skew between nodes, gossip state flaps, clock skew.
- Cost: about 600 TB of provisioned disk for 100 TB of data (replication plus compaction headroom), 150 nodes, and cross-zone transfer for replication. The levers: replication factor per table, compression, TTLs, and value-size limits.

## Evolution

- Multi-region: asynchronous replication between regions with `LOCAL_QUORUM` per region; conflicts across regions resolved by the same per-table mode.
- Change data capture from commit logs for downstream consumers.
- A strongly consistent mode built on Raft per range for tables that need CAS everywhere.
- Tiered storage: cold SSTables moved to object storage.
