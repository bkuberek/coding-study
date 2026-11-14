# Bank Project (Kotlin): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | O(log p) per scheduled transfer; O(log h) per balance change and per historical read; O(a log a) per ranking | O(a + h + p) | default answer; each level adds a property, a class or a package |

Here `a` is the number of accounts, `h` the number of balance changes of one account, and `p` the number of scheduled transfers.

## How the project grows level by level

| Level | New requirement | What the code adds |
|-------|-----------------|--------------------|
| 1 | Accounts, deposits, transfers | `Account` owns its balance behind a `private set` and the rules that move money (`deposit`, `canSend`, `send`); `Ledger` looks accounts up; `Bank` checks every failure before any change |
| 2 | Rank accounts by money sent | A `sent` property on `Account`, raised by `send`, and the comparator `BY_SPENDING` in `Bank` |
| 3 | Transfers booked with their own delay, cancellable | The package `bank.schedule`: `ScheduledTransfer`, a data class, and `Scheduler`, which numbers bookings and hands them out of a `PriorityQueue` by due time, then booking number; `Bank.settle` at the start of every public method |
| 4 | Merges and balances at a past time | `BalanceHistory` on every `Account`, the `merge` link that `absorb` sets, and `holder`, which follows the links |

The starter's `Bank` keeps a plain `mutableMapOf<String, Account>()`, which is all level 1 needs. The reference moves that map into `Ledger` once merges arrive, because a merged-away account must stay findable by its id for `getBalance` while every other method treats it as missing, and that distinction belongs in one place. Nothing earlier is rewritten when a level opens: each level adds a property, a class or a package, and the earlier methods gain one line, the call to `settle`.

Time advances in exactly one place. Every public method starts with `settle(timestamp)`, which runs the scheduled transfers that fell due since the previous call, so every method, read-only ones such as `topSpenders` and `getBalance` included, sees the bank as it is at `timestamp`.

## Approach: reference (Accounts with balance histories and a due-time heap)

### Intuition

The bank is a registry of accounts, and each account owns its numbers: balance and total sent are readable from outside but change only through the account's own methods. The only thing that happens without a call asking for it is a scheduled transfer, which runs on its own clock. Ordering those transfers by due time, with the booking number as a tie-break, gives exactly the order a real clock would run them in, and draining every transfer due by `timestamp` before each call keeps the ledger as if that clock existed.

A scheduled transfer is a plain value, `ScheduledTransfer(sourceId, targetId, amount, due)`. Whether it may still run is the scheduler's business: its `pending` map holds exactly the bookings that may still run, so cancelling removes the booking from that map and leaves the queue alone. A heap removes only its head cheaply, so a cancelled booking stays in the queue and is dropped when it reaches the head and is no longer pending. This is lazy deletion: a cancelled entry costs one extra `poll` later instead of a linear `remove` now.

Merges do not rewrite anything either. The absorbed account records the account that took it in, and `holder` follows those links to the open account at the end. A booked transfer still names the ids it was booked with and finds its current source and target through `holder` when it runs or is cancelled.

### Algorithm

1. `settle(now)`: take from the scheduler every pending transfer due at or before `now`, in (due, number) order. For each, find the accounts that now hold its source and target; when they are different accounts and the source holds at least `amount`, move the money and add `amount` to the source's total sent, recording both changes at the transfer's due time. Otherwise the transfer is skipped. Every public method calls this first.
2. Level 1: `createAccount` rejects a known id, otherwise opens an account whose history starts with balance 0 at `timestamp`. `deposit` adds to an open account. `transfer` checks that both accounts are open and distinct and that the source can afford it; only then does it move the money and add `amount` to the source's total sent. The same `canSend` and `send` serve scheduled transfers.
3. Level 2: `topSpenders` sorts the open accounts by total sent, descending, then by id, and formats the first `n`.
4. Level 3: `scheduleTransfer` checks that both accounts are open and distinct, then hands `ScheduledTransfer(sourceId, targetId, amount, due = timestamp + delay)` to the scheduler, which numbers it `transfer<k>`, with `k` one more than the bookings so far, and adds it to the pending map and the queue. The balance is not looked at. `cancelTransfer` finds the transfer while it is still pending, checks that the account holding its source now is `accountId`, and removes it from the pending map.
5. Level 4: `mergeAccounts` checks that both accounts are open and distinct, adds the other's balance and total sent to the first, and records on the other where it went and when. `getBalance` returns `-1` for an unknown id, before the account's creation or from its merge on, and otherwise the last balance recorded at or before `timeAt`.

### Design

| File | Responsible for |
|------|-----------------|
| `src/main/kotlin/bank/Bank.kt` | `Bank`, the public API and the only code that knows the level rules as a whole: it settles due transfers first in every method, checks requests, delegates, and turns a `null` from the inner classes into the sentinels `-1`, `""` and `false` |
| `src/main/kotlin/bank/Ledger.kt` | `Ledger`: every account by id, open or merged away; opening, merging, `findOpen`, and `holder`, the open account that holds an id now |
| `src/main/kotlin/bank/Account.kt` | `Account`: balance, total sent, history and merge link, and the rules that change them (`deposit`, `canSend`, `send`, `absorb`, `balanceAt`) |
| `src/main/kotlin/bank/BalanceHistory.kt` | `BalanceHistory`: balances by time in a `TreeMap`, and the lookup of the last one at or before a moment |
| `src/main/kotlin/bank/schedule/Scheduler.kt` | `ScheduledTransfer`, one booked transfer as a data class, and `Scheduler`: booking numbers, the run order and lazy cancellation |
| `src/test/kotlin/bank/BalanceHistoryTest.kt`, `LedgerTest.kt`, `schedule/SchedulerTest.kt` | Unit tests for history lookups, merge chains and lifetimes, and the run order and cancellation of bookings: the parts with boundaries that the level examples reach only through `Bank` |

`Bank` is the only public class; everything else is `internal`, visible in this Gradle module and its tests and nowhere else. Dependencies point one way: `Bank` uses `Ledger` and `Scheduler`, `Ledger` uses `Account`, and `Account` uses `BalanceHistory`. The sentinels live only in `Bank`: the inner classes return `null` for "nothing here", which Kotlin's type system tracks, so the grader's conventions never leak into the model. `bank.schedule` imports nothing from `bank` and never sees an account, so the same scheduler would serve any kind of delayed job. Kotlin does not enforce that direction between packages, as Go's `internal/` or Java's module system can: it holds because nothing in `bank.schedule` imports `bank`, and a review keeps it so.

### Correctness

Invariant: after `settle(t)`, every transfer with `due <= t` has run, been skipped or been dropped as cancelled, in (due, number) order, and none with `due > t` has. The queue's head is always the least booking by that comparator, and `takeDue` stops at the first head that is not due yet, so no due transfer is left behind and none runs early. Booking numbers are unique, so the comparator is a total order and the order of equal due times is the booking order, whatever the heap's internal layout. A transfer is never due at the time of the call that books it, because `delay >= 1`. `takeDue` returns the whole batch before any of it runs, which changes nothing: running a transfer never books or cancels another.

Each balance is recorded at the time of its change: the call's timestamp, or the due time for a scheduled transfer. A transfer due at `d` runs during the first call at or after `d`, so no change later than `d` has been recorded when it runs, and the transfers that run before it in the same `settle` are due no later than `d`. Writing a later balance under the same time replaces the earlier one, so the `TreeMap` keeps the balance after the last change at each moment, and `floorEntry(t)` returns the balance after every change at or before `t`.

A booking leaves the pending map exactly once: when it is cancelled, or when `takeDue` hands it out to run or be skipped. So a transfer runs at most once, a skipped one is never retried, and a cancel succeeds only while the transfer has neither run nor been skipped nor been cancelled.

Merge links form chains that end at an open account, because only open accounts absorb others and an absorbed id never comes back. Following the chain from a transfer's original source or target finds the account that holds it now, which is what rewriting every pending transfer at merge time would have stored. When both ends lead to the same account, `canSend` rejects the transfer as a self-transfer, so it is skipped. In `cancelTransfer`, the holder of the source is always open, so comparing its id with `accountId` also rejects a missing or merged-away `accountId`.

### Complexity

- Time: O(log p) per scheduled transfer; O(log h) per balance change and per historical read; O(a log a) per ranking — each booking is added to the queue once and polled once, whether it runs, is skipped or was cancelled, and `settle` does no other work per call; the pending map is a `HashMap`. A balance change is one `TreeMap.put` and a historical read one `floorEntry`, both O(log h) on its red-black tree. `topSpenders` sorts the open accounts. Merge chains are followed in time proportional to their length, which is at most the number of merges.
- Space: O(a + h + p) — one object per account, one map entry per moment an account's balance changed, and one booking, one pending entry and at most one queue entry per scheduled transfer, cancelled ones included in the queue until they reach the head.

### Trade-offs

- A `MutableList` of (time, balance) entries makes each balance change O(1) amortized: append, or replace the last entry when its time equals the new one, which keeps the times strictly increasing. A read is then `binarySearchBy(time) { it.at }` and one step back when the time is not found. That beats the `TreeMap`'s O(log h) per change and uses less memory, at the price of index arithmetic that `floorEntry` names in one call.
- A list kept sorted by due time would also work: insert at the place `binarySearch` finds, O(p) for the shift, and take the earliest transfer from the front. `sortedWith` on every booking is simpler still and right on ties, since Kotlin's sort is stable, but it sorts the whole list again each time. The `PriorityQueue` makes booking and running O(log p) each.
- `PriorityQueue.remove(booking)` would cancel at once, but it is O(p): it searches the array before it can sift. Lazy deletion keeps cancel O(1) and costs only the memory of the cancelled entries until they surface.
- Rewriting every pending transfer at merge time, as the statement describes it, needs a scan of all pending transfers or an index from account to its pending transfers, kept up to date on every booking, run and cancel. The `merge` link gives the same answers with one property per merge. Path compression, pointing every account on a chain straight at its end, would make long chains cheap; with at most 1000 calls it is not worth the extra writes.
- Sorting all accounts in `topSpenders` is O(a log a). A bounded `PriorityQueue` of size `n` makes it O(a log n), and a `TreeSet` keyed by total and id, updated on every transfer, makes queries O(n) at the price of O(log a) per transfer.
- One package would do: the scheduler could sit next to `Bank` in `bank`. A package of its own documents that it knows nothing of accounts, and its tests build it without a bank; Kotlin leaves the boundary to convention, so the package is a signpost rather than a wall.

### Pitfalls and edge cases

- Run due transfers before the call's own logic, in every public method, reads included. The methods written for levels 1 and 2 predate scheduling and are the easiest to forget: a `transfer` at the exact due time may only succeed because the scheduled one ran first.
- A FIFO queue in booking order is wrong: a transfer booked later with a shorter delay must run first, and the order decides which of two transfers the source can still afford.
- Ties on the due time go in booking order, so the comparator needs the booking number as a second key. With `compareBy { it.transfer.due }` alone, `PriorityQueue` hands equal entries out in whatever order its sifting left them: three equal bookings come out first, third, second, because `poll` moves the last entry to the head and stops sifting it down among equals.
- Record a scheduled transfer at its due time, not at the time of the call that ran it, or `getBalance` between the two is wrong.
- Check funds when the transfer runs, not when it is booked. A skipped transfer stays skipped, even if the source receives money later, and it cannot be cancelled afterwards.
- Only the current source may cancel. The target cannot, and after a merge the merged-away id cannot either, while the account that absorbed it can.
- A transfer pending between two accounts that are then merged becomes a self-transfer; it must be skipped, and it must not add to the total sent.
- Transfer numbers count only successful bookings, across the whole bank.
- A merged-away account: `deposit`, `transfer`, `scheduleTransfer` and `cancelTransfer` treat it as missing, `topSpenders` leaves it out and `createAccount` cannot reuse its id, but `getBalance` before the merge still answers from its history.
- Ids compare as strings, character by character, so `b10` comes before `b9`. Parsing the digits off an id, or a "natural" sort, puts `b9` first.
- A balance of 0 is a real answer. `transfer` returns 0 when the source sends its whole balance, and `getBalance` returns 0 for an empty account, so absence travels as `null`, never as a 0 that means "not found".
- Project traps: `Bank` must stay a public class in `src/main/kotlin/bank/Bank.kt`, in package `bank`, with a constructor that takes no arguments, because the grader loads `bank.Bank` by name. Methods keep their names and their types: `Long` where the level says `Long`, since the grader finds a method by its name and parameter types and an `Int` parameter is a different method on the JVM. The tests in `src/test/kotlin/` compile as one source set, so a level's file stops every test from compiling until each method it calls exists. Keep the Gradle files as they are: they build offline with the workspace's JDK, Kotlin and libraries.

### Language notes

- Kotlin has no priority queue of its own; `java.util.PriorityQueue` is the JDK's binary heap. `compareBy<Booking> { it.transfer.due }.thenBy { it.number }` builds its comparator from selectors, and `thenBy` applies only when the first key ties. `peek` and `poll` return `null` on an empty queue, a platform type that `queue.peek()?.let { ... } == true` treats safely.
- The queue's iteration order is not its priority order: `for (booking in queue)` and `queue.toList()` walk the heap array as it lies. Only `poll` hands entries out in order.
- `BY_SPENDING = compareByDescending<Account> { it.sent }.thenBy { it.id }` is a total order, so `sortedWith` ranks equal totals the same way on every run, though a `HashMap`'s order is unspecified. `String.compareTo` compares UTF-16 code units, which for lowercase letters and digits is the byte order the statement asks for.
- Absence is `null`, and the type says so: `findOpen` returns `Account?`, `balanceAt` returns `Long?`, `pending` returns `ScheduledTransfer?`. `Bank` turns it into a sentinel with the elvis operator, `?: return FAILED`, which also ends the method early. `takeIf { it.isOpen }` keeps a lookup and its condition in one expression.
- `var balance = 0L` with `private set` lets `Bank` read a balance but leaves changing it to `Account`. Kotlin's `private` is per class, not per instance, so `send` may call `to.changeBalance(...)` on another account.
- `generateSequence(this) { it.merge?.into }.last()` walks the merge chain until the link is `null`; a `tailrec fun` would do the same.
- `ScheduledTransfer` is a `data class`: a value with `equals`, `hashCode`, `toString` and `copy` for free, which makes test failures readable. `Booking` and `Merge` are plain private classes, since nothing compares them.
- `buildList { ... }` collects the due transfers into a read-only `List` without a mutable list escaping the function.
- `internal` declarations are visible across the Gradle module, its test source set included, which is why the unit tests in `src/test/kotlin/` can build a `Ledger` or a `Scheduler` directly.
- A `Long` holds every amount and balance exactly: they stay below `2^53`. In a test, `assertEquals(70L, history.at(20))` needs the `L`: `assertEquals(70, ...)` compares an `Int` with a `Long?`, and a boxed `Int` never equals a boxed `Long`.
- The starter's methods throw `NotImplementedError` through `TODO(...)`, whose result type `Nothing` fits any return type. An exception escaping a method is graded as an error, so every failure the statement describes returns a sentinel instead.
