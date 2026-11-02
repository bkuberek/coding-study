# {{title}}: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | O(1) per op | O(n) | TODO |

## Approach: reference (Reference)

### Intuition

TODO: the state the class keeps, how a waiting task learns that a value arrived, and how each level extends it.

### Algorithm

1. TODO

### Design

- `app/main.py`: TODO: what the module is responsible for; one line per module of the reference.

### Correctness

TODO: the invariant each operation keeps, and why a waiting task never misses a value stored while it starts to wait.

### Complexity

- Time: O(1) per op — TODO
- Space: O(n) — TODO

### Trade-offs

TODO: what a later level would force you to change in an earlier design.

### Pitfalls and edge cases

TODO: a value stored before the wait starts, a wait that times out as a value arrives, tasks still waiting when a case ends.
