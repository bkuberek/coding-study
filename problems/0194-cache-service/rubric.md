# Cache Service: Rubric

## Responsibilities

- [ ] The cache core alone owns entries, values, expiry times and statistics.
- [ ] The eviction policy alone owns the order of keys and chooses the victim; it never sees values or timestamps.
- [ ] Expiry is decided in one place (an entry's `expired(now)` check), not repeated in every method.
- [ ] Statistics are updated where the event happens (hit, miss, eviction, expiration), so their meaning matches the rules exactly.

## Extension points

- [ ] A new eviction policy is one class implementing the policy interface plus a registry entry; the core does not change.
- [ ] Switching how expired entries are found (scan, heap, timer wheel) changes the core's expiry index only.
- [ ] New statistics (for example a hit rate) are computed from the existing counters without touching policies.

## Patterns

- [ ] Eviction is a Strategy behind a narrow interface: `admit`, `touch`, `forget`, `victim`.
- [ ] FIFO reuses LRU's ordered set and only overrides `touch`, showing the two policies differ in one decision.
- [ ] Expiry uses lazy deletion: stale heap pairs are skipped instead of being removed eagerly.

## Testability

- [ ] Every time-dependent rule takes `timestamp` as an argument; there is no clock or background thread.
- [ ] Each policy can be tested alone by calling `admit`, `touch` and `forget` and checking `victim`.
- [ ] The counters in `stats` make hidden events (evictions, expirations) observable from the public API.

## Reference design

```text
CacheService (core)
 ├── entries: key -> Entry(value, expiresAt)
 ├── expiries: min-heap of (expiresAt, key), stale pairs skipped
 ├── counters: hits, misses, evictions, expirations
 └── policy: EvictionPolicy ◁── LruPolicy ◁── FifoPolicy
                             ◁── LfuPolicy (count -> ordered keys, lowest count in use)
```

All reads of an entry go through `live(now, key)`, which drops and counts an expired entry and otherwise returns it, so `get`, `put` and `remove` share one expiry rule. A `put` of a new key into a full cache first drains the heap of every pair due by `now` (a pair whose expiry no longer matches its entry is stale and skipped), and only then asks the policy for a victim. That order keeps evictions for live data only.

The policy interface has four calls. `LruPolicy` is an insertion-ordered set where `touch` moves a key to the end; `FifoPolicy` inherits it with a `touch` that does nothing. `LfuPolicy` keeps a use count per key and one ordered set per count, so the victim is the first key of the lowest non-empty count. Its lowest-count pointer is reset to 1 on every insertion and only ever moves up, which is enough because counts never decrease.

Trade-offs: the heap makes expiry cost O(log n) per timed `put`, where a scan of all entries would be O(n) whenever the cache is full. Lazy deletion leaves stale pairs in the heap until they come due, so memory is bounded by the number of timed writes, not by the capacity; periodic compaction would bound it if that mattered. The policy never sees time or values, which keeps it reusable but means a policy based on entry size would need a wider interface.
