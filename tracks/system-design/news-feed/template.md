# News Feed: Notes

## Requirements

<!-- Read/write ratio, freshness targets, ranking, pagination guarantees, filters, what is out of scope. -->

## Estimates

<!-- Posts/s, feed loads/s, fan-out inserts/s, feed cache size, post storage, the celebrity worst case. -->

## API

<!-- Publish, feed with cursor, follow, delete. -->

## Data model

<!-- Posts and ids, author timelines, follow graph, feed cache, session snapshots, counters. -->

## High-level design

<!-- Write path with fan-out; read path with candidates, ranking and hydration. -->

## Deep dives

<!-- Push, pull or hybrid; hot keys; ranking and stable pagination; cache tiers; deletes and unfollows. -->

## Failure modes

<!-- Fan-out backlog, ranking down, cache shard lost, partial hydration failure. -->

## Trade-offs

<!-- Write amplification versus read latency, memory versus compute, consistency model. -->

## Observability and cost

<!-- Lag and latency metrics, quality signals, dominant costs. -->

## Evolution

<!-- Recommendations, ads, multi-region, edits. -->
