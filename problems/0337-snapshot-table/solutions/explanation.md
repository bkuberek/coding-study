# Snapshot Table: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| file-lifetimes | optimal | O(F log F) per scan, manifest or expiry and O(F) per overwrite or compaction, F the files ever added; O(k + D) per commit of k changes, D the files changed since its base | O(F + S) for F files and S snapshots | default answer; one interval per file replaces a copy of the live set in every snapshot |

Here `F` is the number of files ever added, `S` the number of snapshots, `k` the files a commit adds or removes, and `D` the files added or removed by the snapshots between a commit's base and the current snapshot.

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | Snapshots that add files | a map from path to file, with the snapshot that added it; a list of snapshots with the files each added |
| 2 | Removals and time travel | each file also records the snapshot that removed it; each snapshot records the files it removed, its parent and its operation |
| 3 | Commits from an older base | nothing new: the per-snapshot lists of added and removed files are what the conflict check walks |
| 4 | Expiry and compaction | the id of the first retained snapshot |

The early choice that makes every level small is to record, for each file, the snapshot that added it and the one that removed it. A first version that copies the live set into each snapshot answers levels 1 and 2 directly, but its memory grows with snapshots times files, and level 4 then has to compare sets of expired and retained snapshots. With lifetimes, "live in snapshot `s`" is `added <= s < removed`, and "can be deleted after expiry" is a comparison of `removed` with two numbers.

## Approach: file-lifetimes (One lifetime per data file over a line of snapshots)

### Intuition

History here is a single line: every commit's parent is the snapshot before it, even a rebased one. A path is never reused, so each data file enters the table once and leaves at most once. Its whole story is therefore an interval of snapshot ids. Every question about a snapshot is a question about which intervals contain its id; every question about a commit is about the files that the snapshots after its base added or removed; and expiry, which always cuts the oldest snapshots, moves one boundary.

### Algorithm

1. A commit validates its input, takes the next id, sets `removed` on each removed file, creates each added file with `added` set to the new id, and appends a snapshot with its parent, timestamp, operation and the two lists.
2. `scanAt(s)` keeps the files with `added <= s < removed`. `manifest(s)` adds the files with `removed == s` as deleted, and marks a live file added when `added == s`.
3. `snapshotAsOf(t)` takes the last snapshot with a timestamp at or before `t`; if it is older than the first retained snapshot, the answer is `0`.
4. `commit(base, ...)` checks that `base` is retained (or `0` while nothing has expired), that the new paths are fresh and that the removed paths are live at `base`. It then walks the snapshots `base + 1` to the current one and stops at the first that removed one of the same paths, or that is not a `replace` and added a file in a partition of a removed path. Otherwise it commits on top of the current snapshot.
5. `expireSnapshots` advances the first retained id while the snapshot there is older than the cutoff and not among the latest `retainLast`. It returns the files whose `removed` lies after the old first retained id and at or before the new one.
6. `compact` collects the live small files of the partition and, if there are two or more, commits a `replace` snapshot that removes them and adds the combined file.

### Correctness

Lifetimes: a file is created by exactly one snapshot and its `removed` is set at most once, by a later snapshot, because a removed path is no longer live and a path is never added again. Every snapshot's live set is the previous live set minus its removals plus its additions, which is exactly the set of files with `added <= s < removed`.

Commits: the conflict test is evaluated on the snapshots after the base, in order, so the reported id is the first conflicting one. A rebased change touches only files that are still live in the current snapshot: a removed file was live at the base, and if a later snapshot had removed it, that snapshot would conflict. Applying the change to the current snapshot keeps every file the snapshots in between added.

Expiry: the retained snapshots form a suffix that starts at `first`. A file is live in some retained snapshot exactly when its lifetime reaches `first`, that is when `removed > first`: if it was added after `first` it is live where it was added, and if it was added before and removed after, it is live in `first`. So the files with `removed <= first` are read by no retained snapshot. Among them, those with `removed` after the previous `first` were live in a snapshot this call expired (the one just before `removed`), and those with `removed` at or before the previous `first` were returned by an earlier call.

### Complexity

- Time: O(F log F) per scan, manifest or expiry and O(F) per overwrite or compaction, F the files ever added; O(k + D) per commit of k changes, D the files changed since its base — reads and maintenance filter all files and sort the answer; a commit validates its own k paths with hash lookups and reads the added and removed lists of the snapshots after its base.
- Space: O(F + S) for F files and S snapshots — each file is stored once, and each snapshot holds its own changes, so every file appears in at most two snapshot lists.

### Trade-offs

- A full copy of the live set per snapshot makes `scanAt` a lookup, at a cost in memory of snapshots times files. Real table formats sit in between: a snapshot points at a list of manifests, and unchanged manifests are shared with the previous snapshot, so a commit writes only its own changes and a read still finds every live file.
- Filtering all files for a scan is simple and linear. An index from snapshot to live files, or keeping the live set of the current snapshot alongside the lifetimes, makes the common read (now) cheaper.
- The conflict rule trades concurrency for safety: any append to a partition you remove from aborts you, even when the new rows would not have been removed. A finer rule needs to know which rows a removal was based on.
- Expiry by a cutoff and a minimum count matches how retention is usually configured. Expiring only the oldest snapshots keeps the retained ones a suffix, which is what makes the file check two comparisons.

### Pitfalls and edge cases

- Snapshot ids start at 1; an empty table's current snapshot is 0, and 0 is not a snapshot for `manifest` or `scanAt`.
- A path can never be used twice, not even after its file was deleted, and a call that is refused uses no id and changes nothing, even if only one of its paths is bad.
- Paths sort by character code, not ignoring case.
- A manifest marks a file added only in the snapshot that added it, and deleted only in the snapshot that removed it.
- An overwrite removes every live file of its partition, refuses files of other partitions, and is named after what it did: an overwrite of an empty partition is an append, and one with no files is a delete.
- `snapshotAsOf` includes commits made exactly at the time, and at a tie the later commit wins.
- A stale append is rebased, not refused; a rebased commit is applied to the current files, and its parent is the current snapshot. Applying it to the base's files loses the commits in between.
- A file that was live at the base but has been removed since is a conflict; a file that was never live at the base is invalid.
- A concurrent removal of another file in the same partition is not a conflict, and a compaction is not an append.
- Expiry never frees a file that any retained snapshot reads, including an older retained snapshot when the current one no longer has the file. A snapshot exactly at the cutoff stays, and the latest `retainLast` stay however old they are.
- A file is freed once: an implementation that collects "files no retained snapshot reads" from every expired snapshot ever reports the same files again on the next call.
- Compaction needs at least two files with fewer rows than the limit, and the new path uses the id of the snapshot being created.

### Language notes

- A removed time of "never" is a large sentinel: `1 << 62` in Python, `Number.MAX_SAFE_INTEGER` in TypeScript, `Integer.MAX_VALUE` in Java and Kotlin, `math.MaxInt` in Go and `i32::MAX` in Rust; snapshot ids are 32-bit `int` everywhere.
- Timestamps are `long` in Java and Kotlin, `int64` in Go and `i64` in Rust. Row counts are summed in 64 bits, because the total of a compaction can pass 2^31.
- Rust keeps every file in one vector and refers to it by index from the path map and from the snapshots, because a file is reachable from both; the other languages share one object.
- Sorting paths: Python's `sorted`, TypeScript's default `sort`, Java's `Collections.sort`, Kotlin's `sorted`, Go's `sort.Strings` and Rust's `sort` all compare by code point or byte, which agree on ASCII.

## Further reading

- [Apache Iceberg Table Spec](https://iceberg.apache.org/spec/): the sections Overview and Optimistic Concurrency (snapshots of live data files, atomic swaps, retries based on the new current version, and writers choosing what to validate), Manifests (the entry status `EXISTING`, `ADDED` or `DELETED`, deletes being informational and unused by scans), Snapshots (the `append`, `replace`, `overwrite` and `delete` operations), Snapshot Retention Policy and Deleting Files (expiry by age and a minimum number of snapshots, and when a data file may be deleted), and Commit Conflict Resolution and Retry (appends always apply; replaces and deletes must find their files still in the table).
- H. T. Kung and J. T. Robinson, ["On Optimistic Methods for Concurrency Control"](https://doi.org/10.1145/319566.319567), ACM Transactions on Database Systems 6(2), 1981, pages 213 to 226: transactions that work without locks in a read phase, are checked in a validation phase, and are backed up and restarted when validation fails.
