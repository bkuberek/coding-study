# Snapshot Array: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| scan-log | brute | O(1) set and snap, O(w) get | O(w) | there are few reads, or as a correctness oracle |
| history-binary-search | optimal | O(1) set and snap, O(log w) get | O(length + w) | default answer |

Here `w` is the number of `set` calls so far. As in the other design problems, the measured class on the ladder describes the whole generated sequence of calls.

## Approach: scan-log (Append every write to a log and scan it backwards)

### Intuition

Record every write in one log and tag it with how many snapshots had been taken when it happened. A write tagged `t` happened before snapshot `t` was taken, so a read of snapshot `snapId` only needs the newest write to that position whose tag is at most `snapId`.

### Algorithm

1. `set(index, value)` appends `(index, value, snaps)` to the log, where `snaps` is the number of snapshots taken so far.
2. `snap()` returns `snaps` and then increments it.
3. `get(index, snapId)` scans the log from the newest entry and returns the value of the first entry with this `index` and a tag `<= snapId`. If there is none, it returns 0.

### Correctness

Tags never decrease along the log, because `snaps` only grows. A write tagged `t` was made after snapshots `0..t-1` and before snapshot `t`, so it is part of every snapshot with id at least `t` until a newer write replaces it. The newest write to `index` with a tag `<= snapId` is therefore exactly the value that snapshot `snapId` saw; a position never written before that snapshot reads 0.

### Complexity

- Time: O(1) set and snap, O(w) get — `set` and `snap` are appends or increments; `get` may scan the whole log of `w` writes.
- Space: O(w) — one log entry per write.

### Trade-offs

Copying the whole array at every `snap` is the other naive idea: O(length) per `snap` and O(length * snaps) memory, which is why it is not the reference here. The log is cheap to write and quadratic over a long run of reads. It is a trustworthy oracle, since it follows the definition.

### Pitfalls and edge cases

- Compare tags with `<= snapId`, not `<`: a write made before `snap()` returned id `t` belongs to snapshot `t`.
- A position that was never written before the snapshot reads 0, even if it is written later.

### Language notes

- Python: a list of tuples scanned with `reversed(...)`.
- TypeScript: the constructor parameter is unused, so it is named `_length` to satisfy `noUnusedParameters`.
- Java: log entries are `int[]` triples; the constructor ignores `length`.
- Kotlin: destructuring an `IntArray` into `(written, value, snapsBefore)` keeps the scan readable.

## Approach: history-binary-search (Per-position change history searched by snapshot id)

### Intuition

For each position, the changes form a list sorted by snapshot id. A snapshot sees the last change made at or before it, and finding that is a binary search.

### Algorithm

1. Keep, for every position, a list of `(snapshot id, value)` pairs with strictly increasing ids.
2. `set(index, value)`: if the last pair of this position has the current snapshot id, overwrite its value; otherwise append `(snaps, value)`.
3. `snap()` returns `snaps` and increments it.
4. `get(index, snapId)`: binary-search the last pair whose id is `<= snapId`. Return its value, or 0 if there is none.

### Correctness

Ids in each list are strictly increasing, because a new pair is appended only with an id larger than the last one, and a second write within the same snapshot overwrites instead. Each pair holds the last value written to that position before the snapshot with that id was taken. For a given `snapId`, the pair with the largest id not above it is the latest change that snapshot can see, so its value is the answer; no such pair means no write happened before the snapshot.

### Complexity

- Time: O(1) set and snap, O(log w) get — `set` and `snap` are amortized O(1); `get` is one binary search over a history of at most `w` pairs.
- Space: O(length + w) — one list per position plus at most one pair per write.

### Trade-offs

Overwriting within the same snapshot keeps each list short. When `length` is huge and writes are rare, allocate the lists lazily in a map keyed by position. Memory does not depend on the number of snapshots, which a design that stores something per snapshot could not say.

### Pitfalls and edge cases

- Without the overwrite rule the lists still work, but they hold duplicate ids and the search must find the last of the equal ids, so use an upper bound (`bisect_right`), not a lower bound.
- A `snapId` smaller than the first change of a position returns 0, not the first value.

### Language notes

- Python: `bisect_right(entries, snap_id, key=itemgetter(0))` is the library upper bound over the id of each pair.
- TypeScript: two parallel arrays per position (ids and values) and a hand-written upper bound, because there is no library search.
- Java: an `ArrayList` of `int[]` pairs per position inside an `ArrayList`, which avoids generic array creation; the search is hand-written.
- Kotlin: `Array(length) { mutableListOf<IntArray>() }` and a hand-written upper bound. The library's `binarySearch` reports a missing key as `-(insertion point) - 1`, so an upper bound loop is clearer.
