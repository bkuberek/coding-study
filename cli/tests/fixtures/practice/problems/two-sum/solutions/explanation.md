# Two Sum: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| brute-force | brute | O(n^2) | O(1) | n is tiny |
| hash-map | optimal | O(n) | O(n) | default answer |

## Approach: brute-force (Check every pair)

### Intuition

Try every pair of positions.

### Algorithm

1. For each `i`, for each `j > i`, return `[i, j]` when the values add up.

### Correctness

Every pair is checked, so the unique answer is found.

### Complexity

- Time: O(n^2) — every pair is visited once.
- Space: O(1) — only loop indices.

### Trade-offs

Simplest to write; too slow for large inputs.

### Pitfalls and edge cases

Never pair a position with itself.

## Approach: hash-map (One-pass hash map)

### Intuition

Remember each value's position; the partner of `x` is `target - x`.

### Algorithm

1. Walk the array once.
2. Return when the partner was seen; otherwise remember the value.

### Correctness

When the second element of the answer is reached, the first one is already in the map.

### Complexity

- Time: O(n) — one pass with constant-time map operations.
- Space: O(n) — the map holds up to n - 1 entries.

### Trade-offs

Linear time at the cost of linear memory.

### Pitfalls and edge cases

Check the map before inserting, so equal values at different positions pair up.

### Language notes

Python uses a dict.
