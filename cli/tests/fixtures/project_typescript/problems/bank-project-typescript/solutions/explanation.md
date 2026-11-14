# Bank Project (TypeScript): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | O(n log n) for balances, O(1) otherwise | O(n) | default answer |

## Approach: reference (Balances in a ledger)

### Intuition

Every operation reads or writes the balance of one or two accounts, so a map from account id to balance answers each one directly.

### Algorithm

1. `createAccount` stores a zero balance unless the id is taken.
2. `deposit` adds to a known balance.
3. `transfer` checks both accounts and the source balance, then moves the amount.
4. The reports read the map: its ids, its balances in id order, and their mean.

### Design

- `src/bank.ts`: the `Bank` class and the rules of each level.
- `src/ledger.ts`: the `Ledger` class, the balances by account id.

### Correctness

Each method changes a balance only after checking every condition its level states, so no balance goes negative and no unknown account appears.

### Complexity

- Time: O(n log n) for balances, O(1) otherwise — `balances` sorts the ids, and every other call reads or writes one or two entries of the map, except the reports, which read each entry once.
- Space: O(n) — one entry per account.

### Trade-offs

A map is the simplest structure that serves both levels; balance histories would need more.

### Pitfalls and edge cases

A transfer from an account to itself is refused, not counted twice.
