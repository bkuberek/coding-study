# Bank Project (Python)

## Statement

Build `Bank`, a set of bank accounts that hold whole amounts of money and send money to one another, as a small Python project. The API grows over four levels: each level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied. You keep the same code from one level to the next, so how you split it into modules and classes is part of the work.

Every method receives the current time as its first argument, `timestamp`, in milliseconds. The bank never reads a clock: the time is whatever the caller passes.

## Input

- `Bank()`: creates a bank with no accounts.
- `timestamp`: the time of the call. Within one test, timestamps strictly increase from one call to the next.
- `account_id`, `source_id`, `target_id`: account identifiers.
- `amount`: a positive amount of money.
- Each level's section describes the methods it adds and their other parameters.

## Output

Each method returns what its level describes. A failed call never raises an exception: it returns a sentinel, `-1` for an `int`, `""` for a `str` and `False` for a `bool`.

## Project

`cstudy start` copies a small Python project into `projects/bank-project-python/` in your workspace, and you solve the problem there, in as many files as you like:

- `bank/bank.py`: the class `Bank`, with level 1's methods raising `NotImplementedError`.
- `bank/models.py`: an `Account` dataclass to grow or replace.
- `tests/conftest.py`: a `bank` fixture for your own tests.
- `tests/test_level_<n>.py`: the examples of each open level as pytest tests, written when the level opens and never rewritten. Edit them, and add your own test files next to them.
- `README.md`, and `pyproject.toml` with the pytest, pyright and ruff settings.

The contract: `Bank` stays in `bank/bank.py` and takes no constructor arguments, and every method keeps the name and parameters its level gives. Each level starts with a line naming the methods it adds.

`cstudy test bank-project-python` runs your tests, and so does `.venv/bin/pytest` in the project folder; either run is feedback only. `cstudy submit bank-project-python` grades every case of the open levels, hidden ones included, and opens the next level when they all pass. Each submission grades the earlier levels again, so the code you change for a new level must keep their rules.

## Level 1: Accounts and transfers

- `create_account(timestamp, account_id)`: opens an account with balance 0 and returns `True`. Returns `False` when the id is already taken.
- `deposit(timestamp, account_id, amount)`: adds `amount` to the account and returns its new balance, or `-1` when there is no such account.
- `transfer(timestamp, source_id, target_id, amount)`: moves `amount` from the source account to the target account and returns the source's new balance. Returns `-1`, leaving both accounts as they were, when either account does not exist, when source and target are the same account, or when the source's balance is below `amount`.

### Example 1

<!-- case: ex1 -->

The second `create_account` of `rosa` fails, and so does the deposit to `kim`, who never opened an account. `rosa` sends 250 of her 600 to `tom` and keeps 350, and a deposit of 50 brings `tom` to 300.

### Example 2

<!-- case: ex2 -->

`ada` cannot send 150 when she holds 100, and the refused transfer moves nothing: a deposit of 1 shows that `bo` received nothing. A transfer of her whole balance goes through and leaves her at 0.

## Level 2: Top spenders

- `top_spenders(timestamp, n)`: ranks the accounts by how much money has left them and returns the first `n` as strings `"<account_id>(<total>)"`. An account's total adds up its successful transfers; deposits and money received never count. Larger totals come first, and equal totals are ordered by account id, ascending, comparing the ids as text. When fewer than `n` accounts exist, every account is returned, including those whose total is 0.
- `1 <= n <= 1000`.

### Example 1

<!-- case: ex3 -->

`nia` sends 400 and then 300, 700 in all. `oz` sends 450, most of it money he had just received from `nia`; only what leaves an account counts, so his total is 450. `pam` only receives: her total is 0, so she comes last and is left out when `n` is 2.

### Example 2

<!-- case: ex4 -->

`una` and `eli` each send 20, so `eli` comes first by id. Asking for 10 accounts when only three exist returns all three.

## Level 3: Scheduled transfers

- `schedule_transfer(timestamp, source_id, target_id, amount, delay)`: books a transfer of `amount` from the source to the target, due at `timestamp + delay`. Returns its id `"transfer<k>"`, where `k` numbers the transfers booked successfully in the whole bank, starting at 1. Returns `""` and books nothing when either account does not exist or both are the same account. The source's balance is not checked when the transfer is booked.
- A booked transfer runs by itself. Every transfer due at time `t` runs before anything else happens in the first call whose timestamp is `t` or later, whatever that call does. When several are due by then, they run in order of due time, and transfers due at the same time run in the order they were booked. Each one takes effect at its due time, not at the time of the call that set it off.
- A transfer that runs moves the money exactly like `transfer`, and its amount counts toward the source's total in `top_spenders`. When the source's balance is below `amount` at the due time, the transfer is skipped: nothing moves, and it is never tried again.
- `cancel_transfer(timestamp, account_id, transfer_id)`: cancels a booked transfer before it runs, so it never runs. Only its source account may cancel it. Returns `True` on success, and `False` when the account does not exist, no transfer has that id, `account_id` is not the transfer's source, or the transfer has already run, been skipped or been cancelled.
- `1 <= delay <= 10^9`.

### Example 1

<!-- case: ex5 -->

`lou` books 30 for `max`, due at 24, and then 50, due at 10. The later booking falls due first: by the deposit at time 12, `max` has received the 50, and by the deposit at time 30 also the 30. Both count as money `lou` sent.

### Example 2

<!-- case: ex6 -->

`ann` books 50 for `raj`, due at 10, and `raj` books 5 for `ann`. `ann` cannot cancel `raj`'s booking; `raj` can. At time 10 the 50 fall due before `ann`'s deposit, while she holds 40, so that transfer is skipped: her deposit brings her to 41, and `raj` receives nothing.

## Level 4: Merges and balance history

- `merge_accounts(timestamp, account_id, other_id)`: folds `other_id` into `account_id`. The balance and the spending total of `other_id` are added to those of `account_id`, and every booked transfer still waiting to run that names `other_id` as its source or its target names `account_id` there instead, so `account_id` can cancel the ones it now sends. Afterwards `other_id` no longer exists, and an id that disappeared in a merge is never created again. Returns `False` and changes nothing when the ids are equal or either account does not exist.
- A transfer that falls due when its source and target are the same account, as a transfer waiting between two merged accounts becomes, is skipped like one the source cannot pay.
- `get_balance(timestamp, account_id, time_at)`: the balance the account had at time `time_at`, after every call with a timestamp at most `time_at` and every scheduled transfer due by then. Returns `-1` when the account did not exist at `time_at`: before it was created, or from the moment it was merged away. The kept account's balance includes the absorbed balance only from the merge on, and the merged-away account still answers for times before the merge.
- `time_at` is never later than `timestamp`.

### Example 1

<!-- case: ex7 -->

`work` has sent 30 and booked 40 for `shop` when it is merged into `home` at time 8: `home` now holds 200 + 50 and has sent 30. `work` no longer takes deposits, and its booking leaves from `home` at time 20, so `shop` holds 30 + 40 before its deposit of 1. The ranking lists `home` with 70 and no longer `work`.

### Example 2

<!-- case: ex8 -->

`joy` books 60 for `kip`, due at 12, and absorbs `kip` at time 15. History knows that `joy` did not exist at time 4, held 100 at time 11, 40 at time 12 when the transfer ran, and 40 + 65 from the merge on. `kip` held 65 at time 14 and is gone at time 15.

## Constraints

- At most 1000 calls per test.
- `1 <= timestamp <= 10^9`, strictly increasing within a test.
- `1 <= amount <= 10^10`; balances stay below `2^53`.
- Account ids are 1 to 10 lowercase letters or digits.

## Follow-ups

- Two debits of the same account that arrive at the same moment can both see enough money and overdraw it together. How would you prevent that: a row lock, a conditional update such as `UPDATE ... SET balance = balance - :amount WHERE balance >= :amount`, or a version check with retries?
- Which parts of your design would you test on their own, without going through `Bank`, and what would those tests pin down that the level examples do not?
- If the bank had to survive a restart, what would you store: the balances, the changes that produced them, or both?

## Hints

### Hint 1

Give each account an object that owns its numbers and the rules that change them, and keep `Bank` to looking accounts up, checking the request and delegating. Each later level then adds a field, a method or a module instead of a rewrite.

### Hint 2

Check every reason a call can fail before you change anything. A failed call must leave every account exactly as it was, which is easy to get wrong when one call touches two accounts.

### Hint 3

When something has to happen at a time of its own rather than at a call, let time move in exactly one place: a private step at the start of every public method, read-only ones included, that catches the bank up to the call's timestamp. Items due at different times must come out in due-time order, which is not always the order they arrived in. A min-heap keyed by (due time, arrival number) hands them out in the right order, and an item that is called off can stay in the heap, marked, until it reaches the top.

### Hint 4

To answer questions about the past, record each change at the moment it took effect, the due time for anything that ran later, and search that record. When accounts are combined, remember where each old id went and resolve it when you need it, instead of rewriting everything that mentions it.
