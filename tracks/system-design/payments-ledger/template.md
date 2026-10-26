# Payments Ledger: Notes

## Requirements

<!-- CP or AP, what the ledger does and does not do, exactly-once semantics, the two clocks, out of scope. -->

## Estimates

<!-- Payments and lines per second, storage for 7 years, hot account update rate versus a row lock. -->

## API

<!-- Posting entries, idempotency behavior, balances and history, holds; money representation. -->

## Data model

<!-- Accounts, entries, lines, balances, snapshots, outbox, settlement records; how states become accounts. -->

## High-level design

<!-- Posting transaction, outbox, reconciliation, period close. -->

## Deep dives

<!-- Double entry with a worked example; idempotency; overdrafts and hot accounts; sharding; reconciliation; audit and time. -->

## Failure modes

<!-- Retries after commit, failover, partial failures across services, bad deploys, duplicate files, rounding. -->

## Trade-offs

<!-- Consistency versus availability, synchronous versus asynchronous balances, one database versus shards, build versus buy. -->

## Observability and cost

<!-- Invariant monitors, latency and conflict metrics, reconciliation breaks; cost. -->

## Evolution

<!-- Currency conversion, legal entities, real-time payouts, sharding. -->
