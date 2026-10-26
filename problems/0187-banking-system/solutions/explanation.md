# Banking System: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| ledger | optimal | O(log h) per balance change or historical read; O(a log a) per ranking | O(a + h + p) | default answer; each level adds one field or one structure |

Here `a` is the number of accounts, `h` the number of balance changes of one account, and `p` the number of payments.

## How the design grows level by level

| Level | New requirement | What the design adds |
|-------|-----------------|----------------------|
| 1 | Accounts, deposits, transfers | `accounts: id -> Account(balance)`; every failure is checked before any mutation |
| 2 | Rank accounts by money sent | An `outgoing` counter on `Account`, bumped on every successful transfer |
| 3 | Payments, and a cashback 24 hours later | A `Payment` record, a FIFO queue of pending cashbacks, and a `settle(timestamp)` step at the start of every call |
| 4 | Merges and balances at a past time | A `(time, balance)` history per account, `closedAt` on merged-away accounts, and a `mergedInto` link to find who owns an old payment |

The decision that keeps level 3 and level 4 manageable is to make time advance in exactly one place. Every public method starts with `settle(timestamp)`, which credits the cashbacks that fell due since the previous call. Any method, including read-only ones such as `topSpenders` and `paymentStatus`, then sees a world that is up to date at `timestamp`.

## Approach: ledger (Accounts with balance histories and a cashback queue)

### Intuition

The ledger is a map of account objects, and each account owns its own numbers: balance, total sent, history and lifetime. The only behavior that is not triggered by the call itself is the cashback, which happens on its own schedule. Because every cashback is due exactly 24 hours after its payment and payments arrive in time order, the cashbacks also fall due in payment order. A queue, not a priority queue, holds them, and draining its front before each call keeps the ledger exactly as it would be with a real clock.

### Algorithm

1. `settle(timestamp)`: while the front payment of the queue is due at or before `timestamp`, pop it, credit its cashback to the account that now owns it, recording the change at the payment's due time, and mark it received. Every public method calls this first.
2. Level 1: `createAccount` rejects a known id, otherwise opens an account whose history starts with `(timestamp, 0)`. `deposit` adds to an open account. `transfer` checks that both accounts are open, distinct and that the source can afford it; only then does it move the money and add `amount` to the source's `outgoing`.
3. Level 2: `topSpenders` sorts the open accounts by `(-outgoing, id)` and formats the first `n`.
4. Level 3: `pay` checks the account and its balance, withdraws, adds to `outgoing`, creates `payment<k>` with `k` the number of successful payments so far plus one, and appends it to the queue with `due = timestamp + 86,400,000` and `cashback = amount * 2 / 100` rounded down. `paymentStatus` checks that the account is open, the payment exists, and the payment's current owner is this account.
5. Level 4: `mergeAccounts` checks both accounts, adds the other's balance and `outgoing` to the first, sets the other's `closedAt` and records `mergedInto[other] = account`. Pending cashbacks are not touched: `settle` resolves the current owner through `mergedInto` when they fall due. `getBalance` returns `-1` outside `[createdAt, closedAt)` and otherwise the last history entry at or before `timeAt`.

### Correctness

Invariant: after `settle(t)`, every cashback with `due <= t` has been credited, and none later. The queue is sorted by `due` because `due = timestamp + constant` and timestamps increase, so stopping at the first payment not yet due is exact.

Each history entry is written at the time the change happens: the call's timestamp, or the due time for a cashback. A cashback due at `d` is credited during the first call at or after `d`, and no earlier call had a timestamp at or after `d`, so the history stays in time order and a floor search finds the balance at any moment. Several changes at the same time (a cashback due at `t` and the call at `t`) keep the last one, which is the balance after all of them.

`mergedInto` forms chains that always end at an open account, because only open accounts can absorb others and an absorbed account is never reopened. Following the chain from a payment's original account therefore finds the account that owns it now, both for `paymentStatus` and for crediting a cashback after one or more merges.

### Complexity

- Time: O(log h) per balance change or historical read; O(a log a) per ranking — appends cost O(1) in Python and TypeScript and O(log h) in the `TreeMap` of Java and Kotlin; `getBalance` is one binary search; `topSpenders` sorts the open accounts. `settle` does O(1) work per cashback over the whole run. Merge chains are followed in time proportional to their length, which is at most the number of merges.
- Space: O(a + h + p) — one object per account, one history entry per balance change, one record per payment.

### Trade-offs

- Sorting all accounts in `topSpenders` is O(a log a). A heap of size `n` (`heapq.nsmallest`, a bounded `PriorityQueue`) makes it O(a log n), and an ordered set keyed by `(-outgoing, id)` updated on every transfer makes queries O(n) at the price of O(log a) per transfer. With 1000 calls the sort is the clearest choice; mention the ordered set if the interviewer pushes on scale.
- A priority queue for cashbacks would also be correct and would survive a change to per-payment delays. The FIFO queue relies on the constant delay; say so explicitly, since it is exactly the kind of assumption a later level might break.
- Moving pending cashbacks to the new owner during the merge is the obvious alternative to `mergedInto`. It needs an index from account to its pending payments, and payment status queries still need the payment's new owner, so the link is simpler.
- Storing a balance per change is the minimum for exact history. Snapshots every so often plus replay of deposits would save memory but complicate every read.

### Pitfalls and edge cases

- Validate everything before changing anything: a transfer to a missing account must not withdraw from the source.
- A transfer from an account to itself fails; without the check it would double-count `outgoing`.
- Credit due cashbacks before the call's own logic, including reads: a transfer at exactly the due time may only succeed because of the cashback.
- Record a cashback at its due time, not at the time of the call that processed it, or `getBalance` between the two is wrong.
- Payment numbers count only successful payments.
- A merged-away account: `deposit`, `transfer`, `pay` and `paymentStatus` treat it as missing, `topSpenders` leaves it out, but `getBalance` before the merge still answers from its history.
- Round the cashback down: 2% of 49 is 0, and the payment still completes its cashback.

### Language notes

- Python: `bisect_right(history, moment, key=...)` searches the list of `(time, balance)` tuples by time, and `sorted` with the key `(-outgoing, id)` ranks accounts. `collections.deque` is the queue.
- TypeScript: amounts stay well below `2^53`, so `number` is exact. There is no deque, so the reference keeps an array and a read index instead of `shift()`, which is O(n). The tie-break compares ids with `<`, not `localeCompare`.
- Java: `TreeMap<Long, Long>` with `floorEntry` is the history, and `put` on an existing time keeps the last balance of that moment. `Comparator.comparingLong(...).reversed().thenComparing(...)` sorts by spending, then id; `closedAt` is a nullable `Long`.
- Kotlin: `compareByDescending<Account> { it.outgoing }.thenBy { it.id }` expresses the ranking, `generateSequence(id) { mergedInto[it] }.last()` follows merges, and `?: return -1` keeps the guard clauses short.
