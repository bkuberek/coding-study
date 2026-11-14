# Bank Project (Rust)

## Statement

Build a small bank whose API grows one level at a time. Every level adds methods to the same `Bank` type in your crate, and the methods of earlier levels keep working.

## Input

- `Bank::new()`: creates a bank with no accounts.
- Timestamps increase from one call to the next. Account ids are non-empty strings.

## Output

Every method returns what its level describes. A request the bank cannot serve returns `-1` or `false`, never a panic.

## Project

The starter holds the crate `bank`, whose `src/lib.rs` declares `Bank` with the methods of level 1. Keep `Bank` public at the crate root: the grader uses `bank::Bank`. Run the tests from the project folder with `cargo test`.

## Level 1: Accounts and deposits

- `create_account(timestamp, account_id)`: opens an account with balance 0; returns `false` when the id is taken.
- `deposit(timestamp, account_id, amount)`: adds `amount` and returns the new balance, or `-1` for an unknown account.

### Example 1

<!-- case: ex1 -->

The second account named `ivy` is refused, and `max` has no account.

## Level 2: Transfers

- `transfer(timestamp, source_id, target_id, amount)`: moves `amount` between two different accounts and returns the new balance of the source, or `-1` when an account is unknown, both are the same, or the source holds less than `amount`.

### Example 1

<!-- case: ex2 -->

The second transfer asks for more than `ivy` still holds.

## Constraints

- At most 1000 operations per case.
- Amounts are positive and at most 10^9.
