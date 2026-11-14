# Time-Based Key-Value Store: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| scan-history | brute | O(k) per get | O(n) | histories stay short, or as a correctness oracle |
| binary-search-history | optimal | O(log k) per get | O(n) | default answer |

`n` is the number of `set` calls and `k` the number of writes to the key being read. Both approaches make `set` O(1) amortized.

## Approach: scan-history (Scan the key's history from the newest entry)

### Intuition

Keep, for every key, the list of its writes in the order they arrived; since timestamps increase, that list is sorted by time. To read the value at time `t`, walk the list from the newest write backwards and stop at the first one made at or before `t`.

### Algorithm

1. Keep a hash map from key to a list of `(timestamp, value)` pairs.
2. `set(key, value, timestamp)`: append the pair to the key's list, creating the list if needed.
3. `get(key, timestamp)`: for each pair in the key's list from last to first, if its timestamp is at most `timestamp`, return its value. If none qualifies, or the key is unknown, return `""`.

### Correctness

Writes to a key are appended in increasing timestamp order, so the list is sorted. Scanning from the end, the first pair with timestamp at most `t` is the one with the largest such timestamp, which is exactly the value the key held at `t`. If no pair qualifies, every write happened after `t` and the answer is `""`.

### Complexity

- Time: O(k) per get — a read may walk the key's whole history; `set` is O(1) amortized. The generator spreads reads uniformly over time with at most 4 keys, so a read scans about half of a history that grows with n, and a sequence of n calls costs O(n^2) in total.
- Space: O(n) — one stored pair per `set` call.

### Trade-offs

Simple, obviously correct, and fast when reads mostly ask about recent times (the scan stops after a few steps). It degrades when keys accumulate long histories and reads ask about the past, which is exactly what the follow-up interviewers probe. It is the oracle for the optimal version.

### Pitfalls and edge cases

- Scan from the newest entry: scanning from the oldest and stopping at the first match returns the earliest qualifying write, not the latest.
- An unknown key and a read before the first write both return `""`; neither may throw.
- The comparison is `<=`: a read at exactly the write's timestamp sees that write.

### Language notes

- Python: `reversed(list)` iterates backwards without copying; `dict.setdefault(key, [])` creates the list on first use.
- TypeScript: `Map<string, ...>` rather than an object, so keys such as `constructor` cannot collide with inherited properties.
- Java: a `record Entry(int timestamp, String value)` keeps the pair immutable; `computeIfAbsent` creates the list on first use.
- Kotlin: `lastOrNull { it.timestamp <= timestamp }` scans from the end of the list, which is this approach in one call.
- Go: reading a missing key from a map returns a nil slice, and `append` on a nil slice allocates it, so `m.history[key] = append(m.history[key], e)` needs no "create on first use" step. A small struct `entry` holds the pair, and a backwards index loop replaces `reversed`.
- Rust: `history.entry(key).or_default().push(..)` creates the list on first use, and `entries.iter().rev()` walks backwards without copying. `get` returns an owned `String`, so the stored value is cloned.

## Approach: binary-search-history (Binary search in the key's history)

### Intuition

Each key's history is sorted by timestamp for free, because writes arrive in time order. A read is then a classic search in a sorted array: find the last timestamp that is not greater than the query. That is the "upper bound" (the number of entries with timestamp at most `t`) minus one, found in O(log k).

### Algorithm

1. Keep a hash map from key to two parallel lists: timestamps and values.
2. `set`: append the timestamp and the value to the key's lists.
3. `get(key, t)`: if the key is unknown, return `""`. Otherwise binary search for `count`, the number of timestamps at most `t`: with `low = 0`, `high = size`, while `low < high` take `middle`; if `timestamps[middle] <= t` set `low = middle + 1`, else `high = middle`. Then `count = low`.
4. Return `values[count - 1]` if `count > 0`, else `""`.

### Correctness

The timestamps of one key are strictly increasing, so "timestamp at most `t`" is true for a prefix of the list and false for the rest. The loop keeps the invariant "entries before `low` are at most `t`, entries from `high` on are greater", so it ends at the prefix length `count`. The entry at `count - 1` is the latest write at or before `t`; `count == 0` means every write is later than `t`.

### Complexity

- Time: O(log k) per get — one binary search over the key's k entries; `set` is an O(1) amortized append.
- Space: O(n) — one timestamp and one value per `set` call.

### Trade-offs

It is the expected answer and costs nothing extra over the brute force at write time. It depends on writes arriving in time order; with out-of-order writes each history must stay sorted under insertion, which calls for a balanced tree (Java `TreeMap.floorEntry`, Kotlin the same class) or sorted-list insertion at O(k) per write.

### Pitfalls and edge cases

- Use the upper bound (first timestamp greater than `t`) and step back one. A lower bound (first timestamp at least `t`) is off by one when no write happened exactly at `t`.
- Guard `count == 0` before indexing `count - 1`.
- Store values per key; one global list of all writes would make a read search through other keys' entries.

### Language notes

- Python: `bisect.bisect_right(times, t)` is exactly the upper bound; parallel lists keep the timestamps as plain `int`s so the search does not compare tuples.
- TypeScript: there is no standard binary search, so the loop is written out; `>>> 1` floors the midpoint.
- Java: timestamps live in a growable `int[]` to avoid boxing every value into an `Integer`; `TreeMap<Integer, String>.floorEntry(t)` is the shortest correct alternative at O(log k) per call, with a larger constant and allocation per entry.
- Kotlin: `List<Int>.binarySearch(t)` returns the index on a hit and `-(insertionPoint) - 1` on a miss; timestamps are distinct, so a hit's index plus one is the count, and a miss's insertion point is the count.
- Go: `sort.Search(n, f)` returns the first index where `f` is true; with `f` meaning "written after `timestamp`" that index is the number of writes at or before it, the upper bound. The history is a slice of `entry` structs, so the closure reads `entries[i].timestamp` directly and no parallel slice is needed.
- Rust: `partition_point` is the upper bound. It takes a predicate on each element, so one `Vec<(i32, String)>` sorted by timestamp is enough; the closure looks at the timestamp only and never compares the strings.
