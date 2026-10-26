# Bank Transfers

## Statement

A bank keeps a balance for each of its accounts and moves money between them on behalf of many tellers working at the same time. Money is never created or destroyed: every transfer takes an amount out of one account and puts the same amount into another, or does nothing at all. Build the bank so that this stays true under any number of concurrent transfers, and so that two tellers can never block each other forever.

Implement the class `Bank`:

- `Bank(balances)` creates accounts numbered `0` to `n - 1`, where account `i` starts with `balances[i]`.
- `transfer(fromAccount, toAccount, amount)` moves `amount` from `fromAccount` to `toAccount` and returns `true`. If either account does not exist, or `fromAccount` holds less than `amount`, it changes nothing and returns `false`. A transfer from an account to itself changes nothing, and returns `true` exactly when the account holds at least `amount`.
- `balance(account)` returns the current balance of `account`, or `-1` if it does not exist.
- `total()` returns the sum of all balances as of one instant: a total that counts a transfer's withdrawal but not its deposit, or the other way round, is wrong.

Reference: this is our own wording of the transfer part of LeetCode problem 2043, [Simple Bank System](https://leetcode.com/problems/simple-bank-system/), with 0-based account numbers and concurrency added.

## Input

- Constructor `balances`: the starting balance of each account.
- `transfer(fromAccount, toAccount, amount)`: the account to take money from, the account to put it into, and how much to move.
- `balance(account)`: the account to look up.
- `total()`: no arguments.

Sequential tests are a sequence of calls on one worker: the constructor first, then method calls in order. Stress tests call the same methods from many workers at once.

## Output

- `transfer` returns whether the money moved.
- `balance` returns the account's balance, or `-1` for an account that does not exist.
- `total` returns the sum of all balances.

The expected output of a sequential test lists one result per call, with `null` for the constructor.

## Examples

### Example 1

<!-- case: ex1 -->

The first transfer moves 30 from account 0 to account 2. The second one fails because account 1 holds only 50, and the total stays 150 throughout.

### Example 2

<!-- case: ex2 -->

Account 1 sends its whole balance to account 0, which then sends 5 back.

## Constraints

- `1 <= balances.length <= 1000`
- `0 <= balances[i]`, and the sum of all balances is at most `10^15`.
- `1 <= amount <= 10^15`
- Account numbers passed to the methods may be outside `0` to `n - 1`.

## Concurrency

Every method is called concurrently by many workers. No method waits for a condition; they may only wait for each other's locks.

- Conservation: at every moment, the balances add up to the starting total. `total` must report exactly that value even while transfers run, and no balance ever becomes negative.
- Atomicity: a transfer either moves the whole amount or nothing, and its balance check and both updates form one step, so two concurrent withdrawals cannot both spend the same money.
- Progress: transfers between the same accounts in opposite directions, run at the same time, must all finish. A schedule in which two transfers wait for each other forever is a bug, and the stress tests report it as `STALLED`.
- Transfers between unrelated accounts should not wait for each other; a single lock for the whole bank is correct but serializes every transfer.

Java and Kotlin run on platform threads and on virtual threads, and Python on threads. A passing stress run is evidence of correct synchronization, not proof; a deadlock that needs a rare schedule may not show up in a few runs.

## Follow-ups

- How does `total` stay consistent without stopping every transfer for the whole time it adds up the balances?
- What changes if a transfer may involve several accounts at once, for example a payment split between three recipients?
- How would you find out that a deadlock happened in production, and what would you log?

## Hints

### Hint 1

Give each account its own lock, so that transfers between different accounts run in parallel. A transfer must hold the locks of both of its accounts.

### Hint 2

Two transfers deadlock when each holds one lock and waits for the other. Can you make every transfer take its two locks in the same global order?

### Hint 3

Order the locks by account number. A consistent `total` takes every account's lock, in that same order.
