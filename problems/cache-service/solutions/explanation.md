# Cache Service: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| policy-seam | optimal | O(1) per get and remove; O(log n) amortized per put and size | O(n + w) | default answer; a new policy never touches the core |

Here `n` is the capacity and `w` the number of writes with a time to live, which bounds the expiry heap.

## Approach: policy-seam (Cache core with pluggable eviction policies and an expiry heap)

### Intuition

Three concerns change for different reasons: what is stored and until when (the core), which entry to sacrifice when full (the policy), and what the operators want to observe (the counters). The policy only needs to know about keys: when one arrives, when it is used, when it leaves, and which one it would give up. With that four-method interface, LRU, FIFO and LFU are each a small class, and the core never branches on the policy's name.

Expiry is the other half. Checking an entry's own expiry when it is read is trivial; the hard case is a full cache that should reclaim expired space before evicting live data. A min-heap of expiry times answers "which entries are expired by now?" without scanning, and lazy deletion (skip heap pairs that no longer match their entry) keeps updates cheap.

### Algorithm

1. `live(now, key)`: when the entry exists and `now >= expiresAt`, drop it, count an expiration and report it missing; otherwise return it.
2. `put(t, key, value, ttl)`: compute `expiresAt` (none for `ttl = 0`). If `live` finds the key, overwrite value and expiry and `touch` the policy. Otherwise make room, insert the entry and `admit` the key. Push `(expiresAt, key)` on the heap when it expires.
3. Making room: when the cache is full, pop every heap pair due by `t`; a pair whose expiry still equals its entry's expiry drops that entry as an expiration, any other pair is stale. If still full, drop `policy.victim()` and count an eviction.
4. `get`: a live key is a hit and a `touch`; anything else is a miss. `remove`: drop a live key. `size`: pop every due pair as in step 3, then count the entries. `stats`: the four counters.
5. Policies: `LruPolicy` keeps an insertion-ordered set; `touch` moves the key to the end; the victim is the first key. `FifoPolicy` is the same with a `touch` that does nothing. `LfuPolicy` keeps a count per key and one insertion-ordered set per count; `touch` moves a key to the next count's set (at its end), `admit` puts it at count 1 and resets the lowest-count pointer to 1, and the victim is the first key of the lowest non-empty count.

### Correctness

Invariant 1: the policy tracks exactly the keys in `entries`. Every insertion calls `admit`, and every removal (explicit, expiration or eviction) goes through `drop`, which calls `forget`.

Invariant 2: every entry with an expiry has a heap pair with that exact expiry. `put` pushes one whenever it sets an expiry. Older pairs of the same key become stale, and the equality check skips them, so a pair can only drop an entry whose current expiry it matches, which by step 3's condition is due.

Victims are right for each policy: in LRU every use moves the key to the end, so the first key is the least recently used; in FIFO uses do not move keys, so the first key is the oldest insertion. In LFU, each count's set is ordered by when keys reached that count, which is their last use, so the first key of the lowest count is the least frequently used, ties broken by least recent use. The lowest-count pointer never exceeds the true minimum because counts only grow and new keys reset it to 1, so scanning upward from it finds the true minimum.

Because expired entries are drained before the policy is asked, an eviction only happens when every entry in the cache is live, matching the rule.

### Complexity

- Time: O(1) per get and remove; O(log n) amortized per put and size — map and ordered-set operations are O(1) on average; a timed put pushes one heap pair; each pair is popped once over the whole run. The LFU pointer only moves up between insertions, so its scans are paid for by the uses that raised the counts.
- Space: O(n + w) — at most `capacity` entries plus their policy bookkeeping, and one heap pair per timed write until it comes due.

### Trade-offs

- Scanning all entries for expired ones when the cache is full is simpler and needs no heap, but costs O(n) on every insertion into a full cache. With small capacities that is acceptable; the heap is the scalable choice.
- Lazy deletion trades memory for simplicity: rewriting a key leaves its old pair in the heap until it comes due. A heap with decrease-key or an indexed structure removes it at once, at the cost of much more code.
- Many caches expire entries proactively with a background sweeper. That needs a clock and threads, which this design avoids on purpose: expiry is observed only when an operation touches it, so the behavior is deterministic.
- An LFU without aging lets an entry that was hot long ago stay forever. Real systems decay counts (or use variants such as LFU with a window); that change lives entirely in `LfuPolicy`.

### Pitfalls and edge cases

- Updating a live key must not evict anything, even when the cache is full.
- A `put` of an expired key is an expiration plus a fresh insertion: under LFU its count restarts at 1.
- Drain expired entries before evicting; evicting a live entry while an expired one occupies space is the classic bug.
- Skip stale heap pairs by comparing expiry times; otherwise a rewritten key is dropped at its old expiry.
- A miss is counted for expired keys as well as missing ones; the expiration is counted once, when the entry is dropped.
- FIFO must ignore both reads and updates.

### Language notes

- Python: `OrderedDict.move_to_end` is the LRU move; `FifoPolicy` subclasses `LruPolicy` and overrides `touch` with a docstring body; `heapq` holds `(expiresAt, key)` tuples. `typing.Protocol` states the policy interface.
- TypeScript: a `Set` preserves insertion order, so delete-then-add moves a key to the end and `values().next().value` is the oldest. There is no heap in the standard library, so the reference includes a small binary heap.
- Java: `LinkedHashSet` for the ordered sets, `PriorityQueue` with `Comparator.comparingLong` for expiries, and nullable `Long` for "never expires" (compare only after the null check). `stats` returns an `int[]`.
- Kotlin: the same collections with `+=` and `-=` on mutable sets, `compareBy(Expiry::expiresAt)` for the heap, `isNullOrEmpty()` for the LFU scan, and an `open class` so `FifoPolicy` can override one method.
- Go: neither the standard library nor the language has an insertion-ordered set, so `orderedKeys` pairs a `container/list` with a `map[string]*list.Element`; that gives O(1) move-to-back and removal, and `fifoPolicy` embeds the LRU policy and shadows `touch` with an empty method, the Go form of the Python subclass. `container/heap` needs the five-method `expiryHeap` type, ordered by expiry time and then key.
- Rust: there is no ordered map or intrusive list either, and a node that points at its neighbors would need `Rc<RefCell<..>>`, so `OrderedKeys` keeps its links in a `Vec` and joins them by slot index (with sentinels and a list of spare slots), plus a `HashMap` from key to slot; every operation is O(1). `FifoPolicy` wraps `LruPolicy` and ignores `touch`. Policies are `Box<dyn EvictionPolicy>`; `victim` takes `&mut self` because LFU moves its lowest-count pointer, and the expiry heap is a `BinaryHeap<Reverse<(i64, String)>>`.
