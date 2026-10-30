# Versioned Rate Table: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| sorted-versions | optimal | O(V + k) per publish, O(log V) per lookup | O(V + K) | default answer |

`V` is the number of versions, `k` the number of classes in the version being published, and `K` the number of class rates stored in total.

## Approach: sorted-versions (Keep versions sorted by effective date and binary-search each lookup)

### Intuition

The table is an append-only history ordered by effective date, and every question is "what was the last version at or before this day?". That is the same search as in a time-based key-value store, with whole tables as the values.

### Algorithm

1. Keep two parallel lists sorted by effective date: the dates, and the versions (an id plus a map from class code to rate).
2. `publish`: increase the version counter, find the upper bound of `effectiveDate` in the dates (the position after every version with that date), and insert the date and a new version there. The version gets its own copy of the codes and rates.
3. `rateAsOf` and `versionAsOf`: find the upper bound of `onDate`. If it is 0, no version has started, so return `-1`. Otherwise the governing version sits just before the bound: read its id, or look the class up in its map and return `-1` when the class is missing.

### Correctness

The lists stay sorted by date, and versions with equal dates stay in publish order, because each insert lands after its equals. The upper bound of a day is therefore the position just past the last version whose date is on or before the day, and among those with the same date it is the last one published, which is the version the statement says governs. Since a version is a complete map, nothing is inherited from older versions.

### Complexity

- Time: O(V + k) per publish, O(log V) per lookup — insertion shifts up to V entries and copies the k codes of the new version; a lookup is one binary search plus one hash lookup.
- Space: O(V + K) — V versions that hold K class rates in total.

### Trade-offs

A balanced tree (Java and Kotlin `TreeMap.floorEntry`, with a list of versions per date to keep the same-date rule) makes `publish` O(log V) as well. A plain scan from the newest version is simpler and fine for a handful of versions. In practice publishing is rare and lookups are frequent, so shifting a list on insert is the right trade for an interview-sized answer. Counted over n publishes in the worst case (each one lands at the front), the total is O(n^2), which is the class this problem declares.

### Pitfalls and edge cases

- A lower-bound search makes a version miss its own effective date (`h2`): the date must count as "on or before".
- Several versions on one date: the last published governs (`h3`, `h9`). A library search that returns any matching index can pick the wrong one.
- Inheriting classes from older versions is wrong (`h5`), and an empty version governs and finds nothing (`h6`).
- A leap-day effective date and a far-future lookup (`h7`).
- Mutating a version after it was published: copy the arrays into a fresh map on `publish`.
- Class codes match exactly, with no trimming or prefix matching (`h10`).

### Language notes

- Python: `bisect_right(dates, day)` is the upper bound and `list.insert` does the shifting. `date` objects compare chronologically.
- TypeScript: a date is an `IsoDate`, a plain `YYYY-MM-DD` string, so `<=` on strings is chronological order. The upper bound is written out and `splice` inserts. Rates are kept in a `Map<string, Decimal>`.
- Java: `Collections.binarySearch` may return any matching index when dates repeat, so the upper bound is written by hand with `compareTo`. A `record` holds the id and the rate map; `LocalDate` is comparable.
- Kotlin: `List.binarySearch` has the same duplicate-key problem (cases `h3` and `h9` catch it), so the upper bound is written by hand. Parameters are named `onDate` because `when` is a keyword.
- Go: a date is a `time.Time` at midnight UTC, so `After` is the strict comparison. `sort.Search` returns the first index where its predicate holds, so `dates[i].After(day)` makes it the upper bound, and equal dates land before it. `slices.Insert` does the shifting (Go 1.21 and newer). Never compare dates with `==`, which also compares the location and the monotonic clock reading.
- Rust: `NaiveDate` is `Ord`, and `partition_point(|date| *date <= day)` is the upper bound on the sorted `Vec`. `Vec::insert` shifts the tail. A missing rate is `Decimal::NEGATIVE_ONE`, and `copied()` turns the `Option<&Decimal>` from the map into an `Option<Decimal>` (`Decimal` is `Copy`).
