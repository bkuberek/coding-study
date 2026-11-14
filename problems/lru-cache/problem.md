# LRU Cache

## Statement

Build a key-value cache with a fixed number of slots. When the cache is full and a new key arrives, it makes room by discarding the entry that has gone unused for the longest time. This rule is called "least recently used" (LRU) eviction.

An entry counts as used whenever it is read with `get` or written with `put`. Implement the class `LRUCache`:

- `LRUCache(capacity)` creates an empty cache that holds at most `capacity` entries.
- `get(key)` returns the value stored for `key` and marks the entry as just used. If `key` is not in the cache, it returns `-1` and changes nothing.
- `put(key, value)` stores `value` under `key` and marks the entry as just used. If `key` is already present, its value is replaced and no other entry is discarded. If `key` is new and the cache is already full, the least recently used entry is discarded first.

Reference: this is our own wording of LeetCode problem 146, [LRU Cache](https://leetcode.com/problems/lru-cache/).

## Input

- Constructor `capacity`: the maximum number of entries the cache holds.
- `get(key)`: `key` is the key to look up.
- `put(key, value)`: `key` is the key to store, `value` the value to associate with it.

Each test is a sequence of calls: the constructor first, then `get` and `put` calls in order.

## Output

- `get` returns the stored value, or `-1` when the key is absent.
- `put` returns nothing.

The expected output of a test lists one result per call, with `null` for the constructor and for every `put`.

## Examples

### Example 1

<!-- case: ex1 -->

With room for two entries, keys 4 and 9 fill the cache. Reading 4 makes 9 the least recently used entry, so storing 6 discards 9. Afterwards 9 is gone (`-1`) while 6 and 4 are still present.

### Example 2

<!-- case: ex2 -->

Storing 7 a second time replaces its value with 3 and counts as a use, so when 9 arrives the cache discards 8, not 7.

## Constraints

- `1 <= capacity <= 10^4`
- `0 <= key <= 10^5`
- `0 <= value <= 10^9`
- At most `10^5` calls to `get` and `put` in total.

## Follow-ups

- Can every `get` and `put` run in O(1) time, independent of `capacity`?
- How would you add a time-to-live, so that entries also expire after a fixed duration?
- What changes if several threads use the cache at the same time?

## Hints

### Hint 1

The cache has to answer two questions quickly: where is the entry for this key, and which entry was used longest ago?

### Hint 2

A hash map answers the first question in O(1). For the second, keep the entries in a sequence ordered by last use, where moving an entry to the "just used" end is cheap.

### Hint 3

In a doubly linked list, a node you already hold can be removed and re-inserted at one end in O(1). Store the list node in the hash map, and keep the key inside the node so that eviction can also delete the key from the map.

### Hint 4

Dummy head and tail nodes remove the special cases for an empty list and for unlinking the first or last node.
