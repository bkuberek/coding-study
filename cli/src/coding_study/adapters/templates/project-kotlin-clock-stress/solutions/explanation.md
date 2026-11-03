# {{title}}: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | O(1) per op | O(n) | TODO |

## Approach: reference (Reference)

### Intuition

TODO: the state the class keeps, how a waiting caller learns that a count changed, what protects the state when several threads call `add` at once (a lock that every read and write of the counts holds), and how each level extends it.

### Algorithm

1. TODO

### Design

- `src/main/kotlin/app/{{class_name}}.kt`: TODO: what the class is responsible for; one line per file of the reference.

### Correctness

TODO: the invariant each operation keeps, why a waiting call never misses an `add` that lands while it starts to wait, and why no interleaving of `add` calls loses an update.

### Complexity

- Time: O(1) per op — TODO
- Space: O(n) — TODO

### Trade-offs

TODO: what a later level would force you to change in an earlier design.

### Pitfalls and edge cases

TODO: an `add` that lands before the wait starts, a wait that times out as the count arrives, coroutines still active when a case ends, a read-modify-write split across two lock holds.

## Broken: lost-update (Add across two lock holds)

### Bug

TODO: what is wrong and which invariant exposes it.

### Failing interleaving

1. TODO

### Fix

TODO: the smallest change that makes it correct.
