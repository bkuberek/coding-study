# Tally Project (Python): Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | O(1) per operation | O(n) | default answer |

## Approach: reference (Counts under one lock)

### Intuition

Each operation reads one count and may write it back, so a dictionary answers each one directly, and one lock around each read and write keeps a thread from overwriting another's change.

### Algorithm

1. `add` adds to the count of a key under the lock and returns the new count.
2. `count` reads the count under the lock.
3. `take` checks and lowers the count under the lock.

### Design

- `tally/tally.py`: the `Tally` class, which delegates to the counts.
- `tally/counts.py`: the counts and the lock that guards them.

### Correctness

Every read and write of a count happens under the same lock, so the changes of concurrent calls apply one after another and none is lost.

### Complexity

- Time: O(1) per operation — each call does a constant number of dictionary operations.
- Space: O(n) — one entry per key.

### Trade-offs

One lock serializes every call; a lock per key would let calls on different keys run together at the cost of more locks.

### Pitfalls and edge cases

A take that would make the count negative changes nothing.

## Broken: unlocked-add (Add outside the lock)

### Bug

`add` reads the count on one line and writes it on the next without the lock.

### Failing interleaving

Two threads read the same count, each adds 1 and writes it back, so one increment is lost and both return the same count.

### Fix

Read and write the count under the lock, as `take` does.
