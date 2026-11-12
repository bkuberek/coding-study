# MVCC Snapshot Isolation: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| version-chains | optimal | O(log v) per plain read; O(w + e) per commit; O(v + t + e) per serializable read or write; O(V + K log K) per vacuum | O(V + T + R + E) | default answer; one version list per key and one record per transaction serve all four levels |

Here `v` is the number of versions of the key, `w` the number of keys a transaction wrote, `t` the number of transactions, `e` the number of edges looked at, `V` the number of versions in all, `K` the number of keys, `T` the number of transactions, `R` the number of recorded reads and `E` the number of edges.

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | Versions are appended, never overwritten; a snapshot is a start time | the clock; per key, parallel lists of stamps and values, sorted because the clock only grows; per transaction, its start time and state |
| 2 | Writes wait in the transaction until the commit stamps them | per transaction, its buffered writes and its commit time |
| 3 | Serializable transactions leave their reads behind and collect edges | per key, the writer of each version and the serializable transactions that read it; per transaction, the ids of its incoming and outgoing edges |
| 4 | The oldest snapshot bounds what can still be read | nothing new: the horizon is a minimum over the transaction records, and a vacuum cuts each version list |

The early choice that keeps the later levels small is to buffer writes in the transaction. The version lists then hold only committed data, so a read never has to ask whether a version's writer committed, an abort only drops a map, and first committer wins is one look at the newest stamp of each written key.

## Approach: version-chains (Version chains with read records and conflict edges)

### Intuition

A snapshot is a point on the clock. Every version carries the commit time of its writer, and the clock only grows, so the versions of a key are sorted by stamp as they are appended, and "what did this key look like at time `s`" is a binary search. Snapshot isolation needs one more rule, first committer wins, to stop two transactions from overwriting each other's writes blindly: a transaction may not commit a key that changed after it started.

Snapshot isolation still lets a transaction act on data that a concurrent transaction is about to change, which is write skew. The theory says that every such anomaly contains a transaction with a read-write antidependency coming in and one going out. So the store records, for serializable transactions, who read what, and turns every "read an old version" and "wrote over a read" into an edge. A transaction that would commit with an edge in and an edge out is refused; if the transaction in the middle has already committed, the transaction that adds the second edge is refused instead.

### Algorithm

1. **Clock.** `put`, `begin`, `beginSerializable` and a successful `commit` each add 1 to the clock and use the new value. A failed commit, an abort and a vacuum do not.
2. **Versions.** Each key has a list of stamps, a list of values and a list of writers (0 for a `put`), appended together. `read` returns the transaction's own buffered value if it wrote the key, otherwise the value at the last stamp before its start, found with a binary search.
3. **Commit.** Refuse an inactive transaction. If the newest stamp of any key it wrote is after its start, abort it with `"write-conflict"`. If it is serializable and has a live incoming and a live outgoing edge, abort it with `"dangerous-structure"`. Otherwise tick, set the commit time and append one version per written key.
4. **Serializable read.** Unless the transaction wrote the key, collect the serializable writers of the versions stamped after its start, and the active serializable transactions that buffered a write of the key. If one of the committed writers has a live outgoing edge, abort the reader and return `""`. Otherwise remember the read and add an edge from the reader to each writer.
5. **Serializable write.** Collect the serializable readers of the key, other than the writer, that are not aborted and are active or committed after the writer's start. If one of them has committed and has a live incoming edge, abort the writer and return `false`. Otherwise add an edge from each reader to the writer and buffer the write.
6. **Live edges.** Edges are never deleted. Every question about edges first drops those whose other end has aborted, and an aborted transaction reports none.
7. **Horizon and vacuum.** The horizon is the smallest start time among active transactions, or the clock when none is active. For each key, find the newest stamp at or before the horizon; every version before it is dead. Report them by key, then by stamp.

### Correctness

**Snapshots.** A version is appended with a stamp larger than every earlier tick, so each list is sorted, and a version stamped before a transaction's start was committed before it began. Buffered writes reach the lists only at the commit, so no transaction sees another's uncommitted write, and a transaction sees its own writes through its buffer.

**First committer wins.** Every version of a key stamped after `T`'s start was committed by someone else while `T` was running, because `T`'s own versions are appended only at its commit. The newest stamp is the largest, so looking at it alone decides whether such a version exists.

**Edges.** A read-write antidependency from `T1` to `T2` on a key exists once both the read and the newer write have happened, and the rules catch it whichever comes second. If the read comes second, `T2`'s version is either committed after `T1` started, or buffered by an active `T2`, and rule 1 adds the edge. If the write comes second, `T1`'s read is on record and `T1` is active or committed after `T2` started, and rule 2 adds the edge. An edge between two transactions that did not run at the same time cannot be part of a dangerous structure, and the rules never add one.

**Dangerous structures are broken.** Suppose a pivot `P` has a live incoming edge and a live outgoing edge. If both exist when `P` tries to commit, the commit refuses it. If `P` committed first, the edge added after its commit was added by a read or a write of another transaction, and the rule for that operation sees a committed transaction with a live edge on the other side, and aborts the transaction that would add the edge. So no pivot ever commits with both edges live, and by the theorem every cycle, hence every non-serializable outcome, is broken. An edge whose end has aborted cannot be part of any committed cycle, which is why only live edges count.

**Vacuum.** A version is dead when a newer version of its key is stamped at or before the horizon. Every active transaction started at or after the horizon, and a start time never equals a stamp, so each of them, and every later one, sees that newer version or a newer one still. First committer wins and the read rule only look at versions stamped after a start time, so they never needed a dead version.

### Complexity

- Time: O(log v) per plain read; O(w + e) per commit; O(v + t + e) per serializable read or write; O(V + K log K) per vacuum — a plain read is a binary search; a commit checks the newest stamp of each written key and filters its own edges; a serializable read walks the versions after its start and the transactions that may hold a buffered write, and a serializable write walks the readers of the key; checking whether an edge is live is a lookup of the other end's state. A vacuum looks at every key once and sorts the keys for the report.
- Space: O(V + T + R + E) — one entry per version, one record per transaction, one entry per recorded read and two per edge. Nothing is ever forgotten except dead versions.

### Trade-offs

- **Buffered writes or versions in place.** A store can instead write a new version into the table at once, uncommitted, and decide its visibility from the state of its writer and the list of transactions running when the snapshot was taken. That makes a commit cheap and an abort a matter of marking the writer, but every read has to filter the uncommitted versions. Buffering keeps the lists clean and makes the commit pay instead.
- **First committer or first updater.** Checking at the commit lets a transaction that will fail keep working until the end. Checking at the write, with a lock that makes a second writer of the same key wait for the first, fails early, but needs locks and waits.
- **Edges or flags.** The algorithm that introduced this kind of detection kept two booleans per transaction, "has an edge in" and "has an edge out". Flags are cheaper and need no lists, but they cannot be cleared when the other end aborts, so they abort more transactions that were harmless: in the second example of level 3, transaction 4 would be refused too. Keeping the other end of every edge also allows refinements that skip structures that cannot close a cycle.
- **Precision.** A dangerous structure is necessary for an anomaly, not sufficient. Building the whole dependency graph and testing it for cycles aborts only what must be aborted, at the price of tracking write-read and write-write dependencies as well.
- **Memory.** The reads of a committed serializable transaction are kept here forever. They are needed only while a transaction that overlapped it is still running, so they can be dropped once every such transaction has finished.

### Pitfalls and edge cases

- `begin` ticks the clock, so transaction ids and version stamps interleave (`h1`). A snapshot sees the versions stamped before its start, which is strictly before, though the two can never be equal anyway.
- A transaction that began before a key existed never sees it, whatever is committed later (`ex2`, `h2`). Unknown ids, 0 and stamps of `put` read nothing.
- A transaction reads its own latest write, and only its own (`h6`). A failed commit and an abort take no tick and leave no version (`h5`); a read-only commit does tick (`h7`).
- First committer wins compares with the start time, so a `put` made after a transaction started beats it (`h4`), and a transaction that started after the other committed does not conflict (`h7`). The first to commit wins even if it wrote last (`h5`).
- Plain transactions and `put`s are invisible to the level 3 rules (`h12`): adding edges for them aborts snapshot-isolation transactions that asked for nothing more.
- The reads of a serializable transaction must survive its commit, or the read-only anomaly goes unseen (`h9`): there the edge into the pivot comes from a reader that committed long before the pivot writes.
- A reader that committed before the writer began, or a version committed before the reader began, makes no edge (`h13`).
- Both kinds of missed write make an edge on a read: a committed newer version and a write still buffered by an active transaction (`h14`).
- Reading one's own write records nothing, so a later writer of that key gets no edge from it (`h14`, `h24`).
- An aborted transaction's edges stop counting at once, for `antidependencies`, for the pivot check and for the early aborts (`ex6`, `h11`, `h15`). Removing them only for the pivot check, or never, gives different answers.
- When the pivot has already committed, the transaction that adds the second edge aborts at its read (`h11`) or its write (`h10`, `h21`), not at its commit; and the abort check comes before anything is recorded.
- The write-conflict check comes before the pivot check (`h22`).
- `antidependencies` sorts ids as numbers: `in:9` before `in:10` (`h23`).
- With no transaction active the horizon is the clock, and a version stamped exactly at the horizon makes the older ones dead (`h17`). Any active transaction holds the horizon, serializable or not, read-only or not (`h19`).
- The vacuum report sorts by key by character codes and by stamp as a number (`h18`).

### Language notes

- Python's `bisect_left` on the list of stamps gives the number of versions before a start time. Rust has `partition_point`, Go `sort.SearchInts`, Java `Collections.binarySearch` (which returns `-(insertion point) - 1` when the value is absent, and the start time is always absent from the stamps), Kotlin's `binarySearch` on a list with the same convention, and TypeScript needs a short loop.
- Sorting ids as numbers is the natural sort of `int` keys in every language; it is the string form `"in:10"` that must not be sorted. Sort the ids, then format them.
- Sorting the keys for the vacuum report by character codes is the default string order in Python, Java, Kotlin, Go and Rust; in TypeScript the default `sort()` compares UTF-16 code units, which is the same for the ASCII keys of this problem.
- Rust borrows: checking the other transactions while changing one needs care. The Rust reference collects the ids to look at into a `Vec` first, checks them with shared borrows, and only then takes `&mut` to the records it changes.
- Go has no set type, so the Go reference keeps the edges in a `map[int]bool` and sorts the live ids before it formats them. The Rust reference uses a `BTreeSet<i32>`, which keeps them sorted already.

## Further reading

- H. Berenson, P. Bernstein, J. Gray, J. Melton, E. O'Neil and P. O'Neil, "A critique of ANSI SQL isolation levels", SIGMOD 1995, [doi:10.1145/223784.223785](https://doi.org/10.1145/223784.223785); also Microsoft Research technical report MSR-TR-95-51. Section 4.2 defines snapshot isolation with a start timestamp, a commit timestamp and the first-committer-wins rule, and shows that it allows write skew (A5B).
- A. Fekete, D. Liarokapis, E. O'Neil, P. O'Neil and D. Shasha, "Making snapshot isolation serializable", ACM Transactions on Database Systems 30(2), 492-528, 2005, [doi:10.1145/1071610.1071615](https://doi.org/10.1145/1071610.1071615). Theorem 2.1: every cycle in the dependency graph of a non-serializable snapshot-isolation history has two consecutive read-write antidependencies between concurrent transactions. Example 1.3 is the read-only anomaly that the hidden case `h9` follows; the article also describes first updater wins.
- M. J. Cahill, U. Röhm and A. D. Fekete, "Serializable isolation for snapshot databases", SIGMOD 2008, [doi:10.1145/1376616.1376690](https://doi.org/10.1145/1376616.1376690); extended in ACM Transactions on Database Systems 34(4), 2009, [doi:10.1145/1620585.1620587](https://doi.org/10.1145/1620585.1620587). The detection algorithm: SIREAD locks kept after the commit, an edge noticed at a read of an old version or at a write over a recorded read, the pivot aborted at its commit, and the reader or the writer aborted when the pivot has already committed. It keeps two flags per transaction where this problem keeps edges.
- D. R. K. Ports and K. Grittner, "Serializable snapshot isolation in PostgreSQL", Proceedings of the VLDB Endowment 5(12), 1850-1861, 2012, [doi:10.14778/2367502.2367523](https://doi.org/10.14778/2367502.2367523). Why a production implementation keeps a list of conflicts per transaction instead of flags (it can drop the conflicts of an aborted transaction), and the read-only refinements.
- A. Adya, "Weak Consistency: A Generalized Theory and Optimistic Implementations for Distributed Transactions", PhD thesis, MIT, 1999. Definition 4 defines anti-dependencies: a transaction anti-depends on another when it installs the next version of an object the other read.
- [Transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html) and [routine vacuuming](https://www.postgresql.org/docs/current/routine-vacuuming.html) in the PostgreSQL documentation: repeatable read as snapshot isolation, serializable as serializable snapshot isolation with non-blocking predicate locks, and why old row versions stay until no transaction can see them.
