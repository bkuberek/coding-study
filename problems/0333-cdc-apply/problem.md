# CDC Apply

## Statement

Build `ReplicaTable`, a copy of one database table that is kept up to date by reading the source's **change log**. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**What is change data capture?** A database records every change it makes, in order, in a log. *Change data capture* (CDC) reads that log and turns each entry into a *change event*: "row 7 was inserted with these values", "row 7 was updated, here is the new row", "row 3 was deleted". Another system can apply the same events to its own copy of the table, a *replica*, and stay in step with the source without ever copying the whole table again. Search indexes, caches, analytics stores and backups are often fed this way.

**Tables and keys.** A table has named **columns**, and every row has one value per column. The first column is the **primary key**: no two rows have the same key, so the key alone says which row an event is about.

**Why it is harder than it looks.** The events travel through queues and networks before they reach the replica. They can arrive twice, after a restart; arrive in another order; belong to transactions that later fail; or describe a table whose columns have since changed. A replica that applies events naively ends up wrong in ways nobody notices until much later. Each level adds one of these problems.

Aim to finish in 120 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 30, level 2 by 55, level 3 by 85 and level 4 by 115, keeping the last minutes for a final run.

## Input

- `ReplicaTable(columns)`: creates an empty replica of a table with these column names, in order. The first name is the primary key's column. There are 1 to 8 columns, with distinct names.
- A **row** is a list of strings, one value per column, in column order, so `row[0]` is the key. A key is a non-empty string, and any value, the empty string included, is at most 20 printable ASCII characters (codes 32 to 126).
- A change's `op` is `"insert"`, `"update"` or `"delete"`. An insert or an update carries the whole row, as it is after the change. A delete carries just the key: its row is `[key]`.
- Each level's section describes the methods it adds and their parameters.

## Output

A method that applies something returns a **result code**, a string: `"ok"` when it was applied, or one of the codes that the levels define. A change that is not applied changes nothing. Where a method returns rows, they come sorted by key, with keys compared by the numeric codes of their characters, so `"B"` comes before `"a"` and `"10"` before `"9"`.

## Level 1: Applying changes

- `apply(op, row)`: applies one change event to the replica, and returns its result code:
  - `"insert"` adds the row. If a row with that key exists already, the result is `"duplicate-key"` and nothing changes.
  - `"update"` replaces the row that has the key with the given row, every column of it. If there is no such row, the result is `"unknown-key"`.
  - `"delete"` removes the row with the key. If there is no such row, the result is `"unknown-key"`.
- `rows()`: every row of the replica, each in column order, sorted by key.

A deleted key can be inserted again later. An error never touches the table: the replica keeps what it had, and whoever runs it can look at the code and decide what to do.

### Example 1

<!-- case: ex1 -->

Two rows are inserted, row 7 is updated to its new city, and row 3 is deleted. The rows come back sorted by key.

### Example 2

<!-- case: ex2 -->

Inserting key `9` a second time is a `"duplicate-key"`, and the existing row keeps its values. Updating or deleting a key that is not in the table is an `"unknown-key"`. Keys sort as text: `"10"` comes before `"9"`.

## Level 2: Positions and replays

Every change in the source's log has a **log sequence number**, its *LSN*: a position in the log, which grows with every entry. A replica that crashes, or a queue that redelivers, will show it changes it has already applied, and sometimes an old change after a newer one. The LSN is how the replica tells.

- `applyAt(lsn, op, row)`: applies a change that sits at position `lsn` of the log.
- The replica keeps, for every key, its **version**: the LSN of the last change applied to that key. A delete keeps the key's version too, even though the row is gone; this remembered version is called a **tombstone**.
- A change whose `lsn` is not greater than the version of its key is **stale**, or a duplicate when it is equal: the replica has already applied it or something newer. Its result is `"skipped"`, and nothing changes.
- Any other change follows the rules of level 1, where a key with a tombstone counts as absent. When it is applied, the key's version becomes `lsn`. A change with an error code changes nothing, its key's version included.
- `version(key)`: the key's version, or `-1` when no change to this key has been applied.

The versions are per key, and not one position for the whole replica, because changes to *different* keys may reach the replica in any order: a queue that spreads the changes over several partitions by key keeps them in order only within each partition. Thanks to the versions, applying the log once more, or any part of it that ends at its end, after it has been applied leaves the table exactly as it was.

Cases that use `applyAt` do not call `apply`.

### Example 1

<!-- case: ex3 -->

The four changes apply in order: key `1` has version 3, from its update, and key `2` has version 4, from its delete. Then the whole log arrives again. Every change is at or below the version of its key, so each is skipped, and the table is unchanged.

### Example 2

<!-- case: ex4 -->

Key `k` is inserted at 10 and deleted at 12. When the insert at 10 is delivered again, the tombstone, with version 12, makes it stale, so the deleted row does not come back. A key that was never changed has version `-1`. A new insert at 15 is applied.

## Level 3: Transactions and snapshots

**Transactions.** In the source, a *transaction* groups changes that succeed or fail together: a transfer takes money from one account and adds it to another, never only one of the two. The log holds the changes of a transaction as they are made, and then one **commit** entry when the transaction succeeds, or an abort when it does not. In the cases, the changes of several open transactions can be interleaved.

- `stage(tx, op, row)`: adds a change to the transaction named `tx`. A staged change is not visible: `rows`, `version`, other transactions and the changes outside transactions behave as if it did not exist.
- `commit(lsn, tx)`: the commit entry of `tx`, at position `lsn`. The transaction's changes are applied in the order they were staged, all of them or none, and the transaction's list of changes is then empty:
  - A change whose key has a version of `lsn` or more is skipped (the replica has seen the key at or after this commit). The version used is the one from before this commit, so several changes to one key in the same transaction all count.
  - The other changes apply one after another, each seeing the ones before it in the transaction, with the rules of level 1. If any of them has an error code, *none* of the transaction's changes apply, and `commit` returns that first error code.
  - Otherwise every key that a change of the transaction applied to, deleted keys included, gets the version `lsn`: in the source, the transaction's changes all became visible at the moment of its commit. `commit` returns `"ok"` if at least one change applied, and `"skipped"` if every change was skipped, as happens when a commit is delivered again.
- `rollback(tx)`: an abort: the transaction's staged changes are thrown away. After a commit or a rollback, the name `tx` can start a new transaction.
- A transaction that is never committed stays invisible forever.

**Snapshots.** A log is not kept forever, so a new replica cannot rebuild a table from its first change. It starts from a *snapshot* instead: a copy of the whole table as of one position of the log, followed by catching up on the log from there.

- `loadSnapshot(lsn, snapshot)`: replaces the table with the rows of `snapshot`, which is the source table as of position `lsn`: it includes every change and every committed transaction at or below `lsn`, and nothing after. Each of its rows gets the version `lsn`. Cases that use it call it once, right after the constructor.
- From then on, a change of `applyAt` with an `lsn` at or below the snapshot's position is `"skipped"`, whatever its key, because the snapshot already holds it. This covers deletes, which leave no tombstone in a snapshot.
- A `commit` at or below the snapshot's position is `"skipped"` as a whole, and its changes are thrown away. A commit *after* it applies with the rules above, even when the transaction's changes were made before the snapshot's position: the snapshot holds only committed work, so such a transaction is not in it.

Each commit in the cases has at least one staged change.

### Example 1

<!-- case: ex5 -->

`t1` and `t2` stage changes in turn, and before the commit the table still shows only the first row. The commit of `t1` at 4 applies both of its changes, and keys `1` and `2` both take version 4. `t2` is rolled back, and `t3` never commits, so the delete of row `2` never shows.

### Example 2

<!-- case: ex6 -->

The snapshot is the table as of position 5, so the insert at 2 and the transaction committed at 4 are already in it and are skipped. The update at 6 applies. Transaction `b` staged its change before the snapshot's position but commits at 7, after it, so its change is not in the snapshot: it applies, and key `4` takes version 7.

## Level 4: Schema changes and checks

The source's table changes shape over time: columns are added, dropped and renamed. These changes travel in the same log, with LSNs, and the replica must apply them at the right moment, between the row changes that come before and after them.

- `alterAt(lsn, change)`: applies a schema change at position `lsn`, and returns its result code. `change` is one of:
  - `["add", name, default]`: adds a column at the end. Every existing row gets the value `default` in it. If the name is taken: `"duplicate-column"`.
  - `["drop", name]`: removes the column and its value from every row. If there is no such column: `"unknown-column"`. The key's column, the first one, cannot be dropped: `"key-column"`.
  - `["rename", old, new]`: renames a column, keeping its position and values. If there is no column `old`: `"unknown-column"`; if `new` is taken, by another column or by `old` itself: `"duplicate-column"`.
- The schema has a version of its own, the LSN of its last applied change. A schema change whose `lsn` is at or below that version, or at or below the snapshot's position, is `"skipped"`, before any of the checks above. One with an error code changes nothing.
- From now on an insert or an update, in `apply`, `applyAt` or a committed transaction, whose row does not hold exactly one value per column of the current schema, has the result `"column-count"`, checked after the skip rules and before the key checks. A delete still carries just the key.
- `columns()`: the current column names, in order.
- `compare(sourceColumns, sourceRows)`: compares the replica with a copy of the source table, given as its column names and its rows, the first column being its key, and lists the differences:
  - `["missing-column", name]` for a column of the source that the replica lacks, and `["extra-column", name]` for one of the replica that the source lacks. Columns are matched by name, not by position.
  - `["missing-row", key]` for a key that only the source has, and `["extra-row", key]` for one that only the replica has.
  - `["value-differs", key, column, replicaValue, sourceValue]` for a key that both have, and a column that both have, where the two values differ.
  - The column differences come first, sorted by column name. Then the row differences, sorted by key, and for one key by column name. A replica that matches its source gives `[]`. Only the committed table is compared.

No transaction is open when a schema change arrives, and the row changes that arrive after a schema change have a greater LSN than it, unless they are deliveries of changes the replica has already applied.

### Example 1

<!-- case: ex7 -->

The column `city` is added with the default `unknown`, which both rows take. The insert at 4 then carries three values. The rename keeps the values in place, and the drop removes the column and its values.

### Example 2

<!-- case: ex8 -->

The source lists its columns in another order, and has an `email` column that the replica lacks. Row `2` has another city in the source, row `3` exists only in the source, and row `4` only in the replica.

## Constraints

- At most 2 * 10^4 calls per test, and at most 10^4 rows in the table, in a snapshot or in a source.
- `1 <= lsn <= 10^9`.
- Transaction names are non-empty strings of at most 20 printable ASCII characters.

## Follow-ups

- An update that arrives before the insert of its row is rejected here, and the insert that comes later wins. What would a replica need to apply changes in any order and still end with the source's table?
- The tombstones grow with every key ever deleted. When is it safe to forget one?
- A snapshot of a large table takes a long time to copy, and the source keeps changing meanwhile. How could a replica copy the table in chunks while it keeps applying the log, and still end consistent?
- `compare` reads every row of both tables. How could a replica and its source find their differences by exchanging far less data, for example a checksum per range of keys?

## Hints

### Hint 1

Start with a dictionary from key to row. An insert checks that the key is not there, an update and a delete check that it is, and each one then adds, replaces or removes. Sort the keys only when `rows` is asked for. Check before you change anything, so that an error leaves the table as it was.

### Hint 2

The versions are a second dictionary from key to LSN. Do not remove a key from it when its row is deleted: that is the tombstone. Before looking at the op, compare the change's LSN with the key's version; only a change that passes goes on to the checks of level 1.

### Hint 3

Keep a dictionary from transaction name to its list of staged changes, and leave the table alone until the commit. At the commit, take the list out of the dictionary, whatever happens next.

### Hint 4

To apply a transaction all or nothing, run its changes against a small dictionary of their own, an overlay that records, for each key the transaction touches, its new row or a mark that it was deleted. A lookup checks the overlay first and the table second. Write the overlay into the table, and set the versions, only after every change passed.

### Hint 5

The snapshot's position works as a floor under every key at once: a change at or below it is skipped even for a key the snapshot does not hold. For a commit, compare the commit's position, not the positions of its changes, because what decides whether a transaction is in the snapshot is when it became visible.

### Hint 6

A schema change touches the column list and every row: an added column appends the default to each row, and a dropped one removes the value at its index. Keep a separate version for the schema. For `compare`, turn the source into a dictionary by key, find the columns both sides have, and read each value by looking up that column's index on each side.
