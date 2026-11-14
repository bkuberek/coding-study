# Level Store: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| hash-map | optimal | O(1) per put, get, remove and size; O(n log n) per scan | O(n) | default answer |

## Approach: hash-map (Hash map)

### Intuition

Every level reads or writes single keys, except the prefix scan, which can afford to sort the matching keys.

### Algorithm

1. Keep one hash map from key to value.
2. `put` and `get` write and read it; `get` falls back to `""`.
3. `remove` deletes the key and reports whether it was there; `size` is the map's size.
4. `keysWithPrefix` filters the keys by prefix and sorts them.

### Correctness

The map always holds exactly the stored keys with their latest values, so every operation reads the current state.

### Complexity

- Time: O(1) per put, get, remove and size; O(n log n) per scan — map operations are constant on average; a scan sorts up to n keys.
- Space: O(n) — one entry per stored key.

### Trade-offs

A sorted map or a trie would make scans faster at the cost of slower writes; at 1000 operations the plain map is simplest.

### Pitfalls and edge cases

- `remove` of an absent key returns `false` and changes nothing.
- The empty prefix matches every key.

### Language notes

Java and Kotlin return `String[]` and `Array<String>`; Python and TypeScript return lists sorted with the default string order, which matches for lowercase ASCII keys.
