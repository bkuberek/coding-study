# Debug: Clone Mutation

## Statement

A payments service keeps account balances in a `Ledger`. Accounts are numbered from 0. The `Ledger` you start from should support:

- `Ledger::new(balances)`: account `i` starts with `balances[i]` and no transfers.
- `transfer(from_account, to_account, amount)`: move `amount` from one account to another and return `true`. The transfer is rejected, changing nothing and returning `false`, when both accounts are the same or when `from_account` holds less than `amount`.
- `balance(account)`: the current balance of `account`.
- `transfers(account)`: the number of successful transfers `account` took part in, as sender or as recipient.

The code compiles without warnings, and the existing tests pass. Find the bug and fix it.

### Bug report

> **Title:** Transfers leave the sender but never arrive
>
> Customers report that transfers are taken from their account and never reach the recipient. The nightly audit agrees: the sum of all balances drops by exactly the amount of every transfer of the day, and recipients' transfer counts stay at zero. The developer who wrote `transfer` remembers that the first version "did not compile because of the borrow checker" and that one small change fixed it. The unit tests only check the sender's side and rejected transfers.

## Input

- `balances`: the opening balance of each account
- `from_account`, `to_account`, `account`: account numbers
- `amount`: the amount to move

## Output

`transfer` returns whether the transfer happened; `balance` and `transfers` return the current values.

## Examples

### Example 1

<!-- case: ex1 -->

The first transfer asks for 150 from an account holding 100, and the second sends to the sending account itself, so both are rejected and nothing changes. This case passes as shipped.

### Example 2

<!-- case: ex2 -->

125 leaves account 0, which keeps 375 and has taken part in one transfer. This case passes too.

## Constraints

- `1 <= balances.length <= 1000`
- `0 <= balances[i] <= 10^6`
- `1 <= amount <= 10^7`
- Account numbers are valid indexes of `balances`.
- At most 1000 operations per test. Transfers move money without creating it, so no balance exceeds the sum of the opening balances, at most `10^9`.

## Follow-ups

- Write the fix with `split_at_mut`, which hands out two mutable references at once. When is that worth the extra code?
- `#[derive(Clone)]` was added to `Account` for this code. After your fix, is it still needed?

## Hints

### Hint 1

Run a transfer and query the recipient's balance. Then add up all balances before and after.

### Hint 2

Which account does `payee.credit(amount)` change?

### Hint 3

Replace `.clone()` with `&mut self.accounts[to]` and read the compiler error. What is it protecting against, and does `transfer` really need both references at the same time?

### Hint 4

Debit the payer, let that borrow end, then borrow the payee: `self.accounts[from].debit(amount)` followed by `self.accounts[to].credit(amount)`.
