# CDC Apply: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| versioned-rows | optimal | O(c) per change; O(k c) per commit of k changes; O(n c) per schema change; O(n log n + n c) per rows or compare | O(n c) for the rows, plus a version per key ever changed and the staged changes | default answer; one version per key makes every replay safe, and an overlay per commit makes transactions atomic |

Here `n` is the number of rows, `c` the number of columns and `k` the number of changes in one transaction.

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | Applying changes | `columns` and a map from key to row; one check function (`duplicate-key`, `unknown-key`) used before every change |
| 2 | Positions and replays | a map from key to version that keeps deleted keys (the tombstones), consulted before the check |
| 3 | Transactions and snapshots | a map from transaction name to its staged changes, a floor (the snapshot's position), and an overlay built during each commit |
| 4 | Schema changes and checks | a schema version; the check also counts the values of a row; `compare` reads columns by name |

The early choice that pays off is to separate *deciding* from *doing*: one function says whether a change may apply, given whether its key is present, and only then does anything change. Level 1 needs it so that an error touches nothing, level 3 reuses it for a key that is present or absent in a transaction's overlay rather than the table, and level 4 adds the column count in one place that all three ways of applying a change share.

## Approach: versioned-rows (Rows and versions in hash maps, with a buffer per transaction)

### Intuition

A replica is correct when its table equals what the source had at some position of the log. Errors aside, three things can push it away from that: applying a change twice, applying an old change after a newer one, and showing part of a transaction. One number per key, the position of the last change applied to it, answers the first two: a change is new to that key exactly when its position is greater. Keeping that number after a delete is what stops an old insert from resurrecting the row. A transaction is a promise of all or nothing, which a buffer until the commit, and an overlay during the commit, keep.

### Algorithm

1. Keep `columns`, `rows` (key to row), `versions` (key to LSN), `floor` (0, or the snapshot's position), the schema version, and `staged` (transaction name to its list of changes).
2. `check(present, op, row)`: for an insert or update whose row length differs from the number of columns, `column-count`; for an insert, `duplicate-key` if present; for an update or delete, `unknown-key` if absent; otherwise `ok`.
3. `apply(op, row)`: check with `present = key in rows`; if `ok`, insert, replace or remove.
4. `applyAt(lsn, op, row)`: if `lsn <= floor` or `lsn <= versions[key]` (`-1` when absent), return `skipped`. Otherwise `apply`, and on `ok` set `versions[key] = lsn`. `version` reads the map.
5. `loadSnapshot(lsn, snapshot)`: `rows` becomes the snapshot, every key gets version `lsn`, and `floor = lsn`.
6. `stage` appends to `staged[tx]`; `rollback` removes `staged[tx]`.
7. `commit(lsn, tx)`: remove the list from `staged`. If `lsn <= floor`, return `skipped`. Otherwise walk the changes with an empty overlay (key to new row, or to a deleted mark): skip a change when `lsn <= versions[key]`; else check it with `present` read from the overlay if the key is there, from `rows` if not, return the code if it is not `ok`, and record the result in the overlay. If the overlay is empty, return `skipped`; otherwise write it into `rows` (deleting the marked keys), set every overlay key's version to `lsn`, and return `ok`.
8. `alterAt(lsn, change)`: if `lsn <= floor` or `lsn <=` the schema version, return `skipped`. Otherwise validate (`duplicate-column`, `unknown-column`, `key-column`); on success, change `columns` and every row (append the default, delete the value at the dropped index, or rename in place), and set the schema version.
9. `rows` sorts the keys; `columns` copies the list.
10. `compare`: the column differences are the symmetric difference of the two name sets, sorted, each marked `missing-column` (source only) or `extra-column` (replica only). Turn the source rows into a map by key, then walk the sorted union of the keys: a key on one side only is `missing-row` or `extra-row`; a key on both sides is compared on every common column, in sorted order, reading each side's value at that side's index of the column.

### Correctness

Versions only grow: a change applies only when its position is greater than its key's version, and then it becomes the version. So, for any one key, the replica applies a subsequence of that key's changes in increasing order of position, and once it has applied the change at position `p`, it never applies one at `p` or below again. Replaying the log, or any suffix of it, after it has been applied therefore finds every change that applied the first time at or below its key's version, and skips it; a change that failed the first time meets the same row it met then, because nothing has changed that key since, and fails again with the same code. The table ends the same. A delete keeps its key's version, so an insert from before the delete stays below it.

A commit computes every change against the overlay first and the table second, which is the table as the transaction's earlier changes left it, and writes nothing until all of them passed, so an error leaves the table exactly as before: nothing or everything. The version test uses the versions from before the commit, which the loop never changes, so a second change to the same key in one transaction is not mistaken for a replay. Setting every touched key to the commit's position records that the transaction became visible there, which is what lets a delivered-again commit be recognized: each of its keys is now at or above the commit's position.

The snapshot holds every change at or below its position, including deletes that left no row. The floor skips exactly those changes, for keys present or absent. A transaction is in the snapshot exactly when its commit is at or below the position, so the commit's position, and not the positions of its changes, is what is compared with the floor.

### Complexity

- Time: O(c) per change; O(k c) per commit of k changes; O(n c) per schema change; O(n log n + n c) per rows or compare — a change is a few hash lookups and copies one row of `c` values. A commit does that for each of its `k` changes, plus one write per key. Adding or dropping a column touches every row. `rows` and `compare` sort `n` keys and read `c` values per row (looking a column up by name is O(c); a map from name to index makes it O(1) without changing the bound).
- Space: O(n c) for the rows, plus a version per key ever changed and the staged changes — the tombstones are why the versions can outnumber the rows.

### Trade-offs

- One position for the whole replica, the largest LSN applied, is smaller and is what a replica that receives the log strictly in order needs. It fails as soon as two keys' changes arrive out of order: the second one looks stale and is lost (`h8`).
- Copying the whole table at each commit and swapping it in is simpler than an overlay, and costs O(n) per commit instead of O(k).
- An undo log, applying changes to the table and reverting them on an error, does the same work as the overlay; the overlay has the advantage that the table never holds half a transaction, even for a moment.
- Tombstones are never removed here. A real replica forgets one once no change at or below its version can still arrive, for example after a new snapshot.

### Pitfalls and edge cases

- An insert that overwrites an existing row, or an update or delete of a missing key that "succeeds" (`ex2`, `h1`, `h5`).
- Sorting keys as numbers, or ignoring case (`h2`).
- Comparing with `<` instead of `<=`: a change at exactly the key's version is a duplicate (`h7`).
- One replica-wide position instead of per-key versions (`h8`).
- Forgetting a key's version when its row is deleted, which lets an old insert bring it back (`ex4`, `h11`).
- Moving the version when the change was rejected (`h9`).
- Showing staged changes before the commit (`ex5`, `h15`); applying a transaction's changes up to the first error (`h12`); checking each change against the table instead of the transaction's own earlier changes (`h13`).
- Answering `ok` to a replayed commit, or leaving the transaction's keys at their old versions (`h14`).
- Skipping a whole transaction because one of its keys is newer: only that change is skipped (`h19`).
- Comparing the snapshot's position with `<` (`h17`), applying the floor to row changes but not to schema changes (`h27`), or giving the snapshot's rows a version of 0 (`h16`).
- Validating a schema change before the skip test, so that a delivered-again `add` reports `duplicate-column` (`h21`); letting the key's column be dropped (`h20`).
- Forgetting to fill the new column of the existing rows, or checking the row width of inserts but not of updates (`ex7`, `h22`).
- Comparing columns by position instead of name, or swapping `missing` and `extra` (`ex8`, `h24`, `h26`); comparing the staged changes too (`h25`).

### Language notes

- Python and TypeScript keep the overlay as a map whose value is the new row or `None`/`null` for a deleted key. Java and Kotlin use a `HashMap` with `null` values the same way, checking `containsKey` before `get`, since a missing key and a deleted mark both read as `null`. Go uses a map to a small struct with a `deleted` flag, and Rust a `HashMap<String, Option<Vec<String>>>`.
- Rows are copied on the way in (`list(row)`, `[...row]`, `new ArrayList<>(row)`, `row.toMutableList()`, `append([]string{}, row...)`, `row.clone()`), so a caller that reuses its list cannot change the table.
- Every language sorts keys by the codes of their characters with its default string order: Python's code points, Java's and Kotlin's UTF-16 code units, TypeScript's default comparison, and Go's and Rust's bytes all agree on printable ASCII.

## Further reading

- C. Mohan, D. Haderle, B. Lindsay, H. Pirahesh and P. Schwarz, "ARIES: A Transaction Recovery Method Supporting Fine-Granularity Locking and Partial Rollbacks Using Write-Ahead Logging", ACM Transactions on Database Systems 17(1), 1992, pages 94 to 162, [doi:10.1145/128765.128770](https://doi.org/10.1145/128765.128770): every log record gets a unique log sequence number, assigned in ascending order, and each page records the LSN of the last logged update applied to it; during recovery an update is redone only if the page's LSN is less than the log record's LSN. A replica's per-key version is the same idea applied to rows.
- C. A. Curino, H. J. Moon and C. Zaniolo, "Graceful Database Schema Evolution: the PRISM Workbench", Proceedings of the VLDB Endowment 1(1), 2008, pages 761 to 772, [doi:10.14778/1453856.1453939](https://doi.org/10.14778/1453856.1453939): schema changes written as a sequence of small schema modification operators, among them adding a column with a constant value, dropping a column and renaming a column.
