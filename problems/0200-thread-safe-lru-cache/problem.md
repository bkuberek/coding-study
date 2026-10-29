# Thread-Safe LRU Cache

## Statement

Build a least recently used (LRU) cache that many threads can share. The cache has a fixed number of slots. When it is full and a new key arrives, it discards the entry that has gone unused for the longest time. An entry counts as used whenever it is read with `get` or written with `put`.

The single-threaded version of this cache is a classic; here every method may run at the same time as any other, and the cache must still behave as if the calls happened one after another, in some order.

Implement the class `LRUCache`:

- `LRUCache(capacity)` creates an empty cache that holds at most `capacity` entries.
- `get(key)` returns the value stored for `key` and marks the entry as just used. If `key` is not in the cache, it returns `-1` and changes nothing.
- `put(key, value)` stores `value` under `key` and marks the entry as just used. If `key` is already present, its value is replaced and no entry is discarded. If `key` is new and the cache is full, the least recently used entry is discarded first.
- `size()` returns the number of entries in the cache.

Reference: the cache rules are our own wording of LeetCode problem 146, [LRU Cache](https://leetcode.com/problems/lru-cache/); the concurrency requirements are added.

## Input

- Constructor `capacity`: the maximum number of entries the cache holds.
- `get(key)`: the key to look up.
- `put(key, value)`: the key to store and the value to associate with it.
- `size()`: no arguments.

Sequential tests are a sequence of calls on one worker: the constructor first, then method calls in order. Stress tests call the same methods from many workers at once.

## Output

- `get` returns the stored value, or `-1` when the key is absent.
- `put` returns nothing.
- `size` returns the number of entries, from 0 to `capacity`.

The expected output of a sequential test lists one result per call, with `null` for the constructor and for every `put`.

## Examples

### Example 1

<!-- case: ex1 -->

With room for two entries, keys 4 and 9 fill the cache. Reading 4 makes 9 the least recently used entry, so storing 6 discards 9. Afterwards 9 is gone while 6 and 4 are present.

### Example 2

<!-- case: ex2 -->

Storing 7 a second time replaces its value and counts as a use, so when 9 arrives the cache discards 8, not 7.

## Constraints

- `1 <= capacity <= 10^4`
- `0 <= key <= 10^5`
- `0 <= value <= 10^9`

## Concurrency

`get`, `put` and `size` are called concurrently by many workers. No method waits for anything but a lock.

- Every call is atomic: the cache behaves as if the calls ran one at a time in some order consistent with each worker's own order. In particular, a `get` that finds a key also moves it to the most recently used position, so `get` changes the cache just like `put` does.
- A hit returns a value that was stored for exactly that key.
- `size` never reports more than `capacity`.
- When the workers are done, the cache must still be a valid LRU cache: the stress tests then store `capacity` fresh keys and expect to read all of them back, with `size` equal to `capacity`. A recency list that lost or duplicated an entry fails this check.

Java and Kotlin run on platform threads and on virtual threads, Python and Rust on threads, and Go on goroutines. In Rust the threads share one cache, so its methods take `&self`. A passing stress run is evidence of thread safety, not proof.

## Follow-ups

- Why does a read-write lock not help here, even when most calls are `get`?
- Splitting the cache into independently locked segments by key hash scales better. What exactly does it give up?
- How do production caches such as Caffeine keep `get` almost lock-free while still evicting in (approximately) LRU order?

## Hints

### Hint 1

Start from the single-threaded design: a hash map from key to node, and a doubly linked list of nodes ordered by recency.

### Hint 2

Which methods change the linked list? Both of them: a hit in `get` moves its node to the most recent end.

### Hint 3

Make every public method one critical section under the same lock. The map and the list must change together, so they need the same lock.
