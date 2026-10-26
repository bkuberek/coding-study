# LRU Cache: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| ordered-dict | optimal | O(1) per op | O(capacity) | default answer |

## Approach: ordered-dict (Ordered dictionary)

### Intuition

An ordered dictionary keeps keys in recency order.

### Algorithm

1. Move a key to the end on every access.
2. Pop the first key when the cache overflows.

### Correctness

The first key is always the least recently used one.

### Complexity

- Time: O(1) per op — dictionary moves are constant time.
- Space: O(capacity) — at most capacity entries.

### Trade-offs

Short, but hides the linked list an interviewer may ask for.

### Pitfalls and edge cases

Updating an existing key also refreshes it.
