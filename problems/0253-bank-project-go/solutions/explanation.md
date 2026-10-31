# Bank Project (Go): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | O(log p) per scheduled transfer; O(1) per balance change; O(log h) per historical read; O(a log a) per ranking | O(a + h + p) | default answer; each level adds a field, a file or a package |

Here `a` is the number of accounts, `h` the number of balance changes of one account, and `p` the number of scheduled transfers.

## How the project grows level by level

| Level | New requirement | What the code adds |
|-------|-----------------|--------------------|
| 1 | Accounts, deposits, transfers | `account` in `account.go` owns its balance and the rules that move money (`deposit`, `canSend`, `send`); `ledger` in `ledger.go` looks accounts up; `Bank` checks every failure before any change |
| 2 | Rank accounts by money sent | A `sent` field on `account`, raised by `send`, and the comparison `bySpending` in `bank.go` |
| 3 | Transfers booked with their own delay, cancellable | The package `internal/schedule`: `Transfer`, `Scheduler`, which numbers bookings and hands them out by `(due, number)`, and `queue`, its `container/heap` queue; `Bank.settle` at the start of every exported method |
| 4 | Merges and balances at a past time | `history` in `history.go` on every `account`, the `mergedInto` link and `mergedAt` time set by `absorb`, and `holder`, which follows the links |

The starter's `Bank` keeps a plain `map[string]*account`, which is all level 1 needs. The reference moves that map into `ledger` once merges arrive, because a merged-away account must stay findable by its id for `GetBalance` while every other method treats it as missing, and that distinction belongs in one place. Nothing earlier is rewritten when a level opens: each level adds a field, a file or a package, and the earlier methods gain one line, the call to `settle`.

Time advances in exactly one place. Every exported method starts with `b.settle(timestamp)`, which runs the scheduled transfers that fell due since the previous call, so every method, read-only ones such as `TopSpenders` and `GetBalance` included, sees the bank as it is at `timestamp`.

## Approach: reference (Accounts with balance histories and a due-time heap)

### Intuition

The bank is a registry of accounts, and each account owns its numbers in unexported fields: balance, total sent, history and merge link. The only thing that happens without a call asking for it is a scheduled transfer, which runs on its own clock. Ordering those transfers by due time, with the booking number as a tie-break, gives exactly the order a real clock would run them in, and draining every transfer due by `timestamp` before each call keeps the ledger as if that clock existed.

A scheduled transfer is a plain value, `schedule.Transfer{Source, Target, Amount, Due}`. Whether it still waits to run is the scheduler's business, so the scheduler wraps each one in a `booking` that carries its number and a `pending` flag. Cancelling does not touch the heap: a heap can only remove its top cheaply, so a cancel clears `pending`, and the scheduler drops a booking that is no longer pending when it reaches the top. This is lazy deletion: a cancelled entry costs one extra pop later instead of a search now.

Merges do not rewrite anything either. The absorbed account points at the account that took it in, and `holder` follows those pointers to the open account at the end. A booked transfer still names the ids it was booked with and finds its current source and target through `holder` when it runs or is cancelled.

### Algorithm

1. `settle(now)`: take from the scheduler every pending transfer due at or before `now`, in `(due, number)` order. For each, find the accounts that now hold its source and target; when they are different accounts and the source holds at least `Amount`, move the money and add `Amount` to the source's total sent, recording both changes at the transfer's due time. Otherwise the transfer is skipped. Every exported method calls this first.
2. Level 1: `CreateAccount` rejects a known id, otherwise opens an account whose history starts with balance 0 at `timestamp`. `Deposit` adds to an open account. `Transfer` checks that both accounts are open and distinct and that the source can afford it; only then does it move the money and add `amount` to the source's total sent. The same `canSend` and `send` serve scheduled transfers.
3. Level 2: `TopSpenders` collects the open accounts sorted by total sent, descending, then by id, and formats the first `n`.
4. Level 3: `ScheduleTransfer` checks that both accounts are open and distinct, then hands `Transfer{Source, Target, Amount, Due: timestamp + delay}` to the scheduler, which numbers it `transfer<k>`, with `k` the number of bookings so far plus one, and pushes the booking on the heap. The balance is not looked at. `CancelTransfer` finds the transfer while it is still pending, checks that the account holding its source now is `accountID`, and clears `pending`.
5. Level 4: `MergeAccounts` checks that both accounts are open and distinct, adds the other's balance and total sent to the first, and records on the other where it went and when. `GetBalance` returns `-1` for an unknown id, before the account's creation or from its merge on, and otherwise the last history entry at or before `timeAt`.

### Design

| File | Responsible for |
|------|-----------------|
| `bank.go` | `Bank` and `NewBank`, the exported API and the only code that knows the level rules as a whole: it settles due transfers first in every method, checks requests, delegates, and turns a missing result (`nil`, or `false` from a comma-ok call) into the sentinels `-1`, `""` and `false` |
| `ledger.go` | `ledger`: every account by id, open or merged away; opening, merging, `findOpen`, and `holder`, the open account that holds an id now |
| `account.go` | `account`: balance, total sent, history and merge link, and the rules that change them (`deposit`, `canSend`, `send`, `absorb`, `balanceAt`) |
| `history.go` | `history`: the time-ordered record of balances and its binary search |
| `internal/schedule/schedule.go` | `Transfer`, one booked transfer as a plain value, and `Scheduler`: booking numbers, the run order and lazy cancellation |
| `internal/schedule/queue.go` | `queue`, the `heap.Interface` that `container/heap` keeps in `(due, number)` order |
| `history_test.go`, `ledger_test.go`, `internal/schedule/schedule_test.go` | Unit tests for history lookups, merge chains and lifetimes, and the run order and cancellation of bookings: the parts with boundaries that the level examples reach only through `Bank` |

Dependencies point one way: package `bank` imports `internal/schedule`, which imports nothing from the module. Inside `bank`, `Bank` uses `ledger`, `ledger` uses `account`, and `account` uses `history`. The sentinels live only in `bank.go`: the inner code returns `nil` or `false` for "nothing here", the way a map lookup does, so the grader's conventions never leak into the model. The scheduler never sees an account, so the same package would serve any kind of delayed job. `internal/` makes that package importable only from inside the module, the tests under `tests/` included, so its exported names are an API for the rest of the bank, not for anyone else.

### Correctness

Invariant: after `settle(t)`, every transfer with `Due <= t` has run, been skipped or been dropped as cancelled, in `(due, number)` order, and none with `Due > t` has. The heap hands its entries out in that order, and `TakeDue` stops at the first entry that is not due yet, so no due transfer is left behind and none runs early. Booking numbers are unique, so `Less` is a total order, and it matches the rule that transfers due at the same time run in booking order. A transfer is never due at the time of the call that books it, because `delay >= 1`. `TakeDue` returns the whole batch before any of it runs, which changes nothing: running a transfer never books or cancels another.

Each history entry is written at the time of its change: the call's timestamp, or the due time for a scheduled transfer. A transfer due at `d` runs during the first call at or after `d`, no earlier call had a timestamp at or after `d`, and the transfers that run before it in the same `settle` are due no later than `d`. The history therefore stays in time order and a binary search finds the balance at any moment. When several changes share a time (two transfers due at `t` and the call at `t`), the search finds the first entry after the moment, so it lands after all of them and returns the balance after the last one.

`pending` is cleared exactly once: by a cancel, or by `TakeDue` when the booking is handed out to run or be skipped. So a transfer runs at most once, a skipped one is never retried, and a cancel succeeds only while the transfer has neither run nor been skipped nor been cancelled.

Merge links form chains that end at an open account, because only open accounts absorb others and an absorbed id never comes back. Following the chain from a transfer's original source or target finds the account that holds it now, which is what rewriting every pending transfer at merge time would have stored. When both ends lead to the same account, `canSend` rejects the transfer as a self-transfer, so it is skipped. In `CancelTransfer`, the holder of the source is always open, so comparing its id with `accountID` also rejects a missing or merged-away `accountID`.

### Complexity

- Time: O(log p) per scheduled transfer; O(1) per balance change; O(log h) per historical read; O(a log a) per ranking — each booking is pushed on the heap once and popped once, whether it runs, is skipped or was cancelled, and `settle` does no other work per call. A balance change appends one entry to a slice, amortized O(1); `GetBalance` is one `sort.Search`; `TopSpenders` sorts the open accounts. Merge chains are followed in time proportional to their length, which is at most the number of merges.
- Space: O(a + h + p) — one struct per account, one history entry per balance change, and one booking and at most one heap entry per scheduled transfer, cancelled ones included until they reach the top.

### Trade-offs

- A slice kept sorted by due time would also work: `slices.Insert` at the place `slices.BinarySearchFunc` finds, O(p) for the shift, and take the earliest transfer from the front. Appending and calling `slices.SortStableFunc` again is simpler still and right on ties, since it is stable, but it sorts the whole slice again on every booking. The heap makes booking and running O(log p) each and leaves cancelled entries in place; with 1000 calls any of these is fast, but only the heap keeps booking logarithmic as the number of pending transfers grows.
- Removing a cancelled transfer from the heap right away needs each entry's index, kept up to date in `Swap`, and `heap.Remove(&q, i)`. Lazy deletion keeps `queue` to its five methods and costs only the memory of the cancelled entries until they surface.
- Rewriting every pending transfer at merge time, as the statement describes it, needs a scan of all pending transfers or an index from account to its pending transfers, kept up to date on every booking, run and cancel. The `mergedInto` pointer gives the same answers with one field per merge. Path compression, pointing every account on a chain straight at its end, would make long chains cheap; with at most 1000 calls it is not worth the extra writes.
- Sorting all accounts in `TopSpenders` is O(a log a). A bounded heap of size `n` makes it O(a log n), and an ordered structure keyed by total and id, updated on every transfer, makes queries O(n) at the price of O(log a) per transfer.
- One package would do, and Go code often keeps a small program in one: the scheduler could be four more files in package `bank`. A package of its own pays for itself here because its boundary is checked by the compiler: `internal/schedule` cannot reach an account, so the run order and cancellation rules are testable without a bank, and `bank` can use only what `schedule` exports.

### Pitfalls and edge cases

- Run due transfers before the call's own logic, in every exported method, reads included. The methods written for levels 1 and 2 predate scheduling and are the easiest to forget: a `Transfer` at the exact due time may only succeed because the scheduled one ran first.
- A FIFO queue in booking order is wrong: a transfer booked later with a shorter delay must run first, and the order decides which of two transfers the source can still afford.
- Ties on the due time go in booking order, so `Less` needs the booking number as a second key. With `q[i].Due < q[j].Due` alone, equal entries come out in whatever order the heap's swaps left them: `container/heap` pops three equal pushes as first, third, second, because `heap.Pop` swaps the last entry to the front and `down` stops at once among equals.
- Record a scheduled transfer at its due time, not at the time of the call that ran it, or `GetBalance` between the two is wrong.
- Check funds when the transfer runs, not when it is booked. A skipped transfer stays skipped, even if the source receives money later, and it cannot be cancelled afterwards.
- Only the current source may cancel. The target cannot, and after a merge the merged-away id cannot either, while the account that absorbed it can.
- A transfer pending between two accounts that are then merged becomes a self-transfer; it must be skipped, and it must not add to the total sent.
- Transfer numbers count only successful bookings, across the whole bank.
- A merged-away account: `Deposit`, `Transfer`, `ScheduleTransfer` and `CancelTransfer` treat it as missing, `TopSpenders` leaves it out and `CreateAccount` cannot reuse its id, but `GetBalance` before the merge still answers from its history.
- Ids compare as strings, byte by byte, so `b10` comes before `b9`. Parsing the digits off an id, or a "natural" sort, puts `b9` first.
- A balance of 0 is a real answer. `Transfer` returns 0 when the source sends its whole balance, and `GetBalance` returns 0 for an empty account, so absence travels as `nil` or a `false` second result, never as a zero value that means "not found".
- Project traps: `Bank` and `NewBank` must stay in `bank.go` at the module root, in a package other than `main`, because the grader imports that package by the module path. Methods must be exported (`CreateAccount`, not `createAccount`) and keep their types: `int64` where the level says `int64`, so an `int` parameter is a signature mismatch even though it is 64 bits wide on most machines. The tests under `tests/` are package `tests_test` and see only exported names, and a level's file stops that package from compiling until every method it calls exists. A `go.sum`, a second `require` or a `use` of this folder in the workspace's root `go.work` breaks the offline build; `cstudy start` writes the folder's own `go.work`.

### Language notes

- Go has no priority queue type, but `container/heap` turns any slice type into one: implement `heap.Interface` (`Len`, `Less`, `Swap`, and `Push` and `Pop` on the pointer receiver), then call `heap.Push(&q, x)` and `heap.Pop(&q)`, never `q.Push` and `q.Pop`, which only append to and cut the slice. `Pop` returns `any`, so the scheduler asserts `.(*booking)`: the standard library has no generic heap.
- `Less` reads `cmp.Or(cmp.Compare(q[i].Due, q[j].Due), cmp.Compare(q[i].number, q[j].number)) < 0`: `cmp.Or` returns its first non-zero argument, so it falls through to the booking number exactly when the due times are equal. `bySpending` is written the same way for `slices.SortedFunc`, which wants a three-way comparison rather than a `less` function.
- Maps have no order, and Go randomizes it on purpose: `ledger.openAccounts` yields the accounts in a different order on every run. `TopSpenders` is still deterministic because `bySpending` is a total order; a comparison by total alone would rank equal totals differently from one run to the next, and only sometimes fail.
- `openAccounts` returns an `iter.Seq[*account]`, a range-over-func iterator, so `slices.SortedFunc` collects and sorts the open accounts without an intermediate slice of every account.
- `history` is a named slice type with a pointer-receiver `record`, because `append` may return a new backing array that the field must keep, and a value-receiver `at`. `sort.Search` finds the first entry after the moment asked for; `slices.BinarySearchFunc` would find the first one at it, which is the wrong end when several changes share a time.
- Absence is a `nil` pointer, the value a map lookup of `*account` already produces, or a comma-ok `false`, as in `Scheduler.Pending`. The exported API returns sentinels instead of `(int64, error)` because the grader's contract fixes the signatures; the inner types keep Go's own conventions.
- `int64` holds every amount and balance exactly: they stay below `2^53`. `TopSpenders` takes `n` as `int`, the type of slice lengths, so `ranked[:min(n, len(ranked))]` needs no conversion; `min` is a builtin since Go 1.21.
- The parameters are named `accountID`, `sourceID` and `transferID`, as Go spells initialisms, while the statement keeps the catalog's `accountId`. A parameter's name is not part of a method's type, so the grader accepts either.
