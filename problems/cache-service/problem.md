# Cache Service

## Statement

Design an in-process cache service with a fixed capacity. Entries may expire after a time to live, the eviction policy is chosen when the cache is created, and the service reports hit, miss, eviction and expiration counts for monitoring. The team expects to add more eviction policies, so a policy must plug in without touching the cache's core logic.

Implement the facade class `CacheService`. Time is passed in as `timestamp`; nothing reads a clock.

## Input

- `CacheService(capacity, policy)`: an empty cache holding at most `capacity` entries, evicting by `policy`: `"LRU"`, `"LFU"` or `"FIFO"`.
- `put(timestamp, key, value, ttl)`: stores `value` under `key`. With `ttl = 0` the entry never expires; otherwise it is live at times `t` with `t < timestamp + ttl` and expired from `timestamp + ttl` on.
- `get(timestamp, key)`: reads a key.
- `remove(timestamp, key)`: deletes a key.
- `size(timestamp)`: the number of live entries.
- `stats()`: the counters.

Rules:

- An expired entry is dropped, and counted as one expiration, when an operation touches it: a `get`, `put` or `remove` of its key, a `size`, or a `put` that needs room (below). Until then it only takes up space.
- A `put` of a live key replaces its value and its time to live; nothing is evicted. A `put` of a missing or expired key inserts a new entry. When the cache already holds `capacity` entries, every expired entry is dropped first; if that frees no room, the policy evicts one live entry.
- Policies:
  - `"LRU"`: evict the least recently used entry; a use is a `get` that finds the key or a `put` of it.
  - `"LFU"`: evict the entry with the fewest uses since it was inserted (its insertion counts as one); among equal counts, the least recently used.
  - `"FIFO"`: evict the entry inserted first; uses do not matter.

## Output

- `put` returns nothing.
- `get` returns the value, or `""` when the key is missing or expired. A found key is a hit, anything else a miss.
- `remove` returns `true` when a live key was deleted, `false` otherwise.
- `size` returns the number of entries after dropping the expired ones.
- `stats` returns `[hits, misses, evictions, expirations]`.

## Examples

### Example 1

<!-- case: ex1 -->

Reading `a` makes `b` the least recently used entry, so adding `c` to the full cache evicts `b`. The cache saw two hits (`a`, `c`), one miss (`b`) and one eviction.

### Example 2

<!-- case: ex2 -->

`session` lives from 10 to 14 and has expired at 15, so the second read is a miss and drops it as an expiration. Only `user` is left.

## Constraints

- `1 <= capacity <= 1000`.
- At most 1000 calls per test.
- `0 <= ttl <= 10^9` and `1 <= timestamp <= 10^9`; timestamps never decrease within a test.
- Keys and values are 1 to 10 letters or digits.

## Follow-ups

- How would you add a size-aware policy, where entries have different weights?
- What would change if many threads used the cache at once?

## Hints

### Hint 1

Split the cache into a core (entries, expiry, statistics) and a policy that only tracks keys. The core tells the policy when a key is admitted, used or forgotten, and asks it for a victim.

### Hint 2

LRU and FIFO are both an insertion-ordered set of keys; they differ only in whether a use moves the key to the end.

### Hint 3

For LFU, keep one ordered set of keys per use count and remember the lowest count in use. For expiry, a min-heap of `(expiresAt, key)` finds the expired entries; skip pairs that no longer match the entry.
