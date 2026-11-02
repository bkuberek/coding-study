# {{title}}: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| reference | optimal | O(1) per op | O(n) | TODO |

## Approach: reference (Reference)

### Intuition

TODO: the state the class keeps, how a waiting coroutine learns that a value arrived, and how each level extends it.

### Algorithm

1. TODO

### Design

- `src/main/kotlin/app/{{class_name}}.kt`: TODO: what the class is responsible for; one line per file of the reference.

### Correctness

TODO: the invariant each operation keeps, and why a waiting call never misses a value stored while it starts to wait.

### Complexity

- Time: O(1) per op — TODO
- Space: O(n) — TODO

### Trade-offs

TODO: what a later level would force you to change in an earlier design.

### Pitfalls and edge cases

TODO: a value stored before the wait starts, a wait that times out as a value arrives, coroutines still active when a case ends.
