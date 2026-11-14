# Banking System

## Statement

Build `BankingSystem`, a ledger of bank accounts that hold whole amounts of money. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

Every method takes the current time as its first argument, `timestamp`, in milliseconds. Nothing reads a clock: time is whatever the caller passes.

## Input

- `BankingSystem()`: creates a system with no accounts.
- `timestamp`: the time of the call. Within one test, timestamps strictly increase from call to call.
- `accountId`, `sourceId`, `targetId`, `otherId`: account identifiers.
- `amount`: a positive amount of money.
- Each level's section describes the methods it adds and their other parameters.

## Output

Each method returns what its level describes. Failure is reported with a sentinel, never with an exception: `-1` for numbers, `""` for strings and `false` for booleans.

## Level 1: Accounts and transfers

- `createAccount(timestamp, accountId)`: opens an account with balance 0. Returns `false` when an account with that id already exists.
- `deposit(timestamp, accountId, amount)`: adds `amount` to the account. Returns the new balance, or `-1` when the account does not exist.
- `transfer(timestamp, sourceId, targetId, amount)`: moves `amount` from the source to the target. Returns the source's new balance. Returns `-1` and changes nothing when either account does not exist, when they are the same account, or when the source holds less than `amount`.

### Example 1

<!-- case: ex1 -->

The second `createAccount` of `alice` fails, and so does a deposit to `carol`, who has no account. `alice` sends 200 of her 500 to `bob` and keeps 300; she cannot send 400 more, cannot send money to herself, and `bob` cannot pay the missing `carol`.

## Level 2: Top spenders

- `topSpenders(timestamp, n)`: the `n` accounts that have sent the most money, as strings `"<accountId>(<total>)"`. The total counts every successful transfer the account sent (and, from level 3, every payment it made). Order by total, largest first; equal totals go in ascending order of account id. Return every account when fewer than `n` exist, including accounts that sent nothing.

### Example 1

<!-- case: ex2 -->

`acc1` sent 300 and then 100, `acc2` sent 500, and `acc3` sent nothing. Receiving money never counts.

## Level 3: Payments with cashback

- `pay(timestamp, accountId, amount)`: withdraws `amount` from the account as a payment, which counts toward the account's total in `topSpenders`. Returns a payment id `"payment<k>"`, where `k` counts the successful payments in the whole system, starting at 1. Returns `""` and changes nothing when the account does not exist or holds less than `amount`.
- Every payment earns a cashback of 2% of `amount`, rounded down, credited to the paying account exactly 86,400,000 milliseconds (24 hours) after the payment. A cashback that falls due at time `t` is credited before anything else happens in a call at time `t` or later. The cashback is not a deposit and does not change the spending total.
- `paymentStatus(timestamp, accountId, paymentId)`: `"IN_PROGRESS"` before the cashback is credited and `"CASHBACK_RECEIVED"` after. Returns `""` when the account does not exist, the payment does not exist, or the payment was not made from this account.

### Example 1

<!-- case: ex3 -->

`ana` pays 300 at time 3000 and keeps 700; with a deposit of 1 she has 701. Her cashback of 6 falls due at 3000 + 86,400,000, so the status changes at that moment, and the next deposit of 1 brings her to 708.

## Level 4: Merges and balance history

- `mergeAccounts(timestamp, accountId, otherId)`: moves everything of `otherId` into `accountId`: its balance, its spending total, its payments (now queried through `accountId`) and its cashbacks still to come. Afterwards `otherId` no longer exists. Returns `false` and changes nothing when the ids are equal or either account does not exist. An id that disappeared in a merge is never created again.
- `getBalance(timestamp, accountId, timeAt)`: the balance the account had at time `timeAt`, after every call with a timestamp at most `timeAt` and every cashback due by then. Returns `-1` when the account did not exist at `timeAt`: before it was created, or from the moment it was merged away.
- `timeAt` is never later than `timestamp`.

### Example 1

<!-- case: ex4 -->

`side` sends 20 to `main` and is then merged into it, so `main` holds 120 + 30 and has spent 20, while `side` can no longer take deposits. History still knows that `main` held 120 at time 5 and 150 at time 6, that `side` held 30 at time 5 and was gone at 6, and that `main` did not exist at time 0.

## Constraints

- At most 1000 calls per test.
- `1 <= timestamp <= 10^9`, strictly increasing within a test.
- `1 <= amount <= 10^10`; balances stay below `2^53`.
- `1 <= n <= 1000`.
- Account ids are 1 to 10 lowercase letters or digits.

## Follow-ups

- How would `topSpenders` stay fast with a million accounts and frequent queries?
- How would you keep balance history bounded if `getBalance` only looked back 30 days?

## Hints

### Hint 1

Keep one object per account with its balance and its spending total; `topSpenders` can sort the accounts with a two-part key.

### Hint 2

Credit due cashbacks at the start of every call. The delay is the same for every payment and timestamps grow, so cashbacks fall due in the order the payments were made: a plain queue is enough.

### Hint 3

For history, append `(time, balance)` to the account after every change, including cashbacks, which happen at their due time. A merged-away account keeps its history and records when it stopped existing.
