# Payments Ledger

## Question

Design the ledger at the center of a payments platform for online merchants. Other services (charges, refunds, payouts, disputes) move money by asking the ledger to record it; the ledger is the system of record for who is owed what. External payment processors and banks settle the real money days later.

## Functional requirements

- Record every money movement: card charges with platform fees, refunds, payouts to merchants' bank accounts, chargebacks and manual adjustments.
- Report each account's balance, both settled and pending, and its full history; answer "what was this balance at the end of last month?".
- Place and release holds, so a payout cannot spend money already committed to a pending refund.
- Prevent payouts that would overdraw a merchant's balance.
- Reconcile the ledger against the settlement reports of processors and banks, and surface every mismatch.
- Support multiple currencies; there is no currency conversion inside a single movement.

## Non-functional requirements

- Correctness first: money is never created or lost, every recorded movement balances, and every business event is recorded exactly once even when callers retry.
- Durability: an acknowledged write is never lost (recovery point objective of zero).
- Auditability: history is immutable and kept for 7 years; every entry says who or what caused it and why.
- Posting latency p99 under 100 ms; 99.95% availability for writes, and the ledger may refuse writes rather than record something wrong.
- Balances read for payouts are strongly consistent.

## Scale

- 20 million payments per day, about 4 ledger lines each once fees and settlement are counted.
- Peak traffic (holiday sales) is 5 times the average.
- 10 million merchant accounts plus internal accounts (fees, processor clearing, reserves).
- A few internal accounts (platform fee revenue, the main processor's clearing account) take a line on almost every payment.
