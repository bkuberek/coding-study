# Bank Project (Kotlin): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | O(1) per operation | O(n) | default answer |

## Approach: reference (Balances in a map)

### Intuition

Every operation reads or writes the balance of one or two accounts, so a map from account id to balance answers each one directly.

### Algorithm

1. `createAccount` stores a zero balance unless the id is taken.
2. `deposit` adds to a known balance.
3. `transfer` checks both accounts and the source balance, then moves the amount.

### Design

- `src/main/kotlin/bank/Bank.kt`: the `Bank` class and its rules.
- `src/main/kotlin/bank/accounts/Balances.kt`: the balance of every account.

### Correctness

Each method changes a balance only after checking every condition its level states, so no balance goes negative and no unknown account appears.

### Complexity

- Time: O(1) per operation — each call does a constant number of map operations.
- Space: O(n) — one entry per account.

### Trade-offs

A map is the simplest structure that serves both levels; balance histories would need more.

### Pitfalls and edge cases

A transfer from an account to itself is refused, not counted twice.
