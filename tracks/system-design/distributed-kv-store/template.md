# Distributed Key-Value Store: Notes

## Requirements

<!-- CAP position, what each consistency level promises, conflict semantics per table, out of scope. -->

## Estimates

<!-- Raw storage, node count, replica operations per node, write bandwidth, cross-zone traffic, hot keys. -->

## API

<!-- get, put, delete, cas; consistency levels; version context; client routing. -->

## Data model

<!-- Record and version, tables, ring and placement, hints, on-disk layout. -->

## High-level design

<!-- Coordinator, preference list, write and read paths, gossip, repair, control plane. -->

## Deep dives

<!-- Partitioning and placement; quorums; conflict resolution; membership and repair; storage engine; CAS. -->

## Failure modes

<!-- Node, zone, slow node, partition, clock skew, compaction, tombstones. -->

## Trade-offs

<!-- Leaderless versus consensus, LWW versus version vectors, vnodes versus fixed partitions. -->

## Observability and cost

<!-- Metrics per node and table; disk, nodes and transfer costs. -->

## Evolution

<!-- Multi-region, change data capture, strongly consistent mode, tiered storage. -->
