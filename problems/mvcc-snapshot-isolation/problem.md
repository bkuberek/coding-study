# MVCC Snapshot Isolation

## Statement

Build `MvccStore`, a key-value store that many transactions use at the same time, and that gives each of them a consistent view of the data without making readers and writers wait for each other. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**What is a transaction?** A transaction is a group of reads and writes that the store treats as one unit: either all of its writes take effect, when it *commits*, or none of them does, when it *aborts*. Moving 10 from account `a` to account `b` reads both balances and writes both. If the program crashes or gives up halfway, neither write may survive, or 10 would vanish.

**What is isolation?** A store runs many transactions at once, and their reads and writes interleave. *Isolation* says how much one transaction may see of the others while they run. The strongest promise, *serializability*, is that the outcome is always one that the same transactions could have produced running one at a time, in some order. Weaker promises let more work run in parallel, but they allow *anomalies*: outcomes that no one-at-a-time order produces. Suppose a report adds up `a` and `b` while the transfer above runs. If it reads `a` before the transfer and `b` after it, it counts the 10 twice, a total that never existed.

**Versions and snapshots.** A store with *multiversion concurrency control* (MVCC) never overwrites a value in place. A write adds a new *version* of the key, stamped with the time its transaction committed, and the older versions stay. A transaction reads from a *snapshot*: the data as it was when the transaction began, made of every version committed before that moment and nothing committed after it. However long the report above runs, and whatever commits meanwhile, it reads `a` and `b` from the same moment, so its total is right, and nobody had to wait: the writers added versions while the report read older ones. This is *snapshot isolation*.

**The clock.** All times in this problem come from one logical clock, a counter that starts at 0. Some methods *tick* the clock: they add 1 to it and use the new value. So every tick is a different number, and a smaller number happened earlier.

Aim to finish in 150 minutes. A good split: read the statement in the first 15 minutes, then finish level 1 by about minute 30, level 2 by 60, level 3 by 115 and level 4 by 140, keeping the last minutes for a final run.

## Input

- `MvccStore()`: creates an empty store, with the clock at 0.
- A **key** and a **value** are strings of 1 to 12 characters, each a letter, a digit, `_` or `-`.
- A **transaction id** `tx` is the number that began the transaction. Any integer may be passed; one that never began a transaction is *unknown*.
- Each level's section describes the methods it adds and their parameters.

## Output

A read returns a value, or `""` when there is nothing to read. Each level's section gives the answers of its methods. Lists are in the order the method states.

## Level 1: Versions and snapshots

- `put(key, value)`: writes `value` in a transaction of its own, which commits at once: it ticks the clock, adds a version of `key` with that value, stamped with the new time, and returns the time.
- `begin()`: starts a transaction. It ticks the clock and returns the new time, which is both the transaction's id and its *start time*. The transaction is *active*. At this level transactions only read, and they stay active.
- `read(tx, key)`: the value of the newest version of `key` stamped before the start time of `tx`. It is `""` when `key` has no such version, and when `tx` is not an active transaction.
- `versions(key)`: every version of `key`, newest first, each written as `"<stamp>:<value>"`, such as `"3:green"`. It is `[]` for a key that was never written.

The stamps and the start times share the clock, so a version is either older or newer than a snapshot, never at the same time.

### Example 1

<!-- case: ex1 -->

The first put commits at time 1. The transaction that begins at time 2 sees that version, and still sees it after the second put commits at time 3: its snapshot was taken before. A transaction that begins at time 4 sees the newer version. Both versions are kept, newest first. Nothing was ever written under `pear`.

### Example 2

<!-- case: ex2 -->

Three snapshots at times 1, 4 and 6. The one at time 1 began before anything was written and sees nothing. The one at 4 sees `door` as `open` and `light` as `on`. The one at 6 sees the newest `door`.

## Level 2: Writers and first committer wins

Transactions now write, commit and abort.

- `write(tx, key, value)`: the transaction writes `value` under `key`. The write is *buffered*: no other transaction sees it until `tx` commits. Writing the same key twice keeps the last value. It is `true`, or `false` when `tx` is not active.
- `read(tx, key)`: a transaction that has written `key` reads its own latest value; otherwise it reads its snapshot as at level 1.
- `commit(tx)`: tries to commit, and answers with a status:
  - `"not-active"` when `tx` is not an active transaction;
  - `"write-conflict"` when *first committer wins* refuses it (below): the transaction aborts;
  - `"committed"` otherwise: the clock ticks, and every key the transaction wrote gets one new version with its last value, stamped with the new time, the *commit time*. A transaction that wrote nothing commits too, and ticks the clock as well.
- `abort(tx)`: ends an active transaction and drops its writes. It is `true`, or `false` when `tx` is not active.
- `status(tx)`: `"active"`, `"committed"`, `"aborted"` (by `abort` or by a refused commit), or `"unknown"`.

A commit that fails and an abort do not tick the clock and add no version.

**First committer wins.** Two transactions both read a counter at 5 and both write 6, each meaning to add one. If both commit, one increment is lost: a *lost update*. Snapshot isolation refuses the second commit instead. A transaction commits only if, for every key it wrote, no version of that key is stamped after its start time. Such a version was committed by another transaction, or by a `put`, while this one was running, so this one would overwrite a change it never saw. The first of the two to commit wins, whichever wrote first, and the other one aborts; a program would retry it from the start.

### Example 1

<!-- case: ex3 -->

Transactions 2 and 3 both write `stock`. Transaction 2 reads its own write; transaction 3 still reads `10`, before and after 2 commits, from its snapshot. Transaction 2 commits first, at time 4. Transaction 3 then tries to commit its write, but `stock` has a version stamped 4, after 3 started: a write conflict, and 3 aborts.

### Example 2

<!-- case: ex4 -->

An aborted transaction leaves no version behind, and committing it afterwards is `"not-active"`. Transaction 3 writes nothing and commits at time 4. Once committed, it can no longer write. An id that never began a transaction is `"unknown"`.

## Level 3: Write skew and dangerous structures

**Write skew.** Snapshot isolation is not serializable. Two replicas of a service, `east` and `west`, must never be down at the same time. Two maintenance jobs start together. Each reads both replicas, sees both up, and takes its own replica down, which is safe *on its own snapshot*. They write different keys, so first committer wins finds no conflict, both commit, and both replicas are down. No order of the two jobs, one after the other, gives that: the second job would have seen the first replica down and stopped. The anomaly is called *write skew*. A program can avoid it by hand, for instance by also writing the key it only read, but a serializable store catches it by itself.

- `begin()` keeps giving snapshot isolation, as at level 2.
- `beginSerializable()`: starts a transaction like `begin`, which is also checked by the rules below.
- `antidependencies(tx)`: the live edges of `tx` (below), as `"in:<id>"` for an edge from transaction `<id>` to `tx`, and `"out:<id>"` for an edge from `tx` to `<id>`. All `in` entries come first, then all `out` entries, each group sorted by id as a number. It is `[]` for an unknown or aborted transaction. A committed transaction keeps its edges.

**Read-write antidependencies.** When transaction `T1` reads a key and transaction `T2` writes a newer version of that key, one that `T1` does not see, `T1` must come before `T2` in any equivalent one-at-a-time order: had it run after `T2`, it would have read `T2`'s value. This is a *read-write antidependency*, an *edge* from `T1` to `T2`. In the write skew above there is an edge from each job to the other, a cycle, so no order exists. It has been proved that every non-serializable outcome of snapshot isolation contains a *dangerous structure*: a transaction, the *pivot*, with an edge coming in from a transaction that ran at the same time as it, and an edge going out to a transaction that also ran at the same time as it (the two may be the same transaction, as in write skew). So a store that aborts one transaction of every such structure before all three can commit is serializable. It sometimes aborts a transaction that was harmless, because not every dangerous structure closes a cycle, but it only has to watch reads and writes, not the whole graph. This detection is one known way to make a snapshot store serializable. Others lock every key a transaction reads until it ends, so that a writer of that key waits for it, or keep the whole graph of dependencies and refuse a commit only when it would close a cycle.

**The rules.** Only serializable transactions take part: a transaction from `begin()` and a `put` never get an edge, and a read or a write by one records nothing. An edge is *live* when neither of its two transactions has aborted, and only live edges count anywhere. Let `T` be an active serializable transaction.

1. **A read.** `read(T, key)` when `T` has not written `key` itself (reading its own write records nothing). `T` misses the versions of `key` committed after it started, and the writes of `key` still buffered by active transactions. Call `W` another serializable transaction that either committed a version of `key` stamped after `T`'s start, or is active and has written `key`. First, if some such `W` that has committed has a live edge going out, `W` is a pivot that can no longer be aborted, and the new edge would complete its structure: `T` aborts instead. The read returns `""` and records nothing. Otherwise the store remembers that `T` read `key`, for rule 2, even after `T` commits, and adds an edge from `T` to each such `W`.
2. **A write.** `write(T, key, value)`. Call `R` a serializable transaction other than `T` that read `key` (by rule 1), has not aborted, and either is active or committed after `T`'s start, so that it ran at the same time as `T`. First, if some such `R` has committed and has a live edge coming in, `T` aborts: the write returns `false` and records nothing. Otherwise `T` buffers the write, and the store adds an edge from each such `R` to `T`.
3. **A commit.** `commit(T)` checks first committer wins first, as at level 2. Then, if `T` has a live edge coming in and a live edge going out, `T` is a pivot: it aborts, and the answer is `"dangerous-structure"`.

Recording the same edge twice keeps one edge. A key that has no version yet can still be read, and that read counts.

### Example 1

<!-- case: ex5 -->

Write skew under snapshot isolation. Both jobs read both replicas `up`, take their own replica `down`, and commit, since they wrote different keys. A transaction that begins afterwards sees both replicas down.

### Example 2

<!-- case: ex6 -->

The same jobs, serializable. Transaction 3 read `west`, which 4 then writes: an edge from 3 to 4. Transaction 4 read `east`, which 3 writes: an edge from 4 to 3. So 3 has an edge in and an edge out, and its commit is refused as a pivot. Its edges die with it, so 4 has no live edge left and commits: only `west` goes down.

## Level 4: Horizon and vacuum

Old versions pile up: every `put` and every commit adds one, and nothing removes them. A version can go once no transaction can read it, now or later.

- `horizon()`: the start time of the oldest active transaction, of any kind; when no transaction is active, the current value of the clock. Every transaction that is active, or that will begin later, started at or after the horizon.
- `vacuum()`: removes every *dead* version and lists what it removed. A version of a key is dead when a newer version of the same key is stamped at or before the horizon: every transaction that is active or will begin later sees that newer version, or a newer one still, and never this one. The newest version of each key is never dead. The answer lists each removed version as `"<key>@<stamp>"`, sorted by key (comparing character codes, so `Z` comes before `a`), then by stamp as a number. `versions` no longer lists what was removed. `vacuum` does not tick the clock.

A vacuum changes no answer of any other method: what it removes, no transaction can read, and first committer wins only looks at versions stamped after a start time, which are never dead. The records of level 3 are not touched.

### Example 1

<!-- case: ex7 -->

Transaction 3 began after the version stamped 2 and before 4, so the horizon is 3. The version stamped 1 is dead, since 2 is at or before the horizon; 2 is not, because transaction 3 still reads it. Once 3 commits at time 6, no transaction is active, the horizon is the clock, 6, and only the newest version survives.

### Example 2

<!-- case: ex8 -->

Transaction 3 holds the horizon at 3, where `a` and `b` each have exactly one version at or before it, so nothing is dead. Once 3 aborts, transaction 5 holds the horizon at 5: `a@1` is dead because `a@4` is at or before 5, but `b@2` is still read by transaction 5. Transaction 5 still reads exactly what it read before.

## Constraints

- At most `10^4` calls per test.
- At most `2000` transactions per test, and at most `100` keys.
- `tx` is any integer from `-10^9` to `10^9`.

## Follow-ups

- A store can also keep uncommitted versions in the version lists, and decide visibility from the list of transactions that were running when the snapshot was taken. What would `read` look like then, and what does an abort have to undo?
- First committer wins lets a doomed transaction run on until its commit. A store can check at the write instead: a write to a key that a concurrent transaction has written waits for that one to finish, and aborts if it commits (first updater wins). What does each choice cost?
- The reads of a committed serializable transaction are kept forever here. When can they be dropped safely, and how does that interact with the horizon?
- A read-only transaction can be part of a dangerous structure. When can a read-only serializable transaction be sure that it will never be aborted, and could it then skip recording its reads?
- The rules keep one edge per pair of transactions. Keeping only two flags per transaction, "has an edge in" and "has an edge out", is cheaper. Which outcome of Example 2 changes, and why?

## Hints

### Hint 1

Keep, for each key, a list of versions in commit order, each a stamp and a value. Because the clock only grows, every new version goes at the end, and the list stays sorted by stamp. Reading at a start time is then a search for the last stamp before it.

### Hint 2

Keep one record per transaction: its start time, its state, the keys and values it has written so far, and later its commit time. Writes stay in that record until the commit, which is the moment to stamp them and append them to the version lists.

### Hint 3

First committer wins needs only the version lists: at commit time, look at the newest version of each key the transaction wrote. If its stamp is after the transaction's start time, someone else committed that key in the meantime.

### Hint 4

For level 3, add to each serializable transaction the set of keys it read, the ids of the transactions with an edge to it and the ids of those it has an edge to, and keep a map from each key to the transactions that read it. Remember who wrote each version, so a read can find the writers of the versions it missed.

### Hint 5

Do not delete edges when a transaction aborts. Keep the sets as they are and, whenever you need edges, keep only those whose other end has not aborted. The same filter answers `antidependencies`, the pivot check at commit, and the two early aborts.

### Hint 6

In a read and in a write, do the check that may abort the transaction before you record anything. Collect the transactions involved, test them, and only then add the read and the edges.

### Hint 7

The horizon is a minimum over the active transactions. For each key, the versions to keep start at the newest one stamped at or before the horizon: find it with the same search as a read, and drop everything before it. Sort the keys before you build the report.
