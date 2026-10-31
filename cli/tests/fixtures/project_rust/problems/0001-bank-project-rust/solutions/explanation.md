# Bank Project (Rust): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | O(1) per operation | O(n) | default answer |

## Approach: reference (Balances in a hash map)

### Intuition

Every operation reads or writes the balance of one or two accounts, so a hash map from account id to balance answers each one directly.

### Algorithm

1. `create_account` stores a zero balance unless the id is taken.
2. `deposit` adds to a known balance.
3. `transfer` checks both accounts and the source balance, then moves the amount.

### Design

- `src/lib.rs`: the `Bank` type, which turns the ledger's answers into the API's values.
- `src/ledger.rs`: the balances and the rules that change them.

### Correctness

Each method changes a balance only after checking every condition its level states, so no balance goes negative and no unknown account appears.

### Complexity

- Time: O(1) per operation — each call does a constant number of hash map operations.
- Space: O(n) — one entry per account.

### Trade-offs

A hash map is the simplest structure that serves both levels; balance histories would need more.

### Pitfalls and edge cases

A transfer from an account to itself is refused, not counted twice.
