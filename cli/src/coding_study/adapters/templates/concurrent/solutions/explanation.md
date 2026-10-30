# {{title}}: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | O(1) per op | O(1) | TODO |

## Approach: reference (Reference)

### Intuition

TODO: the key insight in a few sentences.

### Algorithm

1. TODO

### Correctness

TODO: why no schedule breaks the invariant.

### Complexity

- Time: O(1) per op — TODO
- Space: O(1) — TODO

### Trade-offs

TODO: versus the other approaches.

### Pitfalls and edge cases

TODO: waiting with `if` instead of `while`, lost wake-ups.

### Language notes

TODO: Java platform versus virtual threads, Python's GIL, the Kotlin coroutine version (`Mutex`, `Semaphore`, `Channel`), Go's `sync` package and channels, and Rust's `Mutex`, `Condvar` and `Send + Sync`.

## Broken: no-wait (Acquire without waiting)

### Bug

TODO: what is wrong and which invariant or status exposes it.

### Failing interleaving

1. TODO

### Fix

TODO: the smallest change that makes it correct.
