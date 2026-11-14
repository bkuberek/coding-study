# LRU Cache

## Statement

Design a cache with a fixed capacity that evicts the least recently used key when it is full.

## Input

- `LRUCache(capacity)`: the number of keys the cache holds
- `get(key)`: the value for `key`
- `put(key, value)`: store `value` under `key`

## Output

`get` returns the value, or `-1` when the key is absent.

## Examples

### Example 1

<!-- case: ex1 -->

Key 2 is evicted when key 3 arrives, because key 1 was used more recently.

## Constraints

- `1 <= capacity <= 3000`
