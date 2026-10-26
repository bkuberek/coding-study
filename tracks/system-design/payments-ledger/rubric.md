# Payments Ledger: Rubric

## Requirements and scope

- [ ] States that correctness beats availability and that the ledger is a CP system that may refuse writes.
- [ ] Separates recording money (the ledger) from moving it (payment services calling processors).
- [ ] Defines exactly-once as an effect achieved by idempotency, not as a delivery guarantee.
- [ ] Distinguishes business time from recorded time.

## Estimates

- [ ] Derives payments and ledger lines per second, average and peak.
- [ ] Sizes 7 years of storage.
- [ ] Shows that peak updates on a hot account exceed what one locked row sustains.
- [ ] Concludes throughput fits one strongly consistent database today and plans for growth.

## API and data model

- [ ] Posts balanced entries with multiple lines, an idempotency key derived from the business event, actor and reason.
- [ ] Returns the original result for a replayed key and rejects a reused key with a different payload.
- [ ] Uses integer minor units with a currency on every line.
- [ ] Keeps entries and lines insert-only and balances derived.
- [ ] Models pending, available and held funds as separate accounts moved by entries.

## High-level design

- [ ] Writes entry, lines, protected balances and an outbox row in one transaction on a synchronously replicated database.
- [ ] Publishes entries downstream through a transactional outbox, not a dual write.
- [ ] Includes settlement ingestion, matching and a breaks workflow.

## Deep dives

- [ ] Walks through a concrete charge, fee, settlement and payout in debits and credits.
- [ ] Corrects mistakes with reversing entries, never updates.
- [ ] Prevents overdrafts with a conditional update or row lock inside the posting transaction.
- [ ] Avoids deadlocks with a consistent lock order.
- [ ] Handles hot accounts with asynchronous balances or sub-accounts.
- [ ] Describes a sharding path (distributed SQL or per-shard clearing accounts with a saga).
- [ ] Designs reconciliation with timing windows, break types and approved adjustments.
- [ ] Supports point-in-time balances with snapshots and period close.

## Failure modes and trade-offs

- [ ] Shows a timeout plus retry cannot double post.
- [ ] Covers primary failover with zero data loss.
- [ ] Covers a crash between the processor call and the ledger post, and how reconciliation catches it.
- [ ] Discusses synchronous versus asynchronous balances and build versus buy.

## Operations and evolution

- [ ] Monitors invariants (balanced entries, trial balance, balance drift) as alerts that must stay at zero.
- [ ] Tracks reconciliation breaks by age and amount.
- [ ] Mentions tamper evidence or write-once exports for audits.
- [ ] Describes currency conversion or multiple legal entities as extensions.
