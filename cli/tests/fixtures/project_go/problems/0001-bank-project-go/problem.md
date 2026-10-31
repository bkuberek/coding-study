# Bank Project (Go)

## Statement

Build a small bank whose API grows one level at a time. Every level adds methods to the same `Bank` type in your project folder, and the methods of earlier levels keep working.

## Input

- `NewBank()`: creates a bank with no accounts.
- Timestamps increase from one call to the next. Account ids are non-empty strings.

## Output

Every method returns what its level describes. A request the bank cannot serve returns `-1` or `false`, never a panic.

## Project

The starter holds `bank.go`, which declares the `Bank` type, its constructor `NewBank` and the methods of level 1. Keep them in the module's root package: the grader imports it from there. Run the tests from the project folder with `go test ./...`.

## Level 1: Accounts and deposits

- `CreateAccount(timestamp, accountId)`: opens an account with balance 0; returns `false` when the id is taken.
- `Deposit(timestamp, accountId, amount)`: adds `amount` and returns the new balance, or `-1` for an unknown account.

### Example 1

<!-- case: ex1 -->

The second account named `ivy` is refused, and `max` has no account.

## Level 2: Transfers and reports

- `Transfer(timestamp, sourceId, targetId, amount)`: moves `amount` between two different accounts and returns the new balance of the source, or `-1` when an account is unknown, both are the same, or the source holds less than `amount`.
- `CloseAccount(timestamp, accountId)`: closes the account; its balance is gone.
- `Accounts()`: the ids of the open accounts, in any order.
- `Balances()`: the balances of the open accounts, ordered by account id.
- `AverageBalance()`: the mean balance of the open accounts, or `0` when there are none.
- `Interest(accountId, rate)`: the account's balance times `rate`, exactly, or `0` for an unknown account.

### Example 1

<!-- case: ex2 -->

The second transfer asks for more than `ivy` still holds.

### Example 2

<!-- case: ex3 -->

Interest is exact: 1.5% of 500 is 7.5.

## Constraints

- At most 1000 operations per case.
- Amounts are positive and at most 10^9.
