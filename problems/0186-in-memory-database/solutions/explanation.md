# In-Memory Database: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| versioned-fields | optimal | O(log v) per field operation; O(f log f + f log v) per scan | O(w) | default answer; it survives all four levels without a rewrite |

Here `f` is the number of fields in the scanned record, `v` the number of versions of one field, and `w` the number of writes so far.

## How the design grows level by level

The trap in a progressive problem is writing level 1 so tightly that level 4 forces a rewrite. The reference ends where a candidate would end, but it helps to see each step.

| Level | Change | Structure after the level |
|-------|--------|---------------------------|
| 1 | `set`, `get`, `remove` on one field | `records: key -> (field -> value)` |
| 2 | Sorted scans, optionally by prefix | Unchanged: collect matching fields, then sort |
| 3 | Fields expire at `timestamp + ttl` | The value becomes `(value, expiresAt)`; every read compares `expiresAt` with the time it reads at |
| 4 | Reads at an earlier moment | The value becomes a history of `(since, value or deleted, expiresAt)`; a read binary-searches the version in force |

Two choices made early make the later levels cheap. First, route every read through one helper, "the value of this field at moment `m`": level 3 then changes one function, and level 4 only passes a different moment. Second, treat a deletion as a write of "nothing" rather than as removing the entry, so the history of level 4 can say "missing since 9".

## Approach: versioned-fields (Per-field version history)

### Intuition

Never overwrite anything. Each field keeps the list of its versions, and because timestamps only increase, appending keeps that list sorted by time. "What is the value now" and "what was the value at 7" become the same question: find the last version that started at or before the moment, then check that it is not a deletion and had not expired by then.

### Algorithm

1. Keep `records`, a map from record key to a map from field name to that field's history.
2. A version is `(since, value, expiresAt)`: `value` is absent for a deletion, and `expiresAt` is absent when the value never expires.
3. `valueAt(field, m)`: binary-search the history for the last version with `since <= m`. Return its value when it exists, is not a deletion, and `m < expiresAt` (or never expires); otherwise nothing.
4. Level 1: `set` appends `(timestamp, value, never)`. `get` returns `valueAt(timestamp)` or `""`. `remove` returns `false` when `valueAt(timestamp)` is empty; otherwise it appends `(timestamp, deleted, never)` and returns `true`.
5. Level 2: `scan` and `scanByPrefix` visit the fields of the record, keep those whose name starts with the prefix and whose `valueAt(timestamp)` exists, sort them by name, and format `field(value)`.
6. Level 3: `setWithTtl` appends `(timestamp, value, timestamp + ttl)`. Nothing else changes, because every read already goes through `valueAt`.
7. Level 4: `getAt` and `scanAt` are `get` and `scan` with `atTimestamp` passed as the moment.

### Correctness

Invariant: each history lists every write and deletion of its field in increasing `since` order, because calls arrive with increasing timestamps and each call appends at most one version. The state at moment `m` is defined by the calls with timestamps at most `m`; for one field the only call that matters is the last of them, which is exactly the last version with `since <= m`. That version decides the answer: a deletion means missing, an expiry at or before `m` means missing, anything else is the value. A later `set` or `setWithTtl` appends a new version with its own expiry, so it replaces the old expiry automatically. Scans apply the same rule to every field, so `scanAt(m)` agrees with `getAt(m)` for each field.

### Complexity

- Time: O(log v) per field operation; O(f log f + f log v) per scan — a field operation is one binary search (Python and TypeScript append in O(1); Java and Kotlin insert into a `TreeMap` in O(log v)); a scan does one search per field and sorts the survivors.
- Space: O(w) — every write and deletion stays in its field's history.

### Trade-offs

- Overwriting values (levels 1 to 3) uses O(live fields) memory, but level 4 needs the past, so some history is unavoidable. Keeping it per field means a point read never touches unrelated fields.
- A global append-only log of all writes is simpler to write but makes `getAt` scan the log: O(w) per read.
- Snapshotting the whole database at every write gives O(1) historical reads at an O(total size) cost per write; it only pays off when reads at old moments dominate.
- Scans sort on every call. A sorted map of fields (`TreeMap`, or a sorted list in Python) would make prefix scans O(log f + matches), at the price of O(log f) writes. With at most a few hundred fields per record the sort is cheaper to write and fast enough; say so in the interview.

### Pitfalls and edge cases

- The expiry is exclusive: a field written at 10 with `ttl` 5 is visible at 14 and missing at 15.
- `remove` of an expired field must return `false` and must not write a deletion; it is already missing.
- After `setWithTtl`, a plain `set` must clear the expiry. Storing the expiry inside the version, not in a separate map keyed by field, gets this right for free.
- Judge the expiry at the requested moment. `getAt(100, ..., 5)` for a field that expired at 6 returns its value, even though it is long gone at 100.
- A moment before the first write must return `""`: the binary search finds no version.
- Sort scans by field name with plain string order: `a10` comes before `a2`.

### Language notes

- Python: `bisect_right(versions, moment, key=...)` (Python 3.10 and later) searches by `since` without a parallel list of times. A frozen dataclass with `slots=True` keeps each version small.
- TypeScript: there is no built-in binary search or sorted map, so the reference writes the search by hand. Sorting with `<` and `>` matches the other languages for ASCII; `localeCompare` would not.
- Java: `TreeMap.floorEntry(moment)` is the binary search. A nested `record Version` with a nullable `Long expiresAt` models "never expires" as `null`; compare with `moment < expiresAt` only after the null check, or unboxing throws.
- Kotlin: the same `TreeMap`, with `floorEntry(moment)?.value?.takeIf { ... }` chaining the null checks. File-private top-level classes keep the helpers out of the public API.
- Go: `sort.Search` is the binary search; it returns the first version that starts after the moment, so the one before it is in force. Map iteration order is random, so a scan collects its entries into a slice and sorts them by field name. `NewInMemoryDatabase` has to `make` the map, since a write to a nil map panics.
- Rust: `partition_point` is the binary search, and `value_at` returns an `Option<&str>` borrowed from the history, so a read copies nothing. The stub passes keys and fields as owned `String`s, which the writes move straight into `entry(key).or_default()`; reads borrow them as `&str`.
