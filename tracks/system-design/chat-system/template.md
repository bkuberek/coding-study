# Chat System: Notes

## Requirements

<!-- Ordering scope, delivery semantics, what "sent" promises, history model, out of scope. -->

## Estimates

<!-- Messages/s, deliveries/s with groups and devices, storage per day and year, gateway count. -->

## API

<!-- Real-time frames in both directions; sync and history endpoints. -->

## Data model

<!-- Messages and partitioning, dedup, receipts, sync index, session registry. -->

## High-level design

<!-- Gateways, chat service, session registry, push, receipts; the send flow step by step. -->

## Deep dives

<!-- Ordering and idempotency; gateways and reconnect storms; receipts; offline sync; group fan-out. -->

## Failure modes

<!-- Lost acks, crashes mid-flow, gateway or region loss, split brain. -->

## Trade-offs

<!-- History versus store-and-forward, storage layout, single writer, push versus pull, consistency. -->

## Observability and cost

<!-- Latency and reliability metrics; storage cost and how to reduce it. -->

## Evolution

<!-- End-to-end encryption, presence, edits, search, broadcast channels. -->
