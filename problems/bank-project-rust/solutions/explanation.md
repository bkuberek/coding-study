# Bank Project (Rust): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | O(log p) per scheduled transfer; O(1) per balance change; O(log h) per historical read; O(a log a) per ranking | O(a + h + p) | default answer; each level adds a field, a type or a module |

Here `a` is the number of accounts, `h` the number of balance changes of one account, and `p` the number of scheduled transfers.

## How the project grows level by level

| Level | New requirement | What the code adds |
|-------|-----------------|--------------------|
| 1 | Accounts, deposits, transfers | `Account` owns its balance and the rules that move money (`credit`, `debit`); `Ledger` owns every account and checks a send; `Bank` checks every failure before any change |
| 2 | Rank accounts by money sent | A `sent` field on `Account`, raised by `debit`, and one sort key in `Bank::top_spenders` |
| 3 | Transfers booked with their own delay, cancellable | The module `schedule`: a generic `Scheduler<J>` that numbers bookings with a `Ticket` and hands them out of a `BinaryHeap` by due time, then ticket; `Bank::settle` at the start of every public method |
| 4 | Merges and balances at a past time | `History` on every `Account`, the closing time an account keeps once merged away, and the `merged_into` links that `Ledger::holder` follows |

The starter's `Bank` keeps a plain `HashMap<String, Account>`, which is all level 1 needs. The reference moves the accounts into `Ledger` once merges arrive, because a merged-away account must stay findable by its id for `get_balance` while every other method treats it as missing, and that distinction belongs in one place. Nothing earlier is rewritten when a level opens: each level adds a field, a type or a module, and the earlier methods gain one line, the call to `settle`.

Time advances in exactly one place. Every public method starts with `self.settle(timestamp)`, which runs the scheduled transfers that fell due since the previous call, so every method, read-only ones such as `top_spenders` and `get_balance` included, sees the bank as it is at `timestamp`.

## Approach: reference (An arena of accounts with balance histories and a due-time binary heap)

### Intuition

The bank is a registry of accounts, and each account owns its numbers in private fields: balance, total sent, history and the time it was closed. The only thing that happens without a call asking for it is a scheduled transfer, which runs on its own clock. Ordering those transfers by due time, with the booking number as a tie-break, gives exactly the order a real clock would run them in, and draining every transfer due by `timestamp` before each call keeps the ledger as if that clock existed.

Accounts live in one `Vec`, an arena, and everything else names them by `AccountKey`, a copyable index into it. A booked transfer holds two keys and an amount, and a merge link maps one key to another. Nothing holds a reference to an account, so nothing needs `Rc<RefCell<...>>`: only `Ledger` owns accounts, and it lends one out for the length of a call. An account is never removed from the arena, so a key stays valid after its account is merged away.

The scheduler keeps each booking twice: a small `Slot` of due time and ticket in the heap, which decides the run order, and the job itself in a map of pending bookings, keyed by ticket. Cancelling removes the job from the map and leaves the slot in the heap: a `BinaryHeap` removes its top cheaply but any other element only by rebuilding, so `pop_due` drops a slot whose job is no longer pending when it reaches the top. This is lazy deletion: a cancelled entry costs one extra `pop` later instead of a search now.

Merges do not rewrite anything either. The ledger records where the absorbed account went, and `holder` follows those links to the open account at the end. A booked transfer still names the accounts it was booked with and finds its current source and target through `holder` when it runs or is cancelled.

### Algorithm

1. `settle(now)`: take from the scheduler, one at a time, every pending transfer due at or before `now`, in `(due, ticket)` order. For each, find the accounts that now hold its source and target; `Ledger::send` moves the money and adds `amount` to the source's total sent, recording both changes at the transfer's due time, unless they are the same account or the source holds less than `amount`, in which case the transfer is skipped. Every public method calls this first.
2. Level 1: `create_account` rejects an id the ledger has ever seen, otherwise opens an account whose history starts with balance 0 at `timestamp`. `deposit` adds to an open account. `transfer` finds both accounts open and distinct, and `Ledger::send` checks the funds before it changes anything. The same `send` serves scheduled transfers.
3. Level 2: `top_spenders` collects references to the open accounts, sorts them by the key `(Reverse(sent), id)`, and formats the first `n`.
4. Level 3: `schedule_transfer` finds both accounts open and distinct, then books `BookedTransfer { source, target, amount }` due at `timestamp + delay`; the scheduler numbers it with the next `Ticket`, and `Bank` writes the id `transfer<k>`. The balance is not looked at. `cancel_transfer` reads the ticket back from the id, finds the transfer while it is still pending, checks that the open account named `account_id` is the one holding its source now, and removes it from the pending map.
5. Level 4: `merge_accounts` finds both accounts open and distinct; `Ledger::merge` closes the absorbed account, adds its balance and total sent to the kept one, and links the absorbed key to the kept key. `get_balance` returns `-1` for an unknown id, and otherwise asks the account, which answers `None` before its creation and from its closing on, and the last history entry at or before `time_at` in between.

### Design

| File under `src/` | Responsible for |
|------|-----------------|
| `lib.rs` | The crate root: declares the modules, all private, and re-exports `Bank`, the crate's whole public API |
| `bank.rs` | The public API and the only type that knows the level rules as a whole: it settles due transfers first in every method, checks requests, delegates, and turns a `None` or a `false` into the sentinels `-1`, `""` and `false`; it also writes and reads the transfer ids |
| `ledger.rs` | Every account in an arena, by `AccountKey`, and by id, open or merged away; opening, `find`, `find_open`, `open_accounts`, `deposit`, `send`, `merge`, and `holder`, the open account that holds a key now |
| `account.rs` | Balance, total sent, history and closing time, and the rules that change them (`credit`, `debit`, `close`, `absorb`, `balance_at`) |
| `history.rs` | The time-ordered record of balances and its binary search |
| `schedule.rs` | `Scheduler<J>`: booking numbers (`Ticket`), the run order in a `BinaryHeap`, and lazy cancellation, for any kind of job |

The unit tests sit next to the code they test, in a `#[cfg(test)] mod tests` at the end of `history.rs`, `schedule.rs`, `ledger.rs` and `bank.rs`: history lookups, the run order and cancellation of bookings, merge chains and lifetimes, and the reading of transfer ids, the parts with boundaries that the level examples reach only through `Bank`. A unit test is compiled into the crate, so it reaches private items, such as `parse_transfer_id`, that the integration tests under `tests/` cannot see.

Dependencies point one way: `bank` uses `ledger` and `schedule`, and reads the accounts that `ledger` lends it through `account`'s getters; `ledger` uses `account`, and `account` uses `history`. `schedule` uses nothing from the crate: it never sees an account, so the same module would serve any kind of delayed job, and its tests book plain `&str` jobs. The sentinels live only in `bank.rs`: the inner types return `Option<i64>`, `Option<AccountKey>` or `bool`, so the grader's conventions never leak into the model. Every module is private, so outside the crate only `Bank` exists; inside it, `AccountKey` keeps its index private to `ledger`, so no other module can make up a key.

### Correctness

Invariant: after `settle(t)`, every transfer with `due <= t` has run, been skipped or been dropped as cancelled, in `(due, ticket)` order, and none with `due > t` has. The heap hands its slots out greatest first, and `Reverse` turns that into smallest first; `Slot` derives `Ord` from its fields in declaration order, due time then ticket, and `pop_due` stops at the first top that is not due yet, so no due transfer is left behind and none runs early. Tickets are unique, so the order is total, and it matches the rule that transfers due at the same time run in booking order. A transfer is never due at the time of the call that books it, because `delay >= 1`. `settle` takes one transfer at a time and runs it before taking the next; running a transfer never books or cancels another, so taking the whole batch first would give the same result.

Each history entry is written at the time of its change: the call's timestamp, or the due time for a scheduled transfer. A transfer due at `d` runs during the first call at or after `d`, no earlier call had a timestamp at or after `d`, and the transfers that run before it in the same `settle` are due no later than `d`. The history therefore stays in time order and a binary search finds the balance at any moment. `partition_point` counts the entries at or before the moment, so when several changes share a time (two transfers due at `t` and the call at `t`), the last entry it counts is the last of them. The first entry is the account's creation, so a moment before it counts none.

A booking leaves the pending map exactly once: by a cancel, or by `pop_due` when it is handed out to run or be skipped. So a transfer runs at most once, a skipped one is never retried, and a cancel succeeds only while the transfer has neither run nor been skipped nor been cancelled.

Merge links form chains that end at an open account, because only open accounts absorb others and an absorbed key never opens again: `Ledger::open` refuses every id it has seen. Following the chain from a transfer's original source or target finds the account that holds it now, which is what rewriting every pending transfer at merge time would have stored. When both ends lead to the same account, `send` rejects the transfer as a self-transfer, so it is skipped. In `cancel_transfer`, the holder of the source is always open, so comparing it with `find_open(account_id)` also rejects a missing or merged-away `account_id`.

### Complexity

- Time: O(log p) per scheduled transfer; O(1) per balance change; O(log h) per historical read; O(a log a) per ranking — each slot is pushed once and popped once, whether its transfer runs, is skipped or was cancelled, and `settle` does no other work per call. A balance change pushes one entry onto a `Vec`, amortized O(1), and an account lookup is one `HashMap` probe; `get_balance` is one binary search; `top_spenders` sorts the open accounts. Merge chains are followed in time proportional to their length, which is at most the number of merges.
- Space: O(a + h + p) — one arena entry and one id per account, one history entry per balance change, and one slot and one pending job per scheduled transfer, the job until it leaves the map and the slot until it reaches the top, cancelled ones included.

### Trade-offs

- A `BTreeMap<(i64, Ticket), BookedTransfer>` would also work: its keys sort by due time, then ticket, `pop_first` takes the next transfer, and a cancel removes the entry at once, with no lazy deletion and no second map. It is O(log p) per operation too, but `cancel_transfer` would need the due time to build the key, so the ticket alone would no longer find the booking. Sorting a `Vec` after every booking with the stable `sort_by_key` is simplest and right on ties, but it sorts the whole list again each time.
- Removing a cancelled slot from the heap right away is `queue.retain(|Reverse(slot)| slot.ticket != ticket)`, O(p): it rebuilds the heap. Lazy deletion keeps cancellation O(1) and costs only the memory of the cancelled slots until they surface.
- An arena with keys replaces references between accounts. `HashMap<String, Account>` with merge links stored as ids works too, at the price of a hash and a `String` clone per link and per booked transfer. `Rc<RefCell<Account>>` would let a transfer point at its accounts, but a borrow conflict then shows up at run time as a panic instead of at compile time, and a transfer between two accounts has to borrow both cells at once.
- Rewriting every pending transfer at merge time, as the statement describes it, needs a scan of all pending transfers or an index from account to its pending transfers, kept up to date on every booking, run and cancel. The `merged_into` link gives the same answers with one map entry per merge. Path compression, pointing every key on a chain straight at its end, would make long chains cheap; with at most 1000 calls it is not worth the extra writes, and it would need `&mut self` in `holder`.
- Sorting all accounts in `top_spenders` is O(a log a). `select_nth_unstable_by_key` moves the first `n` to the front in O(a), after which only those `n` need sorting: O(a + n log n). A `BTreeSet<(Reverse<i64>, String)>` updated on every transfer makes queries O(n) at the price of O(log a) per transfer.
- A generic `Scheduler<J>` costs one type parameter and a hand-written `Default`. A scheduler of `BookedTransfer` only would be shorter, but then its tests need accounts, and it could reach into the ledger.

### Pitfalls and edge cases

- Run due transfers before the call's own logic, in every public method, reads included. The methods written for levels 1 and 2 predate scheduling and are the easiest to forget: a `transfer` at the exact due time may only succeed because the scheduled one ran first.
- `BinaryHeap` is a max-heap. Pushing `Slot`s without `Reverse` hands out the transfer due last first, and a FIFO queue in booking order, such as a `VecDeque`, is wrong as well: a transfer booked later with a shorter delay must run first, and the order decides which of two transfers the source can still afford.
- Ties on the due time go in booking order, so the order needs the ticket as a second key. An `Ord` that compares the due time alone leaves equal entries in whatever order the heap's swaps left them: three transfers due together, pushed alone, happen to come out in booking order, but after a fourth booking that falls due before them, they come out as third, first, second. With a derived `Ord`, the order of the fields is the order of the keys, so declaring `ticket` before `due` runs everything in booking order.
- Record a scheduled transfer at its due time, not at the time of the call that ran it, or `get_balance` between the two is wrong.
- Check funds when the transfer runs, not when it is booked. A skipped transfer stays skipped, even if the source receives money later, and it cannot be cancelled afterwards.
- Only the current source may cancel. The target cannot, and after a merge the merged-away id cannot either, while the account that absorbed it can.
- A transfer pending between two accounts that are then merged becomes a self-transfer; it must be skipped, and it must not add to the total sent.
- Transfer numbers count only successful bookings, across the whole bank, starting at 1.
- A merged-away account: `deposit`, `transfer`, `schedule_transfer`, `cancel_transfer` and `merge_accounts` treat it as missing, `top_spenders` leaves it out and `create_account` cannot reuse its id, but `get_balance` before the merge still answers from its history.
- Ids compare as strings, byte by byte, so `b10` comes before `b9`. Parsing the digits off an id, or a "natural" sort, puts `b9` first.
- A balance of 0 is a real answer. `transfer` returns 0 when the source sends its whole balance, and `get_balance` returns 0 for an empty account, so absence travels as `None`, never as a 0 that means "not found".
- Amounts reach `10^10`, beyond an `i32`: keep balances and totals in `i64`. A cast such as `as i32` compiles and silently wraps past `2^31 - 1`.
- Project traps: the crate must stay named `bank` and export `Bank` at its root, because the grader depends on it by that name. Methods must stay `pub`, take `&mut self` and keep their types: `i64` where the level says so, so an `i32` or `u64` parameter is a signature mismatch, `i32` for `n`, and `Vec<String>` for `top_spenders`. A level's test file calls methods you have not written yet, so add each new method, even with a `todo!()` body, before expecting `cargo test` to build. Keep `Cargo.toml` and `.cargo/config.toml` as they are: they build offline with the crates the workspace ships.

### Language notes

- `BinaryHeap<T>` pops its greatest element. `std::cmp::Reverse` is a wrapper whose `Ord` is the inner value's reversed, so `BinaryHeap<Reverse<Slot>>` pops the smallest slot; `while let Some(&Reverse(slot)) = self.queue.peek()` destructures the wrapper and copies the `Copy` slot out of the borrow, which ends the borrow before `pop`. Iterating a heap, or `into_vec`, visits its backing array in heap order, not in sorted order; only repeated `pop` (or `into_sorted_vec`) hands elements out sorted.
- `#[derive(PartialOrd, Ord)]` on a struct compares its fields lexicographically, in the order they are declared, the same way tuples compare. So `Slot { due, ticket }` sorts by due time, then ticket, and swapping the two field declarations changes the run order without any other edit. A hand-written `Ord` must agree with `PartialEq`, `Eq` and `PartialOrd`, which deriving all four guarantees.
- On equal keys, `BinaryHeap::pop` moves the last element to the top and sifts it down to the bottom, choosing the right child when two children compare equal, then sifts it up; the order of equal elements depends on that history of pushes and pops, not on insertion order. That is why the ticket is part of the key and not left to the heap.
- `#[derive(Default)]` on a generic struct adds a `J: Default` bound to the generated `impl`, even when no field of type `J` needs it. `Scheduler<J>` therefore implements `Default` by hand, so that `Bank` can `#[derive(Default)]` with a `Scheduler<BookedTransfer>` field. Clippy's `new_without_default` asks a public type with a no-argument `new` to implement `Default`, so `Bank::new` is `Self::default()`.
- `slice::partition_point` returns the index of the first element for which the predicate is false, on a slice partitioned by it: with `change.at <= moment`, the number of changes at or before the moment. `checked_sub(1)?` turns "no change yet" into `None` without a special case. `binary_search_by_key` would find some entry at the moment, with no guarantee which one when several share it.
- `sort_unstable_by_key(|&account| (Reverse(account.sent()), account.id()))` orders by total, largest first, then by id: `Reverse` flips only the first part of the tuple. The key may hold the `&str` of the id because it borrows the account, which outlives the sort, and not the vector's slot. The keys are unique, because ids are, so the unstable sort has no equal elements to reorder and is the cheaper choice.
- `HashMap` iterates in an order that its random hasher seed picks anew in every process, so a ranking that relied on map order alone would change from run to run. The arena iterates in creation order, which is deterministic but still not id order: only the full sort key makes `top_spenders` correct.
- Two `&mut` borrows of one `Vec` at once do not compile. `Ledger::send` and `Ledger::merge` change the two accounts one after the other instead, through `account_mut`; the slice method `get_disjoint_mut` would hand out both at once, but it is newer than the crate's `rust-version`, 1.80, and clippy's `incompatible_msrv` would flag it. `HashMap::entry` in `Ledger::open` looks the id up once, and inserts only into a vacant entry; `insert` would replace an existing account.
- `str::parse::<u64>` accepts a leading `+` and leading zeros, so `transfer+3` and `transfer03` would both read as ticket 3. `parse_transfer_id` therefore requires the number to print back as the same digits.
- Methods take owned `String` parameters, as the grader's signature declares them; `Bank` borrows them as `&str` (`&account_id`) for lookups and moves `account_id` into the ledger only in `create_account`, which keeps it.
- `let ... else` ends a method early on a missing account without nesting: `let Some(account) = self.ledger.find_open(&account_id) else { return FAILED; };`. `bool::then_some` and `Option::filter` express "this value, if the condition holds" in `open_pair` and `find_open`.
