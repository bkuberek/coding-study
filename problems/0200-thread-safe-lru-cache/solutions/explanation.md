# Thread-Safe LRU Cache: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| locked-dll | optimal | O(1) per op | O(capacity) | default interview answer; you build the structure and make it atomic |
| locked-linked-map | optimal | O(1) per op | O(capacity) | production code, or when library structures are allowed |

Both use the classic O(1) LRU structure and one lock around every public method. The interesting decisions are not in the data structure but in the locking: what must be atomic, and why finer-grained schemes either break the LRU contract or need a very different design.

## Approach: locked-dll (Hash map and doubly linked list under one lock)

### Intuition

The single-threaded cache keeps two structures in sync: a hash map from key to node, and a doubly linked list ordered from least to most recently used. Every operation touches both, and between its steps the two disagree, for example a node that is already unlinked but still in the map. If another thread sees that intermediate state, the structure breaks. So each operation must run entirely under one lock, and since both structures change together, it must be the same lock for both and for every method, `get` included.

### Algorithm

1. State: `nodes`, a hash map from key to node; a doubly linked list between sentinels `head` and `tail` (`head.next` is the least recently used node); one lock.
2. `get(key)`: under the lock, look up the node; if absent return `-1`; otherwise unlink it, append it before `tail`, and return its value.
3. `put(key, value)`: under the lock, if the key has a node, update its value and move it before `tail`. Otherwise, if the map holds `capacity` nodes, unlink `head.next` and remove its key from the map; then create a node, add it to the map and append it.
4. `size()`: under the lock, return the map's size.

### Correctness

Inside the lock the code is the sequential algorithm, whose invariants hold after every call: the map's keys are exactly the list's nodes, and the list is ordered by last use. Because every public method holds the lock for its whole duration, no thread ever observes the intermediate states, and the calls are linearizable in the order they acquire the lock: each one sees the result of all calls before it. The lock's release and acquire also order memory, so on the JVM a thread always sees the pointer updates of the previous holder.

### Complexity

- Time: O(1) per op — one hash lookup and a constant number of pointer updates, plus an uncontended lock acquisition.
- Space: O(capacity) — at most `capacity` map entries and nodes, plus two sentinels.

### Trade-offs

One lock serializes every call, so throughput is limited to one operation at a time. For a cache, that is usually fine: the critical section is tiny, far shorter than the work that the cache saves. When it is not, the options trade exactness for scalability:

- Read-write lock: no help, because a hit is a write to the recency list. Taking the read lock in `get` is exactly the `unlocked-get` bug.
- Lock striping (N independent LRU segments by key hash): scales nearly linearly, but each segment evicts its own least recently used entry, so the global eviction order is only approximately LRU, and a hot segment evicts while others have room.
- Buffered recency (Caffeine, Guava): `get` reads a `ConcurrentHashMap` without blocking and records the access in a lossy ring buffer; a single thread later replays the buffer into the recency order under a lock. Eviction is close to LRU, not exact.

In an interview, write the single-lock version, then discuss these trade-offs; claiming exact LRU with striping is the usual mistake.

### Pitfalls and edge cases

- `get` must take the lock: it is a write.
- Evict before inserting when the key is new and the cache is full, and never on an update of an existing key.
- Store the key in the node, so that eviction can remove the map entry of `head.next`.
- `size` must take the lock as well, or the JVM may return a stale value.
- Do not call out to user code (listeners, loaders) while holding the lock; a slow or reentrant callback would block every thread.

### Language notes

- Java: a `ReentrantLock` with `try`/`finally`. On JDK 21, `synchronized` methods would pin a virtual thread to its carrier while it holds the monitor; with such short critical sections this is harmless, but `ReentrantLock` avoids it entirely. `ConcurrentHashMap` alone does not help, because the map and the list must change together.
- Kotlin: the same JDK lock with `lock.withLock { }`, whose inline lambda allows the early `return -1`. With coroutines the same design uses a `kotlinx.coroutines.sync.Mutex`; holding it never blocks a thread, but it must not be held across a suspending call such as loading a missing value. Coroutines are not autograded here.
- Python: one `threading.Lock` around each method. Single operations on a `dict` are atomic under the GIL, but the five pointer updates of a move are separate statements, and a thread can be switched out between any two of them.

## Approach: locked-linked-map (Access-ordered map from the standard library under one lock)

### Intuition

Java's `LinkedHashMap` and Python's `OrderedDict` are a hash map and a linked list in one structure. In access order, `LinkedHashMap` moves an entry to the end on every `get` and `put`, and `removeEldestEntry` evicts the first entry; `OrderedDict.move_to_end` and `popitem(last=False)` do the same by hand. The structure still is not thread-safe, so the lock stays.

### Algorithm

1. Java and Kotlin: create `LinkedHashMap(16, 0.75f, true)` (access order) whose `removeEldestEntry` returns `size() > capacity`.
2. Python: an `OrderedDict`.
3. `get`: under the lock, look the key up (Java moves it automatically; Python calls `move_to_end`) and return the value or `-1`.
4. `put`: under the lock, store the value (Python: then `move_to_end`); if the size exceeds `capacity`, the eldest entry is removed (Java: by `removeEldestEntry`; Python: `popitem(last=False)`).
5. `size`: under the lock, return the size.

### Correctness

The library structure implements the LRU order correctly for sequential use, and the lock makes every call sequential. As in `locked-dll`, the calls are linearizable in lock order.

### Complexity

- Time: O(1) per op — hash operations plus constant-time list moves inside the library structure.
- Space: O(capacity) — one entry per cached key.

### Trade-offs

Less code and fewer places to get the pointer updates wrong, at the cost of showing less in an interview. `Collections.synchronizedMap(new LinkedHashMap<>(..., true))` looks like a shortcut but locks each map call separately; that is enough for this API, but a compound action such as "get, and put if absent" would still need external locking.

### Pitfalls and edge cases

- `LinkedHashMap` must be created in access order (`true`), or it evicts by insertion order: that is a FIFO cache, not LRU.
- In access order, `LinkedHashMap.get` modifies the map, so even read-only-looking code needs the lock; iterating it while another thread calls `get` throws `ConcurrentModificationException`.
- In Python, `OrderedDict.__setitem__` on an existing key keeps its position; the explicit `move_to_end` makes an update count as a use.

### Language notes

- Java: an anonymous subclass of `LinkedHashMap` overriding `removeEldestEntry`, guarded by a `ReentrantLock`.
- Kotlin: the same JDK class via `object : LinkedHashMap<Int, Int>(16, 0.75f, true)`; with coroutines a `Mutex` replaces the lock.
- Python: `collections.OrderedDict` with `move_to_end` and `popitem(last=False)`; `functools.lru_cache` is thread-safe but caches function results, not a key-value API.

## Broken: no-lock (No lock)

### Bug

Nothing is synchronized, so threads interleave inside the multi-step updates of the map and the list. Two `put` calls can evict the same eldest node: in Python the second `del` raises `KeyError` (`ERROR`), on the JVM the map silently grows past `capacity` (`bounds` on `size`). Two moves to the tail at once lose a node from the list while it stays in the map, so it is never evicted; the final flush of fresh keys then finds an old key still in place of a new one (`final.expected`), or an eviction reaches the sentinel and fails (`ERROR`).

### Failing interleaving

1. The cache is full; A and B both `put` a new key.
2. A reads `eldest = head.next`, node X, and is switched out.
3. B reads the same X, unlinks it and removes X's key from the map.
4. A resumes and unlinks X again, which rewires X's stale neighbors and drops a live node from the list, then fails to remove X's key, which is already gone.

### Fix

Hold one lock for the whole of every public method, as in the `locked-dll` approach.

## Broken: unlocked-get (Get treated as a read)

### Bug

`put` and `size` take the lock, but `get` does not, on the reasoning that it only reads. A hit in an LRU cache is a write: it unlinks the node and appends it at the tail. Two concurrent hits both read the same `tail.prev` and both append after it, so one node falls out of the list while staying in the map; a hit racing with a locked `put` rewires pointers in the middle of an eviction. The broken list shows up in the final flush (`final.expected`), as a growing `size`, or as an exception when an eviction reaches a sentinel.

### Failing interleaving

1. Readers A and B call `get(1)` and `get(2)` on a full cache.
2. A unlinks node 1, reads `last = tail.prev` (node 7) and is switched out.
3. B unlinks node 2, also reads `last` as node 7, and links node 2 between 7 and the tail.
4. A resumes and links node 1 between 7 and the tail, overwriting `7.next` and `tail.prev`: node 2 is now in the map but unreachable in the list, so it can never be evicted.

### Fix

Take the same lock in `get` as in `put`, as in the `locked-dll` approach: every method that changes the recency order is a writer.
