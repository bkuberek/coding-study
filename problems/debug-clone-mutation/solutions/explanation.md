# Debug: Clone Mutation: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| sequential-borrows | optimal | O(1) per op | O(n) | default answer: debit, let the borrow end, then credit |

## Approach: sequential-borrows (One mutable borrow at a time)

### Intuition

`let mut payee = self.accounts[to].clone();` makes a new `Account` with the same values, owned by the local variable `payee`. `payee.credit(amount)` changes that copy, and the copy is dropped when `transfer` returns. The real account in `self.accounts[to]` never changes: every transfer debits the sender and credits nobody, which is exactly the audit's finding.

The clone was the "small change" that made the first version compile. That version borrowed both accounts mutably at once:

```rust
let payer = &mut self.accounts[from];
let payee = &mut self.accounts[to]; // error[E0499]: cannot borrow `self.accounts` as mutable more than once
```

The borrow checker cannot see that `from != to` makes the two elements different, so it rejects two live `&mut` into the same `Vec`. Cloning silences the error because a clone borrows nothing, but it also detaches `payee` from the ledger. The code compiles without a single warning: `credit` takes `&mut self`, which counts as a use of `payee`.

The fix is to notice that `transfer` never needs both references at the same time. Debit the payer, let that borrow end, then borrow the payee.

### Debugging approach

1. **Check conservation.** Add up all balances before and after a transfer. The sum drops by the amount, so money is destroyed, not misrouted: the credit goes nowhere.
2. **Follow the credit.** `payee.credit(amount)` runs (a print inside `credit` shows the new balance), yet `balance(to)` is unchanged afterwards. The value that was changed is not the one in `self.accounts`.
3. **Look for copies.** `.clone()` on the line that defines `payee` creates an independent `Account`. In a debugger, the address of `payee` is on the stack, not inside the vector's buffer.
4. **Undo the workaround and read the error.** Replacing `.clone()` with `&mut` brings back E0499, with the hint to use `split_at_mut`. The real question is whether both borrows must be alive at once; they need not.

### Algorithm

1. Reject the transfer (return `false`) if `from == to` or `self.accounts[from].balance < amount`.
2. `self.accounts[from].debit(amount)`: lower the balance, count the transfer. This borrow ends at the semicolon.
3. `self.accounts[to].credit(amount)`: raise the balance, count the transfer.
4. Return `true`.

### Correctness

Each statement borrows one element of `self.accounts` mutably and releases it at the end of the statement, so both writes go to the accounts stored in the ledger. A transfer that passes the checks lowers `from` by `amount` and raises `to` by the same `amount`, so the total is unchanged, and it adds one to the transfer count of each side. Because `from != to`, the two updates touch different accounts. A rejected transfer returns before any write, so it changes nothing. The balance check reads the current balance, so a chain of transfers (`h2`) sees money that arrived earlier.

### Complexity

- Time: O(1) per op — every operation indexes the vector a constant number of times.
- Space: O(n) — one `Account` per account.

### Trade-offs

Two statements, one borrow each, is the simplest fix and needs no new API. When both references really are needed together, for example to compare or swap fields of two accounts, the options are:

- `split_at_mut`: split the slice at `max(from, to)` and take the lower index from the first half and the higher from the second. Correct and allocation-free, but needs care with the index order.
- `get_disjoint_mut([from, to])`, stable since Rust 1.86, returns both references or an error when the indexes overlap. It is newer than the 1.80 this catalog supports.
- Read what you need first (`let fee = self.fee_for(&self.accounts[to])`), then take the mutable borrows one at a time.

Keeping the clone and writing it back (`self.accounts[to] = payee;`) also works, but copies the whole account and leaves a stale copy around that the next edit can mutate by mistake.

### Pitfalls and edge cases

- The general trap: `.clone()` to satisfy the borrow checker gives you an independent value. Any change to it is invisible to the original. Cloning is right when you want a snapshot, and wrong when you meant to edit in place.
- The compiler does not warn here, because calling a `&mut self` method counts as using the clone. Mutating a field of an unused clone directly (`payee.balance += amount`) does get an "assigned but never read" warning on recent compilers, which is why this bug often hides behind a method call.
- A transfer to the same account must be rejected before any borrow, or it would count two transfers and, with two references, could not even be expressed.
- A balance exactly equal to the amount may be sent (`h4`); only a smaller balance is rejected.

### Prevention

- Treat `.clone()` added to fix a borrow error as a review flag: ask whether the code needs ownership or only a shorter borrow.
- Keep mutations close to the data: methods on `Ledger` that take indexes (`self.credit(to, amount)`) avoid handing out copies of `Account` at all.
- Do not derive `Clone` on a type that represents a single real-world entity unless copies are needed; without `Clone`, this bug does not compile.
- Test invariants, not only return values: here "the sum of balances is unchanged" fails on the first transfer.

### Language notes

- Rust only. In Java, Kotlin, Python, TypeScript and Go (with `[]*Account`), `accounts[to]` is a reference to the account object, so the code would update it in place; there is no borrow checker pushing toward a copy. Go's `[]Account` of values has a cousin of this bug: `payee := accounts[to]` copies the struct, as in the range-copy problem.
- With `#[derive(Copy, Clone)]` the copy would not even need `.clone()`: `let mut payee = self.accounts[to];` copies implicitly, which hides the bug further. Types that model identities are usually better without `Copy`.
