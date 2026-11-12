# SCD Type 2 Dimension: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| versions-by-key | optimal | O(b log b + b v) per load of b rows, v the versions of a key; O(log v) per point lookup; O(k log v) per snapshot of k keys | O(n) for n versions | default answer; one sorted list of versions per business key serves all four levels |

Here `n` is the number of stored versions, `b` the rows of a batch, `v` the versions of one business key and `k` the number of business keys.

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | One row per business key, numbered in key order | a map from business key to its rows, a map from surrogate key to a row, and the next surrogate key |
| 2 | Tracked attributes close a version and append one | the set of tracked attribute positions; the list of a key's rows is sorted by `validFrom`, so the last row is the current one |
| 3 | Lookups by date | nothing new: a binary search over a key's sorted list finds the version valid on a date |
| 4 | Late rows and deletes | the latest load date per business key, which guards the untracked values; new versions are inserted at their place in the sorted list instead of appended |

The early choice that makes level 4 cheap is to keep each key's versions sorted by date and to find "the version valid on a date" with one function. Level 2 only ever changes the last version, so a first version can get away with "close the current row and append". Level 4 then needs the version valid on any date, and a split in the middle; with the lookup already written for level 3, a late change is the same code with a different holder.

## Approach: versions-by-key (Versions sorted by start date per business key)

### Intuition

A type 2 dimension is a set of timelines, one per business key. Each timeline is a sequence of intervals that never overlap, and each interval carries the attribute values that held during it. Every question is either about one timeline at one date (which interval contains it?) or about changing one timeline at one date (cut an interval in two, or correct one). A sorted list per key, searched by start date, answers both. Untracked attributes are not part of the timeline at all: they are one value per key, copied into every interval so that a returned row is complete.

### Algorithm

1. `load` reduces the batch to one row per business key, keeping the last, and visits the keys in sorted order, so new surrogate keys come out in business key order.
2. A new business key gets one version from `loadDate` to the open end.
3. For a known key, if `loadDate` is at least the latest load date of the key, compare the untracked values with the stored ones and copy every difference into all versions; then record `loadDate` as the latest.
4. Find the version valid on `loadDate` by binary search on `validFrom`. If its tracked values match, stop. If it starts on `loadDate`, overwrite its tracked values. Otherwise split it: the new version takes the old end, the old version ends on `loadDate`, and the new version is inserted after it.
5. If no version is valid on `loadDate`, insert one that ends where the next version starts, or at the open end.
6. `loadFull` applies the batch the same way, then closes the last version of every absent key whose `validTo` is still the open end.
7. `lookupAt`, `snapshotAt` and `resolveFacts` use the search of step 4; `resolveFacts` classifies the answer by whether the version found is open.

### Correctness

Invariant: for every business key, its versions are sorted by `validFrom`, their intervals are non-empty and do not overlap, and at most one, the last, has the open end. A new key starts with one interval. A same-date correction changes no interval. A split replaces `[s, e)` with `[s, d)` and `[d, e)`, where `s < d < e` because the version is valid on `d` and does not start on it, so both pieces are non-empty and the union is unchanged. A version added where none is valid fills `[d, next)`, where `d < next` because the next version starts after `d`, and nothing covered `d` before. A full load is dated after every start, so a closed interval `[s, d)` is non-empty. Under this invariant, the last version with `validFrom <= date` is the only candidate that can contain the date, which is what the binary search returns.

Untracked values: every write copies the value into all versions, so the versions of a key always agree on them, and the guard on the latest load date means a value can only be replaced by a row dated on or after the one that wrote it, which is "the latest-dated load wins".

Numbering: every new version is created while visiting the keys in sorted order, and each key gets at most one new version per batch, so the numbers follow the business keys.

### Complexity

- Time: O(b log b + b v) per load of b rows, v the versions of a key; O(log v) per point lookup; O(k log v) per snapshot of k keys — sorting the batch costs `b log b`; per key, copying an untracked value into every version and inserting into the middle of a list are linear in its versions; a lookup is one binary search; a snapshot is one search per key.
- Space: O(n) for n versions — each version is stored once, with one entry in each of the two maps.

### Trade-offs

- A warehouse table holds all versions in one place and finds the valid one with a range condition on the dates; an index on `(businessKey, validFrom)` makes that the same binary search. In memory, a list per key is the direct equivalent.
- Copying untracked values into every version keeps each row complete, at the cost of rewriting old rows on every correction. Keeping untracked values once per key, in a separate map, makes corrections O(1) and the rows assembled on read; the answers are the same.
- Inserting into the middle of a list is linear. A balanced tree per key makes it logarithmic, which matters only for keys with very long histories.
- A version table without merging can hold neighbours with equal values after late corrections. Merging them would change surrogate keys that facts already point at, which is why the statement forbids it.

### Pitfalls and edge cases

- Surrogate keys follow the sorted business keys, not the order of the rows in the batch, and the sort is by character code: `10` before `9`, capitals before lower case.
- A business key repeated in a batch counts once, with its last row. Reading the first row, or applying every row, changes both the values and the counts.
- An overwrite at level 1 keeps the row's `validFrom`. Moving it to the load date makes the row look newer than it is.
- The closed version ends on the load date, not the day before: intervals are half-open, so `validTo` is the first date that is no longer valid.
- A tracked change on the same date as the current version's start corrects that version; a version from a date to the same date would contain no date.
- `trackHistory` affects later loads only, and returns `false` for an attribute that is already tracked or does not exist; attribute names are case-sensitive.
- An untracked change goes into every version, closed ones included. Writing it only into the current version leaves history with two different "latest" values.
- A late row must not overwrite untracked values with older ones: compare its date with the latest load date of the key, and treat an equal date as newer.
- A split keeps the old end for the new version. Giving it the open end creates two current versions.
- A fact dated before the key's first version, or in a gap after a delete, has no version and gets `0`, not the nearest version.
- A full load closes only keys that are still current; a key closed by an earlier full load is not closed or counted again. A key that returns gets a new version, never its old one reopened.
- `history` is ordered by date; after a late change, the surrogate keys are not in date order.

### Language notes

- Python's `bisect_right` with `key=` searches the version list by `validFrom` directly. TypeScript has no binary search in its library, and `Collections.binarySearch` in Java and Kotlin needs a comparator and returns any of several equal positions, so those three references write the loop. Go uses `sort.Search`, and Rust `partition_point`, which both return the first index whose start is after the date.
- Rust keeps every version in one arena vector and stores indexes in the per-key lists and the surrogate key map, because a version is reachable from both and a reference would need shared ownership. The other languages share one object between the two maps.
- Java and Kotlin order the business keys with a `TreeMap`, and Rust with a `BTreeMap`; Python, TypeScript and Go sort the keys when they need them.
- Rows are built as strings at the end, with `String.valueOf` in Java, `toString()` in Kotlin, `strconv.Itoa` in Go and `to_string()` in Rust. Dates fit in a 32-bit `int`, since the open end `99991231` is below 2^31.
- Sorting business keys: Python, Java's `compareTo`, Kotlin's `sorted()`, Go's `sort.Strings` and Rust's `sort()` compare by code point or byte, which agree on ASCII. TypeScript's default `sort()` compares UTF-16 units, which also agree on ASCII; `localeCompare` would not.

## Further reading

- K. Kulkarni and J.-E. Michels, ["Temporal features in SQL:2011"](https://doi.org/10.1145/2380776.2380786), ACM SIGMOD Record 41(3), 2012, pages 34 to 43: the closed-open period model (a period includes its start and excludes its end, and the end must be after the start), valid time and transaction time, and updates for a portion of a period that split a row into contiguous rows.
