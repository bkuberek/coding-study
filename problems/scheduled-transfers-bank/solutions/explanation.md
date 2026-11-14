# Scheduled Transfers Bank: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| ledger-heap | optimal | O(log p) per scheduled transfer; O(log h) per balance change or historical read; O(a log a) per ranking | O(a + h + p) | default answer; each level adds one field or one structure |

Here `a` is the number of accounts, `h` the number of balance changes of one account, and `p` the number of scheduled transfers.

## How the design grows level by level

| Level | New requirement | What the design adds |
|-------|-----------------|----------------------|
| 1 | Accounts, deposits, transfers | `accounts: id -> Account(balance)`; every failure is checked before any mutation |
| 2 | Rank accounts by money sent | An `outgoing` counter on `Account`, bumped by every successful transfer |
| 3 | Transfers booked with their own delay, cancellable | A `ScheduledTransfer` record with a `pending` flag, a min-heap keyed by `(due, number)`, and a `settle(timestamp)` step at the start of every call |
| 4 | Merges and balances at a past time | A `(time, balance)` history per account, `closedAt` on merged-away accounts, and a `mergedInto` link that tells who now sends or receives a booked transfer |

As in Banking System, time advances in exactly one place. Every public method starts with `settle(timestamp)`, which runs the scheduled transfers that fell due since the previous call, so every method, read-only ones such as `topSpenders` and `getBalance` included, sees the bank as it is at `timestamp`.

What changes is the queue. Banking System credits every cashback after the same fixed delay, so cashbacks fall due in the order the payments were made and a FIFO queue is enough. Here each transfer has its own delay: a transfer booked later with a shorter delay falls due first. The pending transfers need a priority queue.

## Approach: ledger-heap (Accounts with balance histories and a due-time heap)

### Intuition

The bank is a map of account objects, and each account owns its numbers: balance, total sent, history and lifetime. The only thing that happens without a call asking for it is a scheduled transfer, which runs on its own clock. Ordering those transfers by due time, with the booking number as a tie-break, gives exactly the order a real clock would run them in, and draining every transfer due by `timestamp` before each call keeps the ledger as if that clock existed.

Cancelling does not touch the heap. A heap can only remove its top cheaply, so `cancelTransfer` clears the transfer's `pending` flag, and `settle` drops a transfer that is no longer pending when it reaches the top. This is lazy deletion: a cancelled entry costs one extra pop later instead of a search now.

### Algorithm

1. `settle(timestamp)`: while the heap's top is due at or before `timestamp`, pop it. If it is no longer pending (it was cancelled), drop it. Otherwise mark it as no longer pending, find the accounts that now hold its source and target through `mergedInto`, and, when they are different accounts and the source holds at least `amount`, move the money and add `amount` to the source's `outgoing`, recording both changes at the transfer's due time. Otherwise the transfer is skipped. Every public method calls this first.
2. Level 1: `createAccount` rejects a known id, otherwise opens an account whose history starts with `(timestamp, 0)`. `deposit` adds to an open account. `transfer` checks that both accounts are open, distinct and that the source can afford it; only then does it move the money and add `amount` to the source's `outgoing`. The same `canSend` and `send` steps serve scheduled transfers.
3. Level 2: `topSpenders` sorts the open accounts by `(-outgoing, id)` and formats the first `n`.
4. Level 3: `scheduleTransfer` checks that both accounts are open and distinct, creates `transfer<k>` with `k` the number of transfers booked so far plus one, stores it by id and pushes it on the heap with `due = timestamp + delay`. It does not look at the balance. `cancelTransfer` checks that the account is open, the transfer exists and is still pending, and the account that now holds its source is `accountId`; then it clears `pending`.
5. Level 4: `mergeAccounts` checks both accounts, adds the other's balance and `outgoing` to the first, sets the other's `closedAt` and records `mergedInto[other] = account`. Booked transfers are not rewritten: `cancelTransfer` and `settle` resolve the current source and target through `mergedInto`. `getBalance` returns `-1` outside `[createdAt, closedAt)` and otherwise the last history entry at or before `timeAt`.

### Correctness

Invariant: after `settle(t)`, every transfer with `due <= t` has run, been skipped or been dropped as cancelled, in `(due, number)` order, and none with `due > t` has. The heap returns its entries in that order, and `settle` stops at the first entry that is not due yet, so no due transfer is left behind and none runs early. Booking numbers are unique, so the order is total, and it matches the rule that transfers due at the same time run in booking order. A transfer is never due at the time of the call that books it, because `delay >= 1`.

Each history entry is written at the time of its change: the call's timestamp, or the due time for a scheduled transfer. A transfer due at `d` runs during the first call at or after `d`, no earlier call had a timestamp at or after `d`, and the transfers that run before it in the same `settle` are due no later than `d`. The history therefore stays in time order and a floor search finds the balance at any moment. When several changes share a time (two transfers due at `t` and the call at `t`), the floor search returns the last of them, the balance after all of them.

`pending` is cleared exactly once: by a cancel, or by `settle` when the transfer runs or is skipped. So a transfer runs at most once, a skipped one is never retried, and a cancel succeeds only while the transfer has neither run nor been skipped nor been cancelled.

`mergedInto` forms chains that end at an open account, because only open accounts absorb others and an absorbed id never comes back. Following the chain from a transfer's original source or target finds the account that holds it now, which is what rewriting every pending transfer at merge time would have stored. When both ends lead to the same account, `canSend` rejects the transfer as a self-transfer, so it is skipped.

### Complexity

- Time: O(log p) per scheduled transfer; O(log h) per balance change or historical read; O(a log a) per ranking — each transfer is pushed on the heap once and popped once, whether it runs, is skipped or was cancelled, and `settle` does no other work per call. History appends cost O(1) in Python, TypeScript, Go and Rust and O(log h) in the `TreeMap` of Java and Kotlin; `getBalance` is one binary search; `topSpenders` sorts the open accounts. Merge chains are followed in time proportional to their length, which is at most the number of merges.
- Space: O(a + h + p) — one object per account, one history entry per balance change, and one record and at most one heap entry per scheduled transfer, cancelled ones included until they reach the top.

### Trade-offs

- A list kept sorted by `(due, number)` would also work. Inserting costs O(p) for the shift, but running the earliest transfer is a pop from one end and a cancel can remove the entry after a binary search. The heap makes booking and running O(log p) each and leaves cancelled entries in place; with 1000 calls either is fast, but only the heap keeps booking logarithmic as the number of pending transfers grows.
- Removing a cancelled transfer from the heap right away needs an indexed heap that tracks each entry's position (or a balanced tree keyed by `(due, number)`). Lazy deletion keeps the standard library heap and costs only the memory of the cancelled entries until they surface.
- Rewriting every pending transfer at merge time, as the statement describes it, needs either a scan of all pending transfers or an index from account to its pending transfers, updated on every booking, run and cancel. The `mergedInto` link gives the same answers with one map entry per merge.
- Sorting all accounts in `topSpenders` is O(a log a). A heap of size `n` makes it O(a log n), and an ordered set keyed by `(-outgoing, id)` updated on every transfer makes queries O(n) at the price of O(log a) per transfer.

### Pitfalls and edge cases

- A FIFO queue in booking order is the natural carry-over from Banking System and is wrong here: a transfer booked later with a shorter delay must run first, and the order decides which of two transfers the source can still afford.
- Ties on the due time go in booking order. A heap of `(due, transfer)` pairs alone is not stable, so the booking number has to be part of the key.
- Run due transfers before the call's own logic, reads included: a transfer due exactly at a call's timestamp runs first, and a `transfer` at that time may only succeed because of it.
- Record a scheduled transfer at its due time, not at the time of the call that ran it, or `getBalance` between the two is wrong.
- Check funds when the transfer runs, not when it is booked. A skipped transfer stays skipped, even if the source receives money later, and it cannot be cancelled afterwards.
- Only the current source may cancel. The target cannot, and after a merge the merged-away id cannot either, while the account that absorbed it can.
- A transfer pending between two accounts that are then merged becomes a self-transfer; it must be skipped, and it must not add to `outgoing`.
- Transfer numbers count only successful bookings, across the whole bank.
- A merged-away account: `deposit`, `transfer`, `scheduleTransfer` and `cancelTransfer` treat it as missing, `topSpenders` leaves it out and `createAccount` cannot reuse its id, but `getBalance` before the merge still answers from its history.

### Language notes

- Python: `heapq` works on a plain list of tuples `(due, number, transfer)`. The number is unique, so tuple comparison never reaches the transfer object, which defines no ordering. `bisect_right(history, moment, key=...)` searches the `(time, balance)` history.
- TypeScript: there is no heap in the standard library, so the reference carries a small binary min-heap that takes a `before(a, b)` function and compares due time, then number. Amounts stay well below `2^53`, so `number` is exact. The tie-break in `topSpenders` compares ids with `<`, not `localeCompare`.
- Java: `PriorityQueue` with `Comparator.comparingLong(due).thenComparingLong(number)` is the heap; `peek` and `poll` read and remove the earliest transfer. `TreeMap<Long, Long>` with `floorEntry` is the history, and `put` on an existing time keeps the last balance of that moment.
- Kotlin: the same `java.util.PriorityQueue`, built with `compareBy({ it.due }, { it.number })`. `generateSequence(id) { mergedInto[it] }.last()` follows merges, and `?: return` keeps the guard clauses short.
- Go: `container/heap` works on any type that implements `heap.Interface`, so `dueQueue` defines `Len`, `Less` (due, then number), `Swap`, `Push` and `Pop`, and the bank calls `heap.Push` and `heap.Pop`, never the methods directly. Map iteration order is random, so `TopSpenders` sorts with an explicit tie-break on the id.
- Rust: `BinaryHeap` is a max-heap, so the entries are `Reverse((due, position))`, where `position` indexes the transfers in booking order and doubles as the tie-break; implementing `Ord` in reverse on a struct would work as well. Two accounts of one `HashMap` cannot be borrowed mutably at once, so `send` validates first and then touches the target and the source one at a time; `transfer` and `settle` share it, and `settle` ignores its `None` for a skipped transfer.
