# Bank Project (TypeScript): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | O(log p) per scheduled transfer; O(1) per balance change; O(log h) per historical read; O(a log a) per ranking | O(a + h + p) | default answer; each level adds a field, a class or a module |

Here `a` is the number of accounts, `h` the number of balance changes of one account, and `p` the number of scheduled transfers.

## How the project grows level by level

| Level | New requirement | What the code adds |
|-------|-----------------|--------------------|
| 1 | Accounts, deposits, transfers | `Account` in `src/models.ts` owns its balance and the rules that move money (`deposit`, `canSend`, `send`); `Accounts` in `src/accounts.ts` looks accounts up; `Bank` checks every failure before any change |
| 2 | Rank accounts by money sent | A private `#sent` total on `Account`, raised by `send`, and the comparator `bySpending` in `src/bank.ts` |
| 3 | Transfers booked with their own delay, cancellable | `src/heap.ts`, a generic `MinHeap<T>`; `src/scheduler.ts`, whose `TransferScheduler` numbers bookings and queues them by `(due, number)`; `Bank.#settle` at the start of every public method |
| 4 | Merges and balances at a past time | `BalanceHistory` on every `Account`, a `#merge` record (into which account, at what time) set by `absorb`, and the `holder` getter that follows it |

The starter's `Bank` keeps a plain `Map<string, Account>`, which is all level 1 needs. The reference moves that map into `Accounts` once merges arrive, because a merged-away account must stay findable by its id for `getBalance` while every other method treats it as missing, and that distinction belongs in one place. Nothing earlier is rewritten when a level opens: each level adds a field, a class or a module, and the earlier methods gain one line, the call to `#settle`.

Time advances in exactly one place. Every public method starts with `this.#settle(timestamp)`, which runs the scheduled transfers that fell due since the previous call, so every method, read-only ones such as `topSpenders` and `getBalance` included, sees the bank as it is at `timestamp`.

## Approach: reference (Accounts with balance histories and a due-time heap)

### Intuition

The bank is a registry of account objects, and each account owns its numbers in private fields: balance, total sent, lifetime and history. The only thing that happens without a call asking for it is a scheduled transfer, which runs on its own clock. Ordering those transfers by due time, with the booking number as a tie-break, gives exactly the order a real clock would run them in, and draining every transfer due by `timestamp` before each call keeps the ledger as if that clock existed.

A scheduled transfer is an immutable value, `{ sourceId, targetId, amount, due }`. Whether it still waits to run is the scheduler's business, so the scheduler wraps each one in a booking that carries its number and a `pending` flag. Cancelling does not touch the heap: a heap can only remove its top cheaply, so a cancel clears `pending`, and the scheduler drops a booking that is no longer pending when it reaches the top. This is lazy deletion: a cancelled entry costs one extra pop later instead of a search now.

Merges do not rewrite anything either. The absorbed account records which account took it in, and its `holder` getter follows those records to the open account at the end. A booked transfer still names the ids it was booked with and finds its current source and target through `holder` when it runs or is cancelled.

### Algorithm

1. `#settle(timestamp)`: take from the scheduler every pending transfer due at or before `timestamp`, in `(due, number)` order. For each, find the accounts that now hold its source and target; when they are different accounts and the source holds at least `amount`, move the money and add `amount` to the source's total sent, recording both changes at the transfer's due time. Otherwise the transfer is skipped. Every public method calls this first.
2. Level 1: `createAccount` rejects a known id, otherwise opens an account whose history starts with balance 0 at `timestamp`. `deposit` adds to an open account. `transfer` checks that both accounts are open, distinct and that the source can afford it; only then does it move the money and add `amount` to the source's total sent. The same `canSend` and `send` serve scheduled transfers.
3. Level 2: `topSpenders` sorts the open accounts by total sent, descending, then by id, and formats the first `n`.
4. Level 3: `scheduleTransfer` checks that both accounts are open and distinct, then hands `{ sourceId, targetId, amount, due: timestamp + delay }` to the scheduler, which numbers it `transfer<k>`, with `k` the number of bookings so far plus one, and pushes the booking on the heap. The balance is not looked at. `cancelTransfer` finds the transfer while it is still pending, checks that the account holding its source now is `accountId`, and clears `pending`.
5. Level 4: `mergeAccounts` checks that both accounts are open and distinct, adds the other's balance and total sent to the first, and records on the other where it went and when. `getBalance` returns `-1` before the account's creation or from its merge on, and otherwise the last history entry at or before `timeAt`.

### Design

| File | Responsible for |
|------|-----------------|
| `src/bank.ts` | `Bank`, the public API and the only module that knows the level rules as a whole: it settles due transfers first in every method, checks requests, delegates, and turns a missing result (`undefined`) into the sentinels `-1`, `""` and `false` |
| `src/accounts.ts` | `Accounts`: every account by id, open or merged away; opening, merging, and `holderOf`, the open account that holds an id now |
| `src/models.ts` | `Account`: balance, total sent, lifetime and merge record, all private, and the rules that change them (`deposit`, `canSend`, `send`, `absorb`); `BalanceHistory`: the time-ordered record of balances and its binary search |
| `src/scheduler.ts` | `ScheduledTransfer`, one booked transfer as a plain value, and `TransferScheduler`: booking numbers, the run order and lazy cancellation |
| `src/heap.ts` | `MinHeap<T>`, a binary heap ordered by a compare function, which knows nothing about money |
| `tests/heap.test.ts`, `tests/scheduler.test.ts`, `tests/models.test.ts` | Unit tests for the heap's order, the run order of bookings, history lookups and merges, the parts with boundaries that the level examples reach only through `Bank` |

Dependencies point one way: `bank` uses `accounts`, `scheduler` and the `Account` type, `accounts` uses `models`, `scheduler` uses `heap`, and `models` and `heap` import nothing from the project. The sentinels live only in `src/bank.ts`: the inner modules return `undefined` for "nothing here", so the grader's conventions never leak into the model, and `?.` with `??` turns them into sentinels at the edge. The scheduler never sees an account, so the same scheduler would serve any kind of delayed job, and the heap would serve any ordering.

### Correctness

Invariant: after `#settle(t)`, every transfer with `due <= t` has run, been skipped or been dropped as cancelled, in `(due, number)` order, and none with `due > t` has. The heap hands its entries out in that order, and `takeDue` stops at the first entry that is not due yet, so no due transfer is left behind and none runs early. Booking numbers are unique, so the order is total, and it matches the rule that transfers due at the same time run in booking order. A transfer is never due at the time of the call that books it, because `delay >= 1`. `takeDue` returns the whole batch before any of it runs, which changes nothing: running a transfer never books or cancels another.

Each history entry is written at the time of its change: the call's timestamp, or the due time for a scheduled transfer. A transfer due at `d` runs during the first call at or after `d`, no earlier call had a timestamp at or after `d`, and the transfers that run before it in the same `#settle` are due no later than `d`. The history therefore stays in time order and a binary search finds the balance at any moment. When several changes share a time (two transfers due at `t` and the call at `t`), the search counts the changes at or before the moment, so it lands after all of them and returns the balance after the last one.

`pending` is cleared exactly once: by a cancel, or by `takeDue` when the booking is handed out to run or be skipped. So a transfer runs at most once, a skipped one is never retried, and a cancel succeeds only while the transfer has neither run nor been skipped nor been cancelled.

Merge records form chains that end at an open account, because only open accounts absorb others and an absorbed id never comes back. Following the chain from a transfer's original source or target finds the account that holds it now, which is what rewriting every pending transfer at merge time would have stored. When both ends lead to the same account, `canSend` rejects the transfer as a self-transfer, so it is skipped. In `cancelTransfer`, the holder of the source is always open, so comparing its id with `accountId` also rejects a missing or merged-away `accountId`.

### Complexity

- Time: O(log p) per scheduled transfer; O(1) per balance change; O(log h) per historical read; O(a log a) per ranking — each booking is pushed on the heap once and popped once, whether it runs, is skipped or was cancelled, and `#settle` does no other work per call. A balance change pushes one entry onto an array, amortized O(1); `getBalance` is one binary search; `topSpenders` sorts the open accounts. Merge chains are followed in time proportional to their length, which is at most the number of merges.
- Space: O(a + h + p) — one object per account, one history entry per balance change, and one booking and at most one heap entry per scheduled transfer, cancelled ones included until they reach the top.

### Trade-offs

- An array kept sorted by due time would also work: insert with `splice` after a binary search, O(p) for the shift, and run the earliest transfer with `shift`, also O(p). Pushing and calling `sort` again is simpler still, and right on ties, because `Array.prototype.sort` is stable; V8 sorts with Timsort, so re-sorting an array that is sorted but for its last entry is a linear pass, O(p) per booking as well. The heap makes booking and running O(log p) each and leaves cancelled entries in place; with 1000 calls any of these is fast, but only the heap keeps booking logarithmic as the number of pending transfers grows.
- Removing a cancelled transfer from the heap right away needs an indexed heap that tracks each entry's position. Lazy deletion keeps the heap at about 70 lines and costs only the memory of the cancelled entries until they surface.
- Rewriting every pending transfer at merge time, as the statement describes it, needs a scan of all pending transfers or an index from account to its pending transfers, kept up to date on every booking, run and cancel. The merge record on the absorbed account gives the same answers with one field per merge. Path compression, pointing every account on a chain straight at its end, would make long chains cheap; with at most 1000 calls it is not worth the extra writes.
- Sorting all accounts in `topSpenders` is O(a log a). A bounded heap of size `n` makes it O(a log n), and an ordered structure keyed by total and id, updated on every transfer, makes queries O(n) at the price of O(log a) per transfer.
- One module would do: the single-file reference of Scheduled Transfers Bank passes every case of this problem in 261 lines, against about 400 here across five modules. The split costs imports, comments and a few delegating methods, and pays back when a level opens: level 3 is two new modules plus one `#settle` line in each existing method, and level 4 adds `BalanceHistory` and an account's lifetime to `src/models.ts`, while `Bank` only gains its two new methods.

### Pitfalls and edge cases

- Run due transfers before the call's own logic, in every public method, reads included. The methods written for levels 1 and 2 predate scheduling and are the easiest to forget: a `transfer` at the exact due time may only succeed because the scheduled one ran first.
- A FIFO queue in booking order is wrong: a transfer booked later with a shorter delay must run first, and the order decides which of two transfers the source can still afford.
- Ties on the due time go in booking order, so the compare function needs the booking number as a second key. A comparator that returns only `a.due - b.due` leaves ties to the heap's internal order, and a binary heap is not stable: two tied transfers happen to come out in booking order, but three pushed in a row come out first, third, second.
- Record a scheduled transfer at its due time, not at the time of the call that ran it, or `getBalance` between the two is wrong.
- Check funds when the transfer runs, not when it is booked. A skipped transfer stays skipped, even if the source receives money later, and it cannot be cancelled afterwards.
- Only the current source may cancel. The target cannot, and after a merge the merged-away id cannot either, while the account that absorbed it can.
- A transfer pending between two accounts that are then merged becomes a self-transfer; it must be skipped, and it must not add to the total sent.
- Transfer numbers count only successful bookings, across the whole bank.
- A merged-away account: `deposit`, `transfer`, `scheduleTransfer` and `cancelTransfer` treat it as missing, `topSpenders` leaves it out and `createAccount` cannot reuse its id, but `getBalance` before the merge still answers from its history.
- Ids compare as strings, so `b10` comes before `b9`. `localeCompare` with `{ numeric: true }` puts `b9` first, and plain `localeCompare` follows the runtime's locale; `<` compares UTF-16 code units, the same everywhere.
- A balance of 0 is a real answer. `transfer` returns 0 when the source sends its whole balance, and `getBalance` returns 0 for an empty account, so turning `undefined` into `-1` needs `??`; `||` turns 0 into `-1` too.
- Project traps: `src/bank.ts` must export `Bank` by name; a default export, or a class that is not exported, is not found. Local imports need their `.ts` extension, since Node resolves the path as written. Type-only syntax that cannot be erased (`enum`, `namespace`, constructor parameter properties) makes Node refuse the file before any test runs, and `tsc` reports it too, because `tsconfig.json` sets `erasableSyntaxOnly`.

### Language notes

- JavaScript has no priority queue, so the reference carries `MinHeap<T>` in `src/heap.ts`, about 70 lines. It takes a compare function with the contract of `Array.prototype.sort` (negative when `a` comes first), so the run order reads `a.transfer.due - b.transfer.due || a.number - b.number`: the `||` falls through to the booking number exactly when the due times are equal.
- `BalanceHistory` keeps one array of `{ at, balance }` records and writes its own upper-bound binary search, since there is no `bisect` either. Times only grow, because changes are recorded in time order.
- Node strips types instead of compiling them, so every file uses erasable syntax only: fields are assigned in the constructor body, with no parameter properties, and there are no enums. State is held in `#private` fields, which JavaScript enforces at run time; one `Account` can read another's `#balance` in `absorb`, because privacy is per class, not per instance.
- `number` holds every amount and balance exactly: they stay below `2^53`, within `Number.MAX_SAFE_INTEGER`. Bitwise operators would truncate them to 32 bits, so the code never uses `| 0` or `>> 1` on money; `Math.floor` halves the search ranges.
- Absence is `undefined` throughout, the value `Map.prototype.get` and optional chaining already produce; `null` never appears. `Accounts.open()` uses the iterator helpers of Node 22 and later (`map.values().filter(...).toArray()`) instead of copying every account into an array first.
- `topSpenders` sorts the fresh array that `open()` returns, so sorting it in place changes no stored state.
