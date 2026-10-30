# Scheduled Transfers Bank

## Statement

Build `Bank`, a set of bank accounts that hold whole amounts of money and send money to one another. The API grows over four levels: each level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

Every method receives the current time as its first argument, `timestamp`, in milliseconds. The class never reads a clock: the time is whatever the caller passes.

## Input

- `Bank()`: creates a bank with no accounts.
- `timestamp`: the time of the call. Within one test, timestamps strictly increase from one call to the next.
- `accountId`, `sourceId`, `targetId`: account identifiers.
- `amount`: a positive amount of money.
- Each level's section describes the methods it adds and their other parameters.

## Output

Each method returns what its level describes. A failed call never throws: it returns a sentinel, `-1` for numbers, `""` for strings and `false` for booleans.

## Level 1: Accounts and transfers

- `createAccount(timestamp, accountId)`: opens an account with balance 0 and returns `true`. Returns `false` when the id is already taken.
- `deposit(timestamp, accountId, amount)`: credits `amount` to the account and returns its new balance, or `-1` when there is no such account.
- `transfer(timestamp, sourceId, targetId, amount)`: moves `amount` from the source account to the target account and returns the source's new balance. Returns `-1`, leaving both accounts as they were, when either account is missing, when source and target are the same account, or when the source's balance is below `amount`.

### Example 1

<!-- case: ex1 -->

The second `createAccount` of `ivy` fails, and so does the deposit to `max`, who never opened an account. `ivy` sends 300 of her 800 to `leo` and keeps 500. With 300, `leo` cannot send 400 back, cannot send money to himself, and nobody can send money to `max`. A last deposit brings `leo` to 325.

## Level 2: Top spenders

- `topSpenders(timestamp, n)`: ranks the accounts by how much money has left them and returns the first `n` as strings `"<accountId>(<total>)"`. An account's total adds up its successful transfers (and, from level 3, its scheduled transfers that ran). Deposits and money received never count. Larger totals come first, and equal totals are ordered by account id, ascending. When fewer than `n` accounts exist, every account is returned, including those whose total is 0.

### Example 1

<!-- case: ex2 -->

`dan` sends 200 and later 100, 300 in all. `eve` sends 350 of the 700 she holds once `dan`'s 200 arrive. `fay` only receives, so her total is 0: she comes last and is left out when `n` is 2.

## Level 3: Scheduled transfers

- `scheduleTransfer(timestamp, sourceId, targetId, amount, delay)`: books a transfer of `amount` from the source to the target, due at `timestamp + delay`. Returns its id `"transfer<k>"`, where `k` numbers the transfers booked successfully in the whole bank, starting at 1. Returns `""` and books nothing when either account is missing or both are the same account. The source's balance is not checked when the transfer is booked.
- A booked transfer runs by itself. Every transfer due at time `t` runs before anything else happens in the first call whose timestamp is `t` or later. When several are due by then, they run in order of due time, and transfers due at the same time run in the order they were booked. Each one takes effect at its due time, not at the time of the call that set it off.
- A transfer that runs moves the money exactly like `transfer`, and its amount counts toward the source's total in `topSpenders`. When the source's balance is below `amount` at the due time, the transfer is skipped: nothing moves, and it is never tried again.
- `cancelTransfer(timestamp, accountId, transferId)`: cancels a booked transfer before it runs, so it never runs. Only its source account may cancel it. Returns `true` on success, and `false` when the account does not exist, no transfer has that id, `accountId` is not the transfer's source, or the transfer has already run, been skipped or been cancelled.

### Example 1

<!-- case: ex3 -->

`ana` books 80 for `ben` with a delay of 20, due at 24, and then 50 with a delay of 10, due at 15. The later booking falls due first: at time 15 it runs before the deposit, so `ben` reaches 1 + 50 + 1 = 52 and `ana` keeps 50. `ben` cancels his own booking of 5 before it is due. At time 24 the 80 fall due, but `ana` holds only 50, so that transfer is skipped and her deposit at time 30 brings her to 51. In booking order, the 80 would have gone through and the 50 would have been skipped. `ana` has sent 50 in all.

## Level 4: Merges and balance history

- `mergeAccounts(timestamp, accountId, otherId)`: folds `otherId` into `accountId`. The balance and the spending total of `otherId` are added to those of `accountId`, and every booked transfer still waiting to run that names `otherId` as its source or its target names `accountId` there instead, so `accountId` can cancel the ones it now sends. Afterwards `otherId` no longer exists, and an id that disappeared in a merge is never created again. Returns `false` and changes nothing when the ids are equal or either account does not exist.
- A transfer that falls due when its source and target are the same account, as a transfer waiting between two merged accounts becomes, is skipped like one the source cannot pay.
- `getBalance(timestamp, accountId, timeAt)`: the balance the account had at time `timeAt`, after every call with a timestamp at most `timeAt` and every scheduled transfer due by then. Returns `-1` when the account did not exist at `timeAt`: before it was created, or from the moment it was merged away. The kept account's balance includes the absorbed balance only from the merge on, and the merged-away account still answers for times before the merge.
- `timeAt` is never later than `timestamp`.

### Example 1

<!-- case: ex4 -->

`side` books 30 for `shop`, due at 16, and is merged into `main` at time 7, so `main` holds 100 + 40 and the transfer now leaves from `main`: at time 16, `main` drops to 110 and `shop` receives the 30. `side` no longer takes deposits. History still knows that `main` held 100 at time 6, 140 at time 7 and 110 at time 16, and that `side` held 40 at time 6 and was gone at time 7. The ranking lists `main` with the 30 it sent, and no longer `side`.

## Constraints

- At most 1000 calls per test.
- `1 <= timestamp <= 10^9`, strictly increasing within a test.
- `1 <= amount <= 10^10`; balances stay below `2^53`.
- `1 <= delay <= 10^9`.
- `1 <= n <= 1000`.
- Account ids are 1 to 10 lowercase letters or digits.

## Follow-ups

- Here time only moves when a call arrives. In a real service, transfers must run on time without any traffic, and several workers share the work. How would you hand out due transfers so that each runs exactly once, for example a jobs table whose rows workers claim with `SELECT ... FOR UPDATE SKIP LOCKED`, or a delay queue, and how would you record whether each one ran, was skipped or was cancelled?
- Two debits of the same account that arrive at the same moment can both see enough money and overdraw it together. How would you prevent that: a row lock, a conditional update such as `UPDATE ... SET balance = balance - :amount WHERE balance >= :amount`, or a version check with retries?
- Why a heap rather than a list kept sorted by due time? Compare what booking, cancelling and running a transfer cost with each.

## Hints

### Hint 1

Keep one object per account with its balance and the total it has sent; `topSpenders` can sort the accounts with a two-part key.

### Hint 2

Run the due transfers at the start of every call. Each transfer has its own delay, so the order in which they fall due is not the order in which they were booked, and a plain queue gets it wrong. A min-heap keyed by (due time, booking number) hands them out in the right order.

### Hint 3

Removing a cancelled transfer from the middle of a heap is awkward. Mark it as no longer pending, leave it where it is, and throw it away when it reaches the top.

### Hint 4

For merges, remember which account each merged id went into and look up a transfer's current source and target only when it runs. For history, append `(time, balance)` after every change, using the due time for scheduled transfers.
