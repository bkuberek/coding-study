# {{title}}: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | O(1) per op | O(n) | TODO |

## Approach: reference (Reference)

### Intuition

TODO: the state the class keeps, what protects it when several threads call at once, and how each level extends it.

### Algorithm

1. TODO

### Design

- `src/main/java/app/{{class_name}}.java`: TODO: what the class is responsible for; one line per file of the reference.

### Correctness

TODO: the invariant each operation keeps, and why no interleaving of the calls loses an `add` or lets a `take` act on a stale count.

### Complexity

- Time: O(1) per op — TODO
- Space: O(n) — TODO

### Trade-offs

TODO: what a later level would force you to change in an earlier design.

### Pitfalls and edge cases

TODO: a read-modify-write split across two lock holds, `take` checking a count and writing it without holding the lock, a lock held while calling out of the class.

## Broken: lost-update (Add across two lock holds)

### Bug

TODO: what is wrong and which invariant exposes it.

### Failing interleaving

1. TODO

### Fix

TODO: the smallest change that makes it correct.
