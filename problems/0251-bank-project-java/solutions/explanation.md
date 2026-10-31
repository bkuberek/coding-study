# Bank Project (Java): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | O(log p) per scheduled transfer; O(1) per balance change; O(log h) per historical read; O(a log a) per ranking | O(a + h + p) | default answer; each level adds a field, a class or a package |

Here `a` is the number of accounts, `h` the number of balance changes of one account, and `p` the number of scheduled transfers.

## How the project grows level by level

| Level | New requirement | What the code adds |
|-------|-----------------|--------------------|
| 1 | Accounts, deposits, transfers | `Account` owns its balance and the rules that move money (`deposit`, `canSend`, `send`); `Ledger` looks accounts up; `Bank` checks every failure before any change |
| 2 | Rank accounts by money sent | A `sent` field on `Account`, raised by `send`, and the comparator `BY_SPENDING` in `Bank` |
| 3 | Transfers booked with their own delay, cancellable | The package `bank.schedule`: the record `ScheduledTransfer`, and `TransferScheduler`, which numbers bookings and hands them out of a `PriorityQueue` by due time, then booking number; `Bank.settle` at the start of every public method |
| 4 | Merges and balances at a past time | `BalanceHistory` on every `Account`, the `Merge` record that `absorb` leaves on the absorbed account, and `holder`, which follows those links |

The starter's `Bank` keeps a plain `HashMap<String, Account>`, which is all level 1 needs. The reference moves that map into `Ledger` once merges arrive, because a merged-away account must stay findable by its id for `getBalance` while every other method treats it as missing, and that distinction belongs in one place. Nothing earlier is rewritten when a level opens: each level adds a field, a class or a package, and the earlier methods gain one line, the call to `settle`.

Time advances in exactly one place. Every public method starts with `settle(timestamp)`, which runs the scheduled transfers that fell due since the previous call, so every method, read-only ones such as `topSpenders` and `getBalance` included, sees the bank as it is at `timestamp`.

## Approach: reference (Accounts with balance histories and a due-time priority queue)

### Intuition

The bank is a registry of accounts, and each account owns its numbers in private fields: balance, total sent, history and merge link. The only thing that happens without a call asking for it is a scheduled transfer, which runs on its own clock. Ordering those transfers by due time, with the booking number as a tie-break, gives exactly the order a real clock would run them in, and draining every transfer due by `timestamp` before each call keeps the ledger as if that clock existed.

A scheduled transfer is an immutable value, the record `ScheduledTransfer(sourceId, targetId, amount, due)`. Whether it still waits to run is the scheduler's business: the scheduler keeps each one in a `Booking` record with its number and id, in the queue and in a map of pending bookings. Cancelling does not touch the queue: a `PriorityQueue` removes its head cheaply but any other element only after a linear search, so a cancel removes the booking from the pending map, and the scheduler drops a booking that is no longer pending when it reaches the head. This is lazy deletion: a cancelled entry costs one extra `poll` later instead of a search now.

Merges do not rewrite anything either. The absorbed account records where it went, and `holder` follows those links to the open account at the end. A booked transfer still names the ids it was booked with and finds its current source and target through `holder` when it runs or is cancelled.

### Algorithm

1. `settle(now)`: take from the scheduler every pending transfer due at or before `now`, in `(due, number)` order. For each, find the accounts that now hold its source and target; when they are different accounts and the source holds at least `amount`, move the money and add `amount` to the source's total sent, recording both changes at the transfer's due time. Otherwise the transfer is skipped. Every public method calls this first.
2. Level 1: `createAccount` rejects a known id, otherwise opens an account whose history starts with balance 0 at `timestamp`. `deposit` adds to an open account. `transfer` checks that both accounts are open and distinct and that the source can afford it; only then does it move the money and add `amount` to the source's total sent. The same `canSend` and `send` serve scheduled transfers.
3. Level 2: `topSpenders` streams the open accounts, sorts them by total sent, descending, then by id, and formats the first `n`.
4. Level 3: `scheduleTransfer` checks that both accounts are open and distinct, then hands `new ScheduledTransfer(sourceId, targetId, amount, timestamp + delay)` to the scheduler, which numbers it `transfer<k>`, with `k` the number of bookings so far plus one, and adds the booking to the queue and the pending map. The balance is not looked at. `cancelTransfer` finds the transfer while it is still pending, checks that the account holding its source now is `accountId`, and removes it from the pending map.
5. Level 4: `mergeAccounts` checks that both accounts are open and distinct, adds the other's balance and total sent to the first, and records on the other where it went and when. `getBalance` returns `-1` for an unknown id, before the account's creation or from its merge on, and otherwise the last history entry at or before `timeAt`.

### Design

| File under `src/main/java/bank/` | Responsible for |
|------|-----------------|
| `Bank.java` | The public API and the only class that knows the level rules as a whole: it settles due transfers first in every method, checks requests, delegates, and turns an empty `Optional` or a `false` into the sentinels `-1`, `""` and `false` |
| `Ledger.java` | Every account by id, open or merged away; opening, merging, `find`, `findOpen`, `openAccounts`, and `holderOf`, the open account that holds an id now |
| `Account.java` | Balance, total sent, history and merge link, and the rules that change them (`deposit`, `canSend`, `send`, `absorb`, `balanceAt`) |
| `BalanceHistory.java` | The time-ordered record of balances and its binary search |
| `schedule/ScheduledTransfer.java` | One booked transfer as an immutable record |
| `schedule/TransferScheduler.java` | Booking numbers, the run order in a `PriorityQueue`, and lazy cancellation |

The overlay also adds unit tests under `src/test/java/bank/`: `BalanceHistoryTest`, `LedgerTest` and `schedule/TransferSchedulerTest`, for history lookups, merge chains and lifetimes, and the run order and cancellation of bookings, the parts with boundaries that the level examples reach only through `Bank`.

Dependencies point one way: package `bank` imports `bank.schedule`, which imports nothing from the project. Inside `bank`, `Bank` uses `Ledger`, `Ledger` uses `Account`, and `Account` uses `BalanceHistory`; all four but `Bank` are package-private, so nothing outside `bank` can reach them. The sentinels live only in `Bank`: the inner classes return `Optional`, `OptionalLong` or `boolean`, so the grader's conventions never leak into the model. The scheduler never sees an account, so the same package would serve any kind of delayed job. Its public types are the API `bank` uses; its `Booking` record stays private to the scheduler.

### Correctness

Invariant: after `settle(t)`, every transfer with `due <= t` has run, been skipped or been dropped as cancelled, in `(due, number)` order, and none with `due > t` has. The queue hands its entries out in comparator order, and `takeDue` stops at the first head that is not due yet, so no due transfer is left behind and none runs early. Booking numbers are unique, so the comparator is a total order, and it matches the rule that transfers due at the same time run in booking order. A transfer is never due at the time of the call that books it, because `delay >= 1`. `takeDue` returns the whole batch before any of it runs, which changes nothing: running a transfer never books or cancels another.

Each history entry is written at the time of its change: the call's timestamp, or the due time for a scheduled transfer. A transfer due at `d` runs during the first call at or after `d`, no earlier call had a timestamp at or after `d`, and the transfers that run before it in the same `settle` are due no later than `d`. The history therefore stays in time order and a binary search finds the balance at any moment. When several changes share a time (two transfers due at `t` and the call at `t`), the search finds the first entry after the moment, so it lands after all of them and returns the balance after the last one. The first entry is the account's creation, so a moment before it finds nothing.

A booking leaves the pending map exactly once: by a cancel, or by `takeDue` when it is handed out to run or be skipped. So a transfer runs at most once, a skipped one is never retried, and a cancel succeeds only while the transfer has neither run nor been skipped nor been cancelled.

Merge links form chains that end at an open account, because only open accounts absorb others and an absorbed id never comes back. Following the chain from a transfer's original source or target finds the account that holds it now, which is what rewriting every pending transfer at merge time would have stored. When both ends lead to the same account, `canSend` rejects the transfer as a self-transfer, so it is skipped. In `cancelTransfer`, the holder of the source is always open, so comparing its id with `accountId` also rejects a missing or merged-away `accountId`.

### Complexity

- Time: O(log p) per scheduled transfer; O(1) per balance change; O(log h) per historical read; O(a log a) per ranking — each booking is added to the queue once and polled once, whether it runs, is skipped or was cancelled, and `settle` does no other work per call. A balance change appends one entry to an `ArrayList`, amortized O(1); `getBalance` is one binary search; `topSpenders` sorts the open accounts. Merge chains are followed in time proportional to their length, which is at most the number of merges.
- Space: O(a + h + p) — one object per account, one history entry per balance change, and one booking per scheduled transfer, in the pending map until it leaves and in the queue until it reaches the head, cancelled ones included.

### Trade-offs

- A `TreeMap<Long, List<ScheduledTransfer>>` keyed by due time would also work: each list keeps booking order, and `headMap(now, true)` holds everything due. It is O(log p) too and needs no booking number, but it allocates a list per due time and removing a cancelled transfer means finding it in its list. Re-sorting an `ArrayList` with `List.sort` after every booking is simplest and right on ties, because `List.sort` is a stable merge sort, but it sorts the whole list again each time.
- Removing a cancelled transfer from the queue right away is `queue.remove(booking)`, O(p): it scans the backing array, using `equals`, which a record defines over all its fields. Lazy deletion keeps cancellation O(1) and costs only the memory of the cancelled entries until they surface.
- Rewriting every pending transfer at merge time, as the statement describes it, needs a scan of all pending transfers or an index from account to its pending transfers, kept up to date on every booking, run and cancel. The `Merge` link gives the same answers with one field per merge. Path compression, pointing every account on a chain straight at its end, would make long chains cheap; with at most 1000 calls it is not worth the extra writes.
- Sorting all accounts in `topSpenders` is O(a log a). A bounded `PriorityQueue` of size `n` makes it O(a log n), and a `TreeSet` ordered by total and id, updated on every transfer by removing and re-adding the account, makes queries O(n) at the price of O(log a) per transfer.
- One package would do: `ScheduledTransfer` and `TransferScheduler` could sit in `bank` next to the rest. A package of its own makes the boundary visible: `bank.schedule` cannot see the package-private `Account`, so the run order and cancellation rules are testable without a bank, and `bank` uses only what the scheduler declares public.

### Pitfalls and edge cases

- Run due transfers before the call's own logic, in every public method, reads included. The methods written for levels 1 and 2 predate scheduling and are the easiest to forget: a `transfer` at the exact due time may only succeed because the scheduled one ran first.
- A FIFO queue in booking order, such as an `ArrayDeque`, is wrong: a transfer booked later with a shorter delay must run first, and the order decides which of two transfers the source can still afford.
- Ties on the due time go in booking order, so the comparator needs the booking number as a second key. With `Comparator.comparingLong(Booking::due)` alone, equal entries come out in whatever order the heap's swaps left them: a `PriorityQueue` polls three equal additions as first, third, second, because `poll` moves the last element to the head and sifts it down, which stops at once among equals.
- Record a scheduled transfer at its due time, not at the time of the call that ran it, or `getBalance` between the two is wrong.
- Check funds when the transfer runs, not when it is booked. A skipped transfer stays skipped, even if the source receives money later, and it cannot be cancelled afterwards.
- Only the current source may cancel. The target cannot, and after a merge the merged-away id cannot either, while the account that absorbed it can.
- A transfer pending between two accounts that are then merged becomes a self-transfer; it must be skipped, and it must not add to the total sent.
- Transfer numbers count only successful bookings, across the whole bank.
- A merged-away account: `deposit`, `transfer`, `scheduleTransfer` and `cancelTransfer` treat it as missing, `topSpenders` leaves it out and `createAccount` cannot reuse its id, but `getBalance` before the merge still answers from its history.
- Ids compare as strings, character by character, so `b10` comes before `b9`. Parsing the digits off an id, or a "natural" sort, puts `b9` first.
- Compare ids with `equals`, never `==`. The level tests pass string literals, which the JVM interns, so `==` often holds there; the grader decodes every id from JSON into a new `String`, and `==` between two of those is false.
- A balance of 0 is a real answer. `transfer` returns 0 when the source sends its whole balance, and `getBalance` returns 0 for an empty account, so absence travels as an empty `Optional`, never as a 0 that means "not found".
- Amounts reach `10^10`, beyond an `int`: keep balances and totals in `long` fields. An `int` field compiles, since `balance += amount` narrows silently, and wraps around past `2^31 - 1`.
- Project traps: `bank.Bank` must stay in `src/main/java/bank/Bank.java`, public, with a public constructor that takes no arguments, because the grader loads it by that name. Methods must stay public and keep their types: `long` where the level says `long`, so an `int` parameter is a signature mismatch, and `List<String>` for `topSpenders`. A level's test class calls methods you have not written yet, and Gradle compiles every test class before it runs one, so add each new method, even as a stub, before expecting any test to run. Keep the Gradle files as they are: they build offline with what `cstudy doctor --fix` cached.

### Language notes

- `java.util.PriorityQueue` is a binary min-heap ordered by the `Comparator` given to its constructor. `peek` and `poll` see the head, the smallest element; iterating the queue, or streaming it, visits the backing array in heap order, not in sorted order, so only repeated `poll` hands elements out sorted.
- The comparator reads `Comparator.comparingLong(Booking::due).thenComparingLong(Booking::number)`: `thenComparingLong` falls through to the booking number exactly when the due times are equal, and `comparingLong` compares with `Long.compare`. A hand-written `(a, b) -> (int) (a.due() - b.due())` can overflow and order two dues the wrong way.
- `BY_SPENDING` is `Comparator.comparingLong(Account::sent).reversed().thenComparing(Account::id)`. `reversed` applies to everything before it, so it sits before `thenComparing`, and the ids still sort ascending. `String.compareTo` compares UTF-16 code units, which for lowercase letters and digits is byte order.
- Records hold the immutable values: `ScheduledTransfer`, the scheduler's private `Booking`, the history's `Change` and the account's `Merge`. A record gets its constructor, accessors (`transfer.due()`, not `getDue()`), `equals` and `hashCode` from its components, which is what lets `TransferSchedulerTest` compare lists of transfers with `assertEquals`. A nested record is implicitly `static`, so `Merge` holds the account it points to as an ordinary field.
- `Optional<Account>` and `OptionalLong` say "maybe absent" in the type, where a `null` would not. `OptionalLong` avoids boxing the balance into a `Long`. `Bank` turns them into sentinels with `orElse(FAILED)`, the only place the grader's `-1` appears.
- `BalanceHistory` writes its own binary search for the first change after a moment. `Collections.binarySearch` would find some change at the moment, with no guarantee which one when several share it, which is the wrong end when two transfers and a call all land at one time.
- `Ledger.open` is `accounts.putIfAbsent(id, account) == null`: one lookup that adds the account only when the id is free and reports whether it did. `put` would replace the existing account and its balance.
- `topSpenders` is one stream: `sorted(BY_SPENDING).limit(n).map(...).toList()`. `limit` makes asking for more accounts than exist safe, where `subList(0, n)` would throw. `Stream.toList()`, from Java 16, returns an unmodifiable list.
- Java's `HashMap` has no defined iteration order, so `openAccounts` streams the accounts in an order that depends on the ids' hash codes. `topSpenders` is deterministic only because `BY_SPENDING` is a total order: a comparison by total alone would leave equal totals in that arbitrary order.
