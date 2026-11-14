# Bank Project (Python): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | O(log p) per scheduled transfer; O(1) per balance change; O(log h) per historical read; O(a log a) per ranking | O(a + h + p) | default answer; each level adds a field, a class or a module |

Here `a` is the number of accounts, `h` the number of balance changes of one account, and `p` the number of scheduled transfers.

## How the project grows level by level

| Level | New requirement | What the code adds |
|-------|-----------------|--------------------|
| 1 | Accounts, deposits, transfers | `Account` in `bank/models.py` owns its balance and the rules that move money (`deposit`, `can_send`, `send`); `Accounts` in `bank/accounts.py` looks accounts up; `Bank` checks every failure before any change |
| 2 | Rank accounts by money sent | An `outgoing` counter on `Account`, raised by `send`, and a sort key in `bank/bank.py` |
| 3 | Transfers booked with their own delay, cancellable | `bank/scheduler.py`: `ScheduledTransfer` with a `pending` flag, and `TransferScheduler`, a min-heap keyed by `(due, number)`; `Bank._settle` at the start of every public method |
| 4 | Merges and balances at a past time | `BalanceHistory` on every `Account`, `merged_away_at`, and `Accounts.merge` with a `merged_into` link that `holder_of` follows |

The starter's `Bank` keeps a plain `dict[str, Account]`, which is all level 1 needs. The reference moves that dict into `Accounts` once merges arrive, because "which account holds this id now" becomes a question of its own, asked by both cancelling and running transfers. Nothing earlier is rewritten when a level opens: each level adds a field, a class or a module, and the earlier methods gain one line, the call to `_settle`.

Time advances in exactly one place. Every public method starts with `_settle(timestamp)`, which runs the scheduled transfers that fell due since the previous call, so every method, read-only ones such as `top_spenders` and `get_balance` included, sees the bank as it is at `timestamp`.

## Approach: reference (Accounts with balance histories and a due-time heap)

### Intuition

The bank is a registry of account objects, and each account owns its numbers: balance, total sent, lifetime and history. The only thing that happens without a call asking for it is a scheduled transfer, which runs on its own clock. Ordering those transfers by due time, with the booking number as a tie-break, gives exactly the order a real clock would run them in, and draining every transfer due by `timestamp` before each call keeps the ledger as if that clock existed.

Cancelling does not touch the heap. A heap can only remove its top cheaply, so a cancel clears the transfer's `pending` flag, and the scheduler drops a transfer that is no longer pending when it reaches the top. This is lazy deletion: a cancelled entry costs one extra pop later instead of a search now.

Merges do not rewrite anything either. A merge records where the absorbed id went, and a booked transfer finds its current source and target by following those records when it runs or is cancelled.

### Algorithm

1. `_settle(timestamp)`: take from the scheduler every pending transfer due at or before `timestamp`, in `(due, number)` order. For each, find the accounts that now hold its source and target through `holder_of`; when they are different accounts and the source holds at least `amount`, move the money and add `amount` to the source's `outgoing`, recording both changes at the transfer's due time. Otherwise the transfer is skipped. Every public method calls this first.
2. Level 1: `create_account` rejects a known id, otherwise opens an account whose history starts with `(timestamp, 0)`. `deposit` adds to an open account. `transfer` checks that both accounts are open, distinct and that the source can afford it; only then does it move the money and add `amount` to the source's `outgoing`. The same `can_send` and `send` serve scheduled transfers.
3. Level 2: `top_spenders` sorts the open accounts by `(-outgoing, account_id)` and formats the first `n`.
4. Level 3: `schedule_transfer` checks that both accounts are open and distinct, then hands a `ScheduledTransfer` with `due = timestamp + delay` to the scheduler, which numbers it `transfer<k>`, with `k` the number of bookings so far plus one, and pushes it on the heap. The balance is not looked at. `cancel_transfer` finds the transfer while it is still pending, checks that the account holding its source now is `account_id`, and clears `pending`.
5. Level 4: `merge_accounts` checks that both accounts are open and distinct, adds the other's balance and `outgoing` to the first, sets the other's `merged_away_at` and records `merged_into[other_id] = account_id`. `get_balance` returns `-1` outside `[created_at, merged_away_at)` and otherwise the last history entry at or before `time_at`.

### Design

| File | Responsible for |
|------|-----------------|
| `bank/bank.py` | `Bank`, the public API and the only module that knows the level rules as a whole: it settles due transfers first in every method, checks requests, delegates, and turns a missing result into the sentinels `-1`, `""` and `False` |
| `bank/accounts.py` | `Accounts`: every account by id, open or merged away; opening, merging, and `holder_of`, which follows merges to the open account that holds an id now |
| `bank/models.py` | `Account`: balance, total sent and lifetime, and the rules that change them (`deposit`, `can_send`, `send`, `absorb`); `BalanceHistory`: the time-ordered record of balances and its floor search |
| `bank/scheduler.py` | `ScheduledTransfer`, one booking, and `TransferScheduler`: booking numbers, the due-time heap and lazy cancellation |
| `tests/test_scheduler.py`, `tests/test_models.py` | Unit tests for run order and history lookups, the parts with boundaries that the level examples reach only through `Bank` |

Dependencies point one way: `bank` uses `accounts`, `scheduler` and `models`, `accounts` uses `models`, and `models` and `scheduler` import nothing from the project. The sentinels live only in `bank/bank.py`: the inner modules return `None` for "nothing here", so the grader's conventions never leak into the model. `ScheduledTransfer` keeps the ids it was booked with, and the scheduler never sees an account, so the same scheduler would serve any kind of delayed job.

### Correctness

Invariant: after `_settle(t)`, every transfer with `due <= t` has run, been skipped or been dropped as cancelled, in `(due, number)` order, and none with `due > t` has. The heap returns its entries in that order, and `take_due` stops at the first entry that is not due yet, so no due transfer is left behind and none runs early. Booking numbers are unique, so the order is total, and it matches the rule that transfers due at the same time run in booking order. A transfer is never due at the time of the call that books it, because `delay >= 1`. `take_due` returns the whole batch before any of it runs, which changes nothing: running a transfer never books or cancels another.

Each history entry is written at the time of its change: the call's timestamp, or the due time for a scheduled transfer. A transfer due at `d` runs during the first call at or after `d`, no earlier call had a timestamp at or after `d`, and the transfers that run before it in the same `_settle` are due no later than `d`. The history therefore stays in time order and a floor search finds the balance at any moment. When several changes share a time (two transfers due at `t` and the call at `t`), `bisect_right` lands after all of them, so the search returns the balance after the last one.

`pending` is cleared exactly once: by a cancel, or by `take_due` when the transfer is handed out to run or be skipped. So a transfer runs at most once, a skipped one is never retried, and a cancel succeeds only while the transfer has neither run nor been skipped nor been cancelled.

`merged_into` forms chains that end at an open account, because only open accounts absorb others and an absorbed id never comes back. Following the chain from a transfer's original source or target finds the account that holds it now, which is what rewriting every pending transfer at merge time would have stored. When both ends lead to the same account, `can_send` rejects the transfer as a self-transfer, so it is skipped. In `cancel_transfer`, the holder of the source is always open, so comparing its id with `account_id` also rejects a missing or merged-away `account_id`.

### Complexity

- Time: O(log p) per scheduled transfer; O(1) per balance change; O(log h) per historical read; O(a log a) per ranking — each transfer is pushed on the heap once and popped once, whether it runs, is skipped or was cancelled, and `_settle` does no other work per call. A balance change appends to two lists; `get_balance` is one `bisect_right`; `top_spenders` sorts the open accounts. Merge chains are followed in time proportional to their length, which is at most the number of merges.
- Space: O(a + h + p) — one object per account, one history entry per balance change, and one record and at most one heap entry per scheduled transfer, cancelled ones included until they reach the top.

### Trade-offs

- A list kept sorted by `(due, number)` would also work: inserting costs O(p) for the shift, running the earliest transfer is a pop from one end, and a cancel can remove the entry after a binary search. The heap makes booking and running O(log p) each and leaves cancelled entries in place; with 1000 calls either is fast, but only the heap keeps booking logarithmic as the number of pending transfers grows.
- Removing a cancelled transfer from the heap right away needs an indexed heap that tracks each entry's position, or a balanced tree keyed by `(due, number)`. Lazy deletion keeps `heapq` and costs only the memory of the cancelled entries until they surface.
- Rewriting every pending transfer at merge time, as the statement describes it, needs a scan of all pending transfers or an index from account to its pending transfers, kept up to date on every booking, run and cancel. The `merged_into` link gives the same answers with one map entry per merge. Path compression in `holder_of`, pointing every id on a chain straight at its end, would make long chains cheap; with at most 1000 calls it is not worth the extra writes.
- Sorting all accounts in `top_spenders` is O(a log a). `heapq.nsmallest(n, accounts, key=...)` makes it O(a log n), and an ordered structure keyed by `(-outgoing, account_id)`, updated on every transfer, makes queries O(n) at the price of O(log a) per transfer.
- One module would do: the single-file reference of Scheduled Transfers Bank passes every case of this problem in 155 lines, against about 280 here across four modules. The split costs imports, docstrings and a few delegating methods, and pays back when a level opens: level 3 is a new module plus one `_settle` line in each existing method, and level 4 adds `BalanceHistory` and an account's lifetime to `models.py` and the merge bookkeeping to `accounts.py`, while `Bank` only gains its two new methods.

### Pitfalls and edge cases

- Run due transfers before the call's own logic, in every public method, reads included. The methods written for levels 1 and 2 predate scheduling and are the easiest to forget: a `transfer` at the exact due time may only succeed because the scheduled one ran first.
- A FIFO queue in booking order is wrong: a transfer booked later with a shorter delay must run first, and the order decides which of two transfers the source can still afford.
- Ties on the due time go in booking order. A heap of `(due, transfer)` alone is not stable and, in Python, compares the transfer objects on a tie and fails, so the booking number has to be part of the key.
- Record a scheduled transfer at its due time, not at the time of the call that ran it, or `get_balance` between the two is wrong.
- Check funds when the transfer runs, not when it is booked. A skipped transfer stays skipped, even if the source receives money later, and it cannot be cancelled afterwards.
- Only the current source may cancel. The target cannot, and after a merge the merged-away id cannot either, while the account that absorbed it can.
- A transfer pending between two accounts that are then merged becomes a self-transfer; it must be skipped, and it must not add to `outgoing`.
- Transfer numbers count only successful bookings, across the whole bank.
- A merged-away account: `deposit`, `transfer`, `schedule_transfer` and `cancel_transfer` treat it as missing, `top_spenders` leaves it out and `create_account` cannot reuse its id, but `get_balance` before the merge still answers from its history.
- Ids compare as text in the ranking, so `b10` comes before `b9`.
- Project traps: `Bank` must stay in `bank/bank.py`, the module `submit` imports. A module named after a standard-library one (`random.py`, `types.py`) breaks imports when the folder comes first on `sys.path`, which is why the README warns against `python -m pytest`. And a `[project]` table in `pyproject.toml` would let `uv run` manage the shared `.venv`.

### Language notes

- `heapq` works on a plain list of tuples `(due, number, transfer)`. The number is unique, so tuple comparison never reaches the transfer, which defines no ordering.
- `ScheduledTransfer` and `Account` are dataclasses with `slots=True` and `eq=False`: two bookings with equal fields are still two bookings, so equality is identity, which the scheduler tests rely on.
- `BalanceHistory` keeps times and balances in two lists so that `bisect_right(times, moment)` needs no `key`.
- `typing.Self` types the other account in `can_send`, `send` and `absorb`, and `typing.Final` marks the sentinels.
- No `__init__.py` is needed: `bank` is a namespace package, and `pythonpath = ["."]` in `pyproject.toml` lets the tests import it.
