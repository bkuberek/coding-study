# Distributed Key-Value Store: Rubric

## Requirements and scope

- [ ] States the CAP position (available and partition tolerant by default) from the "always writable" requirement.
- [ ] Says precisely what `QUORUM` guarantees (overlapping quorums, read-your-writes) and that it is not linearizable.
- [ ] Makes the conflict mode a per-table property and explains why mixing modes on a key is unsafe.
- [ ] Names what is out of scope (range scans, secondary indexes, transactions, multi-region).

## Estimates

- [ ] Sizes raw storage with replication and compaction headroom, and derives a node count.
- [ ] Converts client operations into replica operations per node.
- [ ] Estimates write bandwidth and notes compaction write amplification on disk.
- [ ] Notices cross-zone replication traffic as a cost.
- [ ] Shows a hot key cannot be solved by adding nodes.

## API and data model

- [ ] Defines get, put, delete with per-request consistency, and a separate compare-and-set.
- [ ] Carries a version context so writes declare which versions they supersede.
- [ ] Uses a token-aware client or explains the coordinator role.
- [ ] Describes the on-disk layout (commit log, memtable, SSTables, bloom filters).

## High-level design

- [ ] Uses consistent hashing with replicas on distinct zones.
- [ ] Describes the write path (send to N, ack after W, hints) and the read path (data plus digest reads, read repair).
- [ ] Separates gossip-based failure detection from explicit ring changes.

## Deep dives

- [ ] Explains virtual nodes (or fixed partitions) and how capacity is added without downtime.
- [ ] Explains why zone-aware placement keeps strict quorums available through a zone outage.
- [ ] Contrasts strict and sloppy quorums and what hinted handoff does to the overlap guarantee.
- [ ] Compares last-writer-wins, version vectors with siblings, and CRDTs, with a use for each.
- [ ] Explains tombstones and why the grace period must exceed the repair cycle.
- [ ] Describes anti-entropy with Merkle trees and read repair.
- [ ] Implements compare-and-set with consensus (Paxos or Raft) and states its latency cost.
- [ ] Chooses compaction strategies by workload.

## Failure modes and trade-offs

- [ ] Covers node loss, zone loss, slow nodes (speculative reads) and partitions between zones.
- [ ] Explains how clock skew breaks last-writer-wins and mitigates it (hybrid logical clocks).
- [ ] Compares leaderless replication with consensus per range (availability and latency versus linearizability).

## Operations and evolution

- [ ] Names the key metrics: pending hints, repair progress, compaction backlog, SSTables per read, tombstones per read, per-node latency.
- [ ] Identifies disk, node count and cross-zone transfer as the cost drivers and the levers that reduce them.
- [ ] Describes multi-region replication with local quorums as the next step.
