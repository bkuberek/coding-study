# Effective-Dated History: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| write-log-and-view | optimal | O(w) per setValue or getValueAsKnown, O(log w) per getValue, O(f log f + W) per snapshot | O(W) | default answer |

`w` is the number of writes to one field, `f` the number of fields of the record, and `W` the number of writes in total.

## Approach: write-log-and-view (Per-field write log plus a sorted current view)

### Intuition

There are two time axes. Effective dates say when a value is true; timestamps say when the insurer learned it. Level 1 needs only the latest knowledge, which is a sorted map from effective date to value per field. Level 2 replays the writes known at a time.

### Algorithm

1. For every record and field keep two things: a log of every write in timestamp order, and a current view, sorted by effective date, with one value per date.
2. `setValue`: append the write to the log, and upsert it into the view (insert the date, or replace the value of an existing date).
3. `getValue`: find the last view entry whose date is on or before `onDate` (a floor lookup); `""` if there is none.
4. `getValueAsKnown`: take the prefix of the log with `timestamp <= knownAt`, and scan it for the write with the latest effective date on or before `onDate`, letting a later write win a tie on the date.
5. Snapshots read every field of the record in name order and drop the empty values.

### Correctness

The view holds, per effective date, the value of the latest write for that date, which is exactly what the latest knowledge says; the floor lookup then finds the governing date. Timestamps increase, so the writes known at `knownAt` are a prefix of the log. Among known writes with the same effective date, the later one in the log is the correction, and the scan prefers it. A cleared value is stored like any other value, so it governs from its date and only the snapshot hides it.

### Complexity

- Time: O(w) per setValue or getValueAsKnown, O(log w) per getValue, O(f log f + W) per snapshot — an insert shifts up to w view entries and an as-known read scans up to w writes; a snapshot sorts the field names and reads each field.
- Space: O(W) — every write is kept once in a log and at most once in a view.

### Trade-offs

Storing only the current view loses Level 2. Replaying all writes for every `getValue` is simple but O(W) per read. Keeping each field's writes sorted by effective date and timestamp allows a binary search for as-known reads, at the cost of more expensive inserts.

### Pitfalls and edge cases

- Appending a same-date write instead of replacing it (`h1`, `h5`).
- A clear must govern, so an older value does not show through, but it stays out of snapshots (`ex2`, `h4`, `h5`).
- Unknown records and fields read as empty, and records do not leak into each other (`h2`).
- Field order is text order: `payroll` comes before `payrollBasis` (`h3`).
- `knownAt` is inclusive (`h6`).
- A back-dated write stays invisible to earlier knowledge (`h7`).
- A clear that was learned later (`h8`).
- Corrections of corrections (`h9`, `ex3`).

### Language notes

- Python: two sorted lists with `bisect_left` and `bisect_right` hold the view; the prefix of known writes comes from `bisect_right(write_times, known_at)`. `date` objects compare chronologically.
- TypeScript: a date is an `IsoDate`, a plain ISO string, so `<=` compares chronologically. There is no sorted map, so the bounds are written by hand over the dates and over the timestamps. Snapshot field names sort with the default `sort()`. Timestamps are `number`s, which hold up to 10^9 exactly.
- Java: `TreeMap<LocalDate, String>` is the view: `put` replaces a same-date entry and `floorEntry(onDate)` reads. A `TreeMap<String, FieldHistory>` per record gives the field names in sorted order. `Collections.binarySearch` would be safe on the timestamps, because they are distinct (unlike duplicate dates in `versioned-rate-table`), but the bound is short enough to write out.
- Kotlin: the same `java.util.TreeMap`; `floorEntry(onDate)?.value ?: ""`; `buildList` collects snapshots. `timestamp` is a `Long`.
