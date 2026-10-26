# Payments Ledger: Reference

## Requirements

Clarify before designing:

- **Correctness over availability**: when in doubt, refuse the write. This is a CP system, the opposite of most interview designs, and saying so early frames every later choice.
- **The ledger records, it does not move money**: calls to processors and banks belong to the payment services; the ledger never calls out. That keeps it deterministic and testable.
- **Exactly once is an effect, not a delivery guarantee**: callers will retry; idempotency keys make each business event land once.
- **Two clocks**: when something happened in business terms (`effective_at`) and when the ledger learned it (`recorded_at`). Month-end reports, late settlement files and corrections all need both.
- **Out of scope**: currency conversion, tax, invoicing, the payment services themselves.

## Estimates

| Quantity | Calculation | Result |
|----------|-------------|--------|
| Payments | 20 M/day | ~230/s average, ~1,200/s peak |
| Ledger lines | 4 per payment | 80 M/day, ~930/s average, ~4,600/s peak |
| Storage | ~400 B per line with entry header and indexes | ~32 GB/day, ~12 TB/year, ~85 TB for 7 years |
| Hot accounts | fee revenue takes a line per payment | ~1,200 updates/s at peak on one balance row |
| Single-row update ceiling | ~1-2 ms lock hold per transaction | ~500-1,000 updates/s per row |

Throughput is modest: one well-provisioned relational primary with synchronous replication handles 4,600 lines/s. The hard parts are hot accounts (the row-lock ceiling is below peak demand), correctness under retries and partial failures, and reconciliation.

## API

```text
POST /v1/entries                        Idempotency-Key: charge:ch_8Kq2:captured
  {"event_type": "charge_captured", "event_ref": "ch_8Kq2", "effective_at": "2026-03-14T10:02:11Z",
   "lines": [
     {"account": "processor_receivable:acme", "direction": "debit",  "amount": 10000, "currency": "USD"},
     {"account": "merchant_pending:m_123",    "direction": "credit", "amount": 9700,  "currency": "USD"},
     {"account": "fee_revenue",               "direction": "credit", "amount": 300,   "currency": "USD"}],
   "actor": "svc:charges", "reason": "card charge captured"}
  201 {"entry_id": "...", "recorded_at": "..."}
  200 same body, when the same key and the same payload are replayed
  409 {"error": "idempotency_key_reused"}   the key was used with a different payload
  422 {"error": "unbalanced"}              the lines do not balance per currency
  422 {"error": "insufficient_funds"}      a debit would overdraw an overdraft-protected account

GET /v1/accounts/{id}/balance?as_of=2026-02-28T23:59:59Z      posted, pending, held, available
GET /v1/accounts/{id}/lines?cursor=&from=&to=
POST /v1/holds {account, amount, currency, reason, expires_at}   -> an entry moving available to held
POST /v1/holds/{id}/release
```

Amounts are integers in the currency's minor unit (cents), never floating point; each currency declares its exponent (JPY has 0, KWD has 3).

## Data model

| Table | Key | Fields | Rules |
|-------|-----|--------|-------|
| `accounts` | `account_id` | owner, type (asset, liability, revenue, expense), currency, overdraft protected, status | |
| `entries` | `entry_id` | idempotency key (unique per client), request hash, event type and ref, `effective_at`, `recorded_at`, actor, reason, previous-entry hash | Insert only |
| `lines` | `(entry_id, line_no)` | account, direction, amount, currency | Insert only; per entry and currency, debits equal credits |
| `balances` | `(account_id, currency)` | posted, version | Derived; updated in the posting transaction only for overdraft-protected accounts |
| `balance_snapshots` | `(account_id, currency, period_end)` | balance | Written at period close; `as_of` reads start here |
| `outbox` | `id` | entry id, payload, published flag | Same transaction as the entry |
| `settlement_records` | `(source, file_id, record_no)` | external ref, amount, currency, settlement date, match status | Ingested idempotently by file hash |

Business states are separate accounts, not flags: a merchant has `merchant_pending`, `merchant_available` and `merchant_held`. Settling a charge or placing a hold is an entry that moves money between them, so every state change is itself balanced and auditable.

## High-level design

```text
charges / refunds / payouts / disputes services
   --> ledger API (stateless): validate, idempotency check, balance rules
         --> one database transaction:
               insert entry + lines, update protected balances (conditional), insert outbox row
         --> commit on a synchronously replicated primary (RPO 0)
   outbox relay --> event log "ledger.entry_recorded" --> balance read models, reporting,
                                                          warehouse, merchant notifications
processor and bank settlement files --> ingestion --> reconciliation matcher --> breaks queue --> ops
                                                                             --> adjustment entries (approved)
period close job --> snapshots, invariant checks, period lock
```

## Deep dives

### Double-entry model

A $100.00 card charge with a $3.00 platform fee, then settlement, then payout:

| Entry | Debit | Credit |
|-------|-------|--------|
| Charge captured | `processor_receivable` 100.00 | `merchant_pending:m_123` 97.00, `fee_revenue` 3.00 |
| Processor settles net of its $2.20 cost | `bank_cash` 97.80, `processing_cost` 2.20 | `processor_receivable` 100.00 |
| Funds become available | `merchant_pending:m_123` 97.00 | `merchant_available:m_123` 97.00 |
| Payout | `merchant_available:m_123` 97.00 | `bank_cash` 97.00 |

- Every entry sums to zero per currency, so money cannot appear or vanish: a bug produces an unbalanced entry, which the ledger rejects, instead of a silently wrong balance.
- Nothing is ever updated or deleted. A mistake is fixed by a reversing entry plus a correct one, which keeps the history of what the ledger believed and when.

### Idempotency and exactly-once effects

- The idempotency key is derived from the business event (`charge:ch_8Kq2:captured`), not generated per HTTP attempt, so every retry from any instance of the caller carries the same key.
- The key, a hash of the request and the resulting entry id are written in the same transaction as the entry. A replay with the same payload returns the original result; a different payload with the same key is a caller bug and gets 409.
- Downstream, the transactional outbox publishes each entry at least once; consumers deduplicate by entry id. At-least-once delivery plus idempotent processing on every hop is what "exactly-once effects" means in practice.

### Concurrency, overdrafts and hot accounts

- Overdraft-protected debits (payouts, holds) use a conditional update in the posting transaction: `UPDATE balances SET posted = posted - :amount, version = version + 1 WHERE account_id = :id AND posted >= :amount`. Zero rows updated means insufficient funds, and the whole entry rolls back.
- Entries touching several protected accounts lock balance rows in sorted account-id order to avoid deadlocks.
- Hot accounts never need an overdraft check (fee revenue only grows; clearing accounts are reconciled, not limited). Do not keep a synchronous balance row for them: append lines only and compute the balance from the last snapshot plus lines since, in a background aggregator. If a synchronous balance is needed, split the account into N sub-accounts chosen by entry id and sum them on read.

### Scaling beyond one primary

- Today's peak fits one primary; plan for 10x. Sharding by account breaks single-transaction entries whose lines live on different shards.
- Option A: a distributed SQL database with serializable cross-shard transactions; simplest model, higher latency per entry.
- Option B: each shard stays balanced on its own by routing cross-shard movements through per-shard clearing accounts, with a saga that posts the two halves; global clearing accounts net to zero once both halves land, and an invariant job alerts when they do not.

### Reconciliation

- Ingest processor and bank settlement reports idempotently (by file hash), normalize them, and match each record to ledger lines by external reference, amount, currency and date window.
- Settlement is late by design (one to three days), so a record is a break only after its expected window passes. Break types: in the report but not in the ledger, in the ledger but not in the report, amount or currency mismatch, duplicate.
- Breaks go to an operations queue with age and amount; resolutions are adjustment entries that require a second approver.
- Internal invariants run continuously: every entry balances, all lines per currency sum to zero (trial balance), every derived balance equals its lines.

### Auditability and time

- The application's database role can insert but not update or delete `entries` and `lines`.
- `as_of` queries combine the latest snapshot before the date with lines after it. Two questions differ: "what was the balance on March 31" (by `effective_at`) and "what did we report on March 31" (by `recorded_at`); support both.
- Close each month: snapshot, lock the period, and post later corrections with the current `recorded_at` and an `effective_at` in the closed period only through an approved adjustment.
- Tamper evidence: each entry stores the hash of the previous entry in its partition; periodic exports go to write-once storage.

## Failure modes

| Failure | Effect | Mitigation |
|---------|--------|------------|
| Caller times out after the ledger committed | Caller retries | Same key returns the original entry; no double posting |
| Primary database fails | Writes refused briefly | Synchronous replica promoted with fencing; callers retry with the same keys |
| Processor charged the card but the charges service crashed before posting | Ledger misses money | The charges service's own state machine retries the post; reconciliation catches anything left |
| Outbox relay down | Read models and notifications lag | The ledger stays correct; relay catches up from the outbox |
| Bad deploy posts wrong entries | Wrong balances | Balance invariants alert, entries are reversible in bulk by event ref, deploys canaried on shadow traffic |
| Duplicate settlement file | Double matching | Idempotent ingestion by file hash and record number |
| Rounding differences on fees | Off-by-a-cent breaks | Integer minor units, explicit rounding rules, a rounding account for remainders |

## Trade-offs

- **Consistency over availability**: the ledger refuses writes it cannot make durable and consistent; payment services queue and retry.
- **Synchronous balances only where they protect money**: overdraft-protected accounts pay the locking cost; hot accounts get asynchronous balances.
- **One database versus shards**: one primary is simpler and fast enough now; the sharding plan (distributed SQL or clearing accounts) is decided before it is needed.
- **Build versus buy**: purpose-built ledger databases exist and handle hot accounts and invariants natively; building on a relational database trades raw throughput for familiarity and tooling.

## Observability and cost

- Invariant monitors, all expected to be zero: unbalanced entries, trial balance per currency, derived balance drift, negative protected balances.
- Posting latency p99, idempotent replay rate and 409 rate, lock wait time on balance rows, outbox lag, reconciliation breaks by type, age and amount, time to close a period.
- Cost is modest: one strongly consistent database cluster with synchronous replicas, about 12 TB a year, and long-term archival for 7 years. The real cost is operational rigor: approvals, audits and on-call for breaks.

## Evolution

- Currency conversion through per-currency FX accounts, with the rate recorded on the entry.
- Multiple legal entities with intercompany accounts.
- Real-time payouts, which tighten reconciliation windows.
- Sharding by merchant when growth requires it, using the plan above.
