# Bank Project (Go): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | O(n log n) for balances, O(1) otherwise | O(n) | default answer |

## Approach: reference (Balances in a ledger)

### Intuition

Every operation reads or writes the balance of one or two accounts, so a map from account id to balance answers each one directly.

### Algorithm

1. `CreateAccount` stores a zero balance unless the id is taken.
2. `Deposit` adds to a known balance.
3. `Transfer` checks both accounts and the source balance, then moves the amount.
4. The reports read the map: its ids, its balances in id order, their mean, and one balance times a rate.

### Design

- `bank.go`: the `Bank` type and the rules of each level.
- `ledger/ledger.go`: the `Ledger` type, the balances by account id, in a package of its own.

### Correctness

Each method changes a balance only after checking every condition its level states, so no balance goes negative and no unknown account appears.

### Complexity

- Time: O(n log n) for balances, O(1) otherwise — `Balances` sorts the ids, and every other call reads or writes one or two entries of the map, except the reports, which read each entry once.
- Space: O(n) — one entry per account.

### Trade-offs

A map is the simplest structure that serves both levels; balance histories would need more.

### Pitfalls and edge cases

A transfer from an account to itself is refused, not counted twice.
