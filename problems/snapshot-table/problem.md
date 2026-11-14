# Snapshot Table

## Statement

Build `SnapshotTable`, the bookkeeping behind a large analytic table stored as many files. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**Data files are never edited.** A big table is stored as many *data files*, each holding a slice of its rows, often one group of files per *partition* (a month, a country). Files in such storage are written once and then only read or deleted, so the table never changes a file in place. Adding rows means writing new files; removing rows means dropping files from the table; changing rows means both.

**Snapshots.** Which files make up the table right now? The table keeps a list of *snapshots*. Each commit (an append, a delete, a rewrite) creates a new snapshot that lists every file that is part of the table after the commit: its *live* files. A reader picks one snapshot and reads exactly its files, so it never sees half of a commit, and an old snapshot still describes the table as it was. The list that a snapshot keeps is its *manifest*. This is a simplification: in real table formats a snapshot points to a manifest list, which points to many manifests, and a manifest that did not change is shared by the snapshots that use it.

Aim to finish in 120 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 30, level 2 by 60, level 3 by 90 and level 4 by 115, keeping the last minutes for a final run.

## Input

- `SnapshotTable()`: creates an empty table.
- A **file** is described as `[path, partition, rows]`: its path, the partition it belongs to, and its number of rows as a decimal integer.
- A **timestamp** is an integer of your choice, such as milliseconds. The table never reads a clock. Timestamps never go down from one call to the next; equal timestamps are allowed.
- Each level's section describes the methods it adds and their parameters.

## Output

Snapshot ids are integers. A method that creates a snapshot returns its id, or `-1` when it refuses the call; a refused call changes nothing. Lists of paths are sorted by the numeric value of their characters, so that `B` comes before `a`, and `10` before `9`. Numbers inside lists of strings are written in decimal.

## Level 1: Append-only snapshots

- `append(files, timestamp)`: adds the files to the table in one commit, which creates a new snapshot. Snapshot ids count up from `1` in commit order, and the new snapshot's live files are the live files of the previous one plus `files`. It returns the new id, or `-1` when `files` is empty, when a path appears twice in `files`, or when a path was **ever** used before in this table. A path names one file forever: since files are never edited, reusing a name would make two different files look like one.
- `currentSnapshot()`: the id of the latest snapshot, `0` for an empty table.
- `scan()`: the paths of the live files of the current snapshot, sorted.
- `manifest(snapshotId)`: the manifest of a snapshot, sorted by path. It has one entry `[path, partition, rows, status]` for each live file of the snapshot, with `status` = `"added"` when this snapshot added the file and `"existing"` when it was there before. It returns `[]` for an id that is not a snapshot of the table (`0` included).

### Example 1

<!-- case: ex1 -->

The first append adds two files and creates snapshot 1; `scan` sorts the paths. Snapshot 2 adds `d/c.data`, so its manifest marks that file as added and the two older ones as existing. There is no snapshot 3.

### Example 2

<!-- case: ex2 -->

An empty append and an append that names `x` twice are refused. Once `x` is in the table, its path cannot be used again. Refused calls create no snapshot, and `0` is not a snapshot.

## Level 2: Deletes and time travel

- `deleteFiles(paths, timestamp)`: a commit that removes the files at `paths` from the table. It returns the new snapshot's id, or `-1` when `paths` is empty, names a path twice, or names a path that is not live in the current snapshot.
- `overwrite(partition, files, timestamp)`: a commit that replaces a whole partition: it removes every live file of `partition` and adds `files`. It returns the new id, or `-1` when a file of `files` is not in `partition`, when a path appears twice or was used before, or when nothing would change (the partition has no live file and `files` is empty).
- `scanAt(snapshotId)`: the live paths of that snapshot, sorted; `[]` for an id that is not a snapshot. Reading an old snapshot is called **time travel**.
- `snapshotAsOf(timestamp)`: the snapshot that was current at `timestamp`: the latest snapshot whose commit timestamp is at or before it. Commits with equal timestamps happened in call order, so the later one wins. It returns `0` when no commit is that old.
- `history()`: one entry per snapshot, in commit order: `[id, parentId, timestamp, operation, added, removed]`. The parent is the snapshot the commit was applied to (`0` for the first), `added` and `removed` count its files, and `operation` names the change: `"append"` when it only added files, `"delete"` when it only removed some, and `"overwrite"` when it did both.

A manifest now also lists the files that its own snapshot removed, with `status` = `"deleted"`. Such an entry records the change; the file is not live and a scan does not read it. Only the snapshot that removed a file lists it as deleted.

### Example 1

<!-- case: ex3 -->

Deleting `a` creates snapshot 2; snapshot 1 still lists `a`, `b` and `c`. Overwriting partition `p2` removes `c` and adds `d` in one commit, so the manifest of snapshot 3 shows `c` as deleted and `d` as added. The history shows the three operations and their parents.

### Example 2

<!-- case: ex4 -->

Snapshots 2 and 3 were both committed at time 200; the table as of 200 is snapshot 3, the later one. At 199 it was snapshot 1, and before 100 there was no snapshot. Snapshot 4 deleted `a` and `b`, so only `c` is left.

## Level 3: Optimistic commits

Several writers work on the table at once. Each one reads a snapshot, prepares its change (writing new data files can take minutes), and then commits. Meanwhile another writer may have committed. Locking the table for those minutes would make everyone wait. Instead, a writer commits **optimistically**: it says which snapshot it started from, and the table checks whether what happened since then conflicts with the change. If not, the change is applied on top of the current snapshot (it is *rebased*); if it does, the commit is refused and the writer starts again.

- `commit(base, adds, removes, timestamp)`: a writer that read snapshot `base` (or the empty table, `0`) wants to add the files `adds` and remove the live files at the paths `removes`. It returns two strings:
  - `["invalid", ""]` when the commit could never apply: `base` is not a snapshot of the table (`0` aside), both lists are empty, a path of `adds` appears twice or was used before, or a path of `removes` appears twice or is not live in snapshot `base`.
  - `["committed", id]` when `base` is the current snapshot: nothing happened in between, and the commit creates snapshot `id`.
  - `["conflict", id]` when a snapshot committed after `base` conflicts with the change; `id` is the first such snapshot. Nothing changes.
  - `["rebased", id]` otherwise: the change is applied to the live files of the **current** snapshot, not of `base`, so the commits made in between are kept, and the new snapshot's parent is the current snapshot.
- A snapshot `S` committed after `base` **conflicts** with the change when:
  - `S` removed a file that this commit removes (the file is already gone), or
  - `S` added a file to a partition from which this commit removes a file. The writer decided what to remove without seeing that file: an overwrite of the partition would keep data it meant to replace.
- A commit that only adds files never conflicts: appends can be applied in any order.
- The operation of the new snapshot follows the level 2 rule: `append`, `delete` or `overwrite`.

`append`, `deleteFiles` and `overwrite` are commits whose base is the current snapshot.

### Example 1

<!-- case: ex5 -->

Four writers start from snapshot 1. The first appends to `p1` and commits as snapshot 2. The second appends to `p3`: an append never conflicts, so it is rebased. The third removes `b` from `p2`; nothing touched `p2` since snapshot 1, so it is rebased as well. The fourth replaces `a` in `p1`, but snapshot 2 added `c` to `p1`: conflict.

### Example 2

<!-- case: ex6 -->

Two writers both remove `a` from snapshot 1: the first wins, and the second conflicts with snapshot 2, which already removed it. A base that does not exist, a file that is not in the base, and an empty commit are invalid.

## Level 4: Expiry and compaction

Old snapshots cost storage: a file removed from the table stays on disk as long as some snapshot can still read it. Maintenance removes old snapshots and then deletes the files nobody can read any more.

- `expireSnapshots(olderThan, retainLast)`: expires every snapshot whose timestamp is **before** `olderThan` and that is not one of the `retainLast` latest snapshots (`retainLast >= 1`, so the current snapshot always stays). Since timestamps never go down, the expired snapshots are always the oldest ones. It returns the paths, sorted, of the data files that a newly expired snapshot had live and that **no** retained snapshot has live: those files can now be deleted from storage. A file still live in any retained snapshot is never returned, and a file is returned at most once over all calls.
- An expired snapshot is gone: `manifest` and `scanAt` return `[]` for it, `history` leaves it out, `snapshotAsOf` returns `0` when the snapshot current at that time has expired, and a `commit` based on it is invalid. Once any snapshot has expired, base `0` is invalid too, since the commits after it are no longer known.
- `compact(partition, maxFileRows, timestamp)`: rewrites the small files of a partition into one. The small files are the live files of `partition` with fewer than `maxFileRows` rows. With fewer than two of them it returns `-1`. Otherwise it commits a snapshot that removes them and adds one file of the same partition, with their total rows, at the path `partition + "/compacted-" + id`, where `id` is the new snapshot's id. Its operation is `"replace"`: the data did not change, only how it is stored. Paths given to the table never contain `compacted-`.
- A `replace` snapshot adds no new rows, so it never counts as an append in the conflict rule; removing a file that a compaction already removed still conflicts.

Several of these rules follow the Apache Iceberg table specification: its snapshots list live data files through manifests, whose entries are marked existing, added or deleted in its format versions 1 to 3; its operations are append, replace, overwrite and delete; an append can always be retried on a newer snapshot, while a rewrite or a delete must check that the files it removes are still in the table; and snapshot expiry keeps snapshots newer than a maximum age or among a minimum number of latest ones. The rule about appends to a partition that a commit removes from is this problem's own, stricter check: the specification lets each writer choose what to validate, and so which isolation it gets.

### Example 1

<!-- case: ex7 -->

Expiring before time 250 while keeping the latest snapshot drops snapshots 1 and 2. File `a` was live in snapshot 1 and no retained snapshot has it, so it can be deleted; `b` is still live in snapshot 3. Snapshot 2 no longer exists for time travel or as a base. Expiring everything older than 1000 then leaves only snapshot 4, which frees `b` and `c`.

### Example 2

<!-- case: ex8 -->

`p/1` and `p/2` have fewer than 100 rows; `p/3` has 500 and `q/1` is in another partition. Compaction replaces the two small files with `p/compacted-2`, holding their 30 rows. A second compaction finds only one small file and does nothing.

## Constraints

- Paths and partitions are 1 to 40 printable ASCII characters (codes 33 to 126); row counts are integers from 1 to 10^9.
- Timestamps are integers from 0 to 10^15 and never go down; `1 <= retainLast <= 1000` and `1 <= maxFileRows <= 10^9`.
- At most 200 calls per test and at most 100 files per call.

## Follow-ups

- Copying every live file into every snapshot's manifest costs as much as the table on each commit. Real formats share manifests between snapshots and only write new ones for changed files. How would you store snapshots so that a commit costs only its own changes?
- The conflict rule here is strict: a concurrent append anywhere in a partition you remove from conflicts. Which commits could you safely rebase if each writer also said which rows its removal was based on?
- Expiry deletes files that no snapshot reads. Files written by a writer that crashed before committing are referenced by no snapshot at all. How would you find and remove them safely?
- Compaction itself is a commit and can conflict with a delete. Which of the two should win, and how would you retry the loser?

## Hints

### Hint 1

Keep a list of snapshots, each with its id, parent, timestamp, operation, and the files it added and removed. For level 1 you can also give each snapshot the full set of its live paths, copied from the previous snapshot and changed by the commit. Keep a separate set of every path ever used, which is what decides whether a new path is allowed.

### Hint 2

Store each file once, in a map from path to `[partition, rows]`. A snapshot's manifest then needs only the paths: its live paths, the paths it added and the paths it removed.

### Hint 3

Snapshots form one line, and a path is never reused, so a file is live in one unbroken run of snapshots: from the one that added it up to, but not including, the one that removed it. Two numbers per file replace all the copied sets: the file is live in snapshot `s` exactly when `added <= s < removed`.

### Hint 4

For a commit, first validate everything against the base, then walk the snapshots after the base in order and test each one against the two conflict rules. Only if none conflicts, apply the change to the current snapshot.

### Hint 5

Because expiry always removes the oldest snapshots, the retained ones are a suffix of the list: one number, the first retained id, describes them. A file is live in no retained snapshot when its `removed` is at or before that first id, and it was live in a snapshot expired by this call when its `removed` is after the first id from before the call.
