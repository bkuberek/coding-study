# LRU Cache: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| ordered-scan | brute | O(capacity) per op | O(capacity) | capacity is tiny, or as a correctness oracle |
| hash-map-dll | optimal | O(1) per op | O(capacity) | default interview answer; shows you can build the structure |
| ordered-map | optimal | O(1) per op | O(capacity) | production code, or when the interviewer allows library structures |

All three keep the same order: least recently used first, most recently used last. Only the data structure that maintains that order changes.

## Approach: ordered-scan (List with linear scan)

### Intuition

LRU eviction only needs to know the order in which keys were last used. A plain list sorted by last use holds exactly that: the front is the next entry to discard, and the back is the entry just used. Finding a key means walking the list.

### Algorithm

1. Keep a list of `(key, value)` entries ordered from least to most recently used.
2. `get(key)`: scan for `key`. If it is absent, return `-1`. Otherwise remove the entry, append it at the back, and return its value.
3. `put(key, value)`: scan for `key`.
   1. If it is present, remove the old entry.
   2. Else, if the list holds `capacity` entries, remove the front entry.
   3. Append `(key, value)` at the back.

### Correctness

Invariant: the list holds exactly the cached entries, each key once, ordered by the time of last use. `get` and `put` both move the touched key to the back, which is the "just used" position, and no other entry changes relative order. When a new key needs room, the front entry is the one whose last use is oldest, which is exactly the LRU entry. Updating an existing key removes its old entry before appending, so the size never grows and nothing is evicted.

### Complexity

- Time: O(capacity) per op — every call scans up to `capacity` entries, and removing from the middle of an array-backed list shifts up to `capacity` elements. For the generated sequences of n calls with capacity n/10 that totals O(n^2), the `n^2` class in `meta.yaml`.
- Space: O(capacity) — one list entry per cached key.

### Trade-offs

It is short and obviously correct, which makes it the oracle for random testing. For a small capacity (a few dozen entries) a linear scan over a contiguous array is genuinely competitive. At capacity 10^4 it is one to two orders of magnitude slower than the O(1) versions: on the generated case `g1` with 10^5 calls it takes seconds in Python and close to a second on the JVM and in Node, where the others take tens of milliseconds. In an interview, mention it as the baseline and move on.

### Pitfalls and edge cases

- `put` on an existing key must not evict anything, even when the cache is full: remove the old entry first, then append.
- A miss in `get` must not reorder anything.
- Capacity 1: every new key evicts the only entry.

### Language notes

- Python: the reference keeps keys and values in two parallel lists and finds keys with `list.index`, so the scan runs in C. A hand-written loop over a list of pairs is the same O(capacity) but several times slower.
- TypeScript: `findIndex`, then `splice(index, 1)` to remove and `push` to append. `shift()` removes the front and is O(n) as well.
- Java: an `ArrayList` of a small `record Entry(int key, int value)`. `remove(int index)` removes by position; with a `List<Integer>`, `remove(key)` would pick the `remove(int index)` overload instead of `remove(Object)`, a classic boxing trap.
- Kotlin: `mutableListOf<Entry>()` with `indexOfFirst { it.key == key }` and `removeAt(index)`. Kotlin names the positional removal `removeAt`, avoiding Java's overload trap.

## Approach: hash-map-dll (Hash map plus doubly linked list)

### Intuition

The scan in the list version serves two purposes: finding the entry and moving it. A hash map finds a node in O(1). A doubly linked list moves a node you already hold to the back in O(1), because unlinking needs only its two neighbors. Combining them, the map stores key to node and the list keeps the recency order.

### Algorithm

1. Keep `nodes`, a map from key to list node, and a doubly linked list between two sentinel nodes `head` and `tail`. `head.next` is the least recently used node; `tail.prev` is the most recent. Each node stores its key and value.
2. `get(key)`: look up the node. If it is absent, return `-1`. Otherwise unlink it, append it before `tail`, and return its value.
3. `put(key, value)`:
   1. If the key has a node, update its value and unlink it.
   2. Else, if the map holds `capacity` nodes, unlink `head.next` and delete its key from the map. Then create a node and add it to the map.
   3. Append the node before `tail`.

### Correctness

Two invariants hold after every call. First, the map's keys are exactly the keys of the list nodes, each mapped to its own node. Second, the list is ordered by last use, oldest first. `get` and `put` move only the touched node, and they move it to the most recent end. Eviction removes `head.next`, the oldest node, from both the list and the map, using the key stored in the node. That is why nodes store their key. With the sentinels, every real node always has non-null `prev` and `next` neighbors, so unlinking and appending never need special cases.

### Complexity

- Time: O(1) per op — one hash lookup (O(1) on average) and a constant number of pointer updates.
- Space: O(capacity) — at most `capacity` map entries and list nodes, plus two sentinels.

### Trade-offs

This is the answer interviewers usually want, because it shows that you can combine two structures and keep them consistent. It costs more code than the library version, and each node carries two pointers on top of the key and value. Compared with ordered-scan it turns O(capacity) work into O(1).

### Pitfalls and edge cases

- Forgetting to store the key in the node leaves eviction unable to delete the evicted key from the map.
- Delete the evicted key from the map, or the map grows without bound and `get` returns evicted values.
- On an update, change the value and move the node; do not create a second node for the same key.
- Check `capacity` before inserting a new key, not after, and never on updates.
- Zero is a valid key and a valid value: test for a missing node, not for a falsy value.

### Language notes

- Python: a `_Node` class with `__slots__` saves memory per node. `dict.get(key)` returns `None` for a miss. `OrderedDict` would do all of this for you (see ordered-map).
- TypeScript: `Map<number, Entry>` for the index. Initializing `prev` and `next` to `this` keeps their type `Entry` instead of `Entry | null`, so no non-null assertions are needed. There are no parameter properties, so fields are declared and assigned explicitly.
- Java: a `private static final class Node` avoids holding a reference to the outer cache. `HashMap<Integer, Node>` boxes keys; `nodes.get(key)` returns `null` on a miss.
- Kotlin: `lateinit var prev: Node` and `next` avoid nullable links: a node's links are always set before use, thanks to the sentinels. `nodes[key] ?: return -1` handles the miss in one line.

## Approach: ordered-map (Insertion-ordered map from the standard library)

### Intuition

Every language here ships a hash map that remembers an order and can move or remove entries at its ends in O(1). Such a map is exactly a hash map plus a linked list, built and tested for you, and all the cache has to do is keep the most recent key at the end.

### Algorithm

1. Keep one ordered map from key to value, least recently used first.
2. `get(key)`: if the key is absent, return `-1`. Otherwise move it to the end and return its value.
3. `put(key, value)`: store the value, move the key to the end, and if the map now exceeds `capacity`, remove the first entry.

Java and Kotlin get steps 2 and 3 from `LinkedHashMap` itself: built with access order, it moves an entry to the end on every `get` and `put`, and the `removeEldestEntry` hook evicts after an insertion.

### Correctness

The map's iteration order is the recency order: every use moves the touched key to the end, and nothing else reorders. After a `put` of a new key the map holds at most `capacity + 1` entries, and removing the first entry removes the least recently used one, bringing the size back to `capacity`. Updating an existing key keeps the size unchanged, so nothing is removed.

### Complexity

- Time: O(1) per op — each library call (lookup, move to end, remove first) is O(1) on average.
- Space: O(capacity) — one map entry per cached key; the map evicts as soon as it exceeds `capacity`.

### Trade-offs

It is the least code and the least risk, and it is what production code should use. In an interview, offer it, but expect "now build it without the library", which is hash-map-dll. It depends on the precise semantics of each library (access order, eviction hooks, insertion-order iteration), which are worth knowing anyway.

### Pitfalls and edge cases

- In Python, assigning to an existing key of an `OrderedDict` keeps its old position: call `move_to_end` after the update.
- In TypeScript, `map.set` on an existing key also keeps its position: delete first, then set.
- In TypeScript, a fresh `keys().next()` on every eviction rescans the deleted slots at the front of the map; keep one iterator instead (see the language notes).
- In Java, the two-argument `LinkedHashMap` constructor uses insertion order. Pass `accessOrder = true` or reads will not refresh recency.
- Evict after inserting (size greater than `capacity`), or before inserting only when the key is new. Mixing the two evicts too early.

### Language notes

- Python: `collections.OrderedDict` with `move_to_end(key)` and `popitem(last=False)`. A plain `dict` also preserves insertion order (Python 3.7+), but it has no `move_to_end`. You would pop and reinsert, and find the oldest key with `next(iter(d))`.
- TypeScript: `Map` iterates in insertion order, so `delete` then `set` moves a key to the end. Find the oldest key with one iterator kept for the cache's whole life, not a fresh `keys().next()` per eviction. In V8 a deleted entry stays a hole at the front of the table until the next compaction, and every fresh iterator walks those holes again: that version grew like n^1.5 in this benchmark. The long-lived iterator is correct because Map iteration is live: it skips deleted entries and reaches keys added after it was created. Every key it has passed was evicted or moved to the end, so its next key is always the least recently used. With it, the approach runs about 1.2 times slower than the hand-built list.
- Java: `new LinkedHashMap<>(16, 0.75f, true)` with an anonymous subclass overriding `removeEldestEntry`. `getOrDefault` also counts as an access in access-order mode. Prefer composition (a private field) over `extends LinkedHashMap`, which would expose every map method on the cache.
- Kotlin: the same `LinkedHashMap` through an `object :` expression. `entries[key] ?: -1` covers the miss, and the override's parameter type is `MutableMap.MutableEntry<Int, Int>?` because it comes from Java.
