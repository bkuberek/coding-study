# Logical Clocks: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| stamped-events | optimal | O(n) per event or compare; O(w^2 n) per read or concurrentWrites; O(E log E) per order | O(E n) | default answer; every question is answered from the stamps the events keep |

Here `n` is the number of processes, `E` the number of recorded events and `w` the number of writes to one key.

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | One counter per process; each event keeps its timestamp, its process and whether it is a send | `lamport[p]`, and per event a record; a set of received messages |
| 2 | One vector per process; each event keeps a copy | `vector[p]`, and a vector in each record |
| 3 | Writes are local events that also keep a key and a value | per key, the list of its write events |
| 4 | One `(l, c)` pair per process; each event keeps its pair and its wall reading | `hybrid[p]`, and a pair in each record |

The choice that keeps every level small is to give each event a record that holds everything it was stamped with. Each new level adds one more clock to the update that every event method shares, and one more field to the record. The questions never replay the history: an order is a sort of the records, a comparison reads two vectors, and a read filters the writes of one key.

## Approach: stamped-events (Clocks kept per process and stamped on every event)

### Intuition

Every clock in this problem is a rule of the form "a process's clock moves forward on each of its events, and a receive also takes in what the message carried". So each process needs only its current clock values, and each event keeps a copy of them at the moment it happened. Causality questions then become questions about those copies: a vector is `≤` another exactly when the first event is in the causal past of the second, and the writes a process knows of are the writes in the causal past of its latest event.

### Algorithm

1. Keep per process: `lamport[p]` (0), `vector[p]` (all zeros) and `hybrid[p]` (`(0, 0)`). Keep per event a record: process, Lamport timestamp, vector, hybrid pair, wall reading, whether it is a send, and for a write its key and value.
2. One helper records an event on process `p`, given the message's record for a receive (or nothing). It refuses a process out of range or a name in use. Otherwise: Lamport `C = C + 1`, or `C = max(C, T) + 1` for a receive; vector: copy `vector[p]`, take the entry-wise maximum with the message's vector for a receive, then add one to entry `p`; hybrid: the local rule or the receive rule of the paper. It stores the three new values on the process and in the event's record and returns the Lamport timestamp.
3. `receive` first checks the message: it must name a send event, not received yet, from another process. Only when the helper accepts the event is the message marked as received.
4. `totalOrder` sorts the names by `(lamport, process)`; `hlcOrder` sorts them by `(l, c, process)`.
5. `compare` answers `""` for an unknown name, then `"same"`, then tests `≤` in both directions.
6. `write` records a local event and appends it to the list of its key. `read(p, key)` keeps the writes of the key whose vectors are `≤` `vector[p]`, drops each one whose vector is `≤` that of another kept write, and sorts the values of the rest. `concurrentWrites` compares every pair of writes of the key.
7. `maxOffset` is the largest `l - wall` over the records.

### Correctness

Lamport timestamps: within one process each event adds at least one, and a receive is larger than the message's stamp. Every step of a happened-before chain is one of those two, so the timestamps increase along the chain: `a → b` implies `C(a) < C(b)`, the paper's clock condition. Two events with the same timestamp are therefore never ordered by `→`, and two events of one process never share a timestamp, so `(timestamp, process)` is a total order that extends `→`.

Vectors: entry `j` of a process's vector is the number of events of process `j` in the causal past of its latest event, by induction on the events: a local event adds its own, and a receive adds the sender's past (the maximum is the union of two pasts, since the events of one process form a sequence) and itself. So `V(a) ≤ V(b)` holds exactly when the past of `a` is inside the past of `b`, which is `a → b` or `a = b`. This is Mattern's theorem that `e < e'` if and only if `C(e) < C(e')`. Two different events never have equal vectors, so `≤` between different events is `"before"`.

Siblings: the writes that process `p` knows of are those in the causal past of its latest event, which is the test `V(w) ≤ vector[p]`. A write is superseded when a known write to the same key happened after it, and the siblings are the maximal elements. A replica that merges the versions in every message it receives and drops the dominated ones holds exactly these, because dominance is transitive: a version dropped at any step is dominated by one that is kept or is itself dropped for a larger one.

Hybrid clocks: the update is the paper's, so its theorems apply: `a → b` implies `(l(a), c(a)) < (l(b), c(b))`, and `l` is the largest reading in the event's causal past, its own included. That also proves `l - wall >= 0`, so the maximum offset is never negative. The tie-break by process number makes the order total, because one process's pairs strictly increase: when `l` stays, `c` grows; when `l` grows, the pair grows whatever `c` becomes.

### Complexity

- Time: O(n) per event or compare; O(w^2 n) per read or concurrentWrites; O(E log E) per order — an event copies and merges one vector of `n` entries, a comparison reads two; a read compares every pair of the `w` writes of a key, `n` entries each; an order sorts the `E` records (with `n` small, the comparison of two keys is constant).
- Space: O(E n) — every record keeps a vector of `n` entries, besides a constant number of other fields.

### Trade-offs

- Keeping a vector in every event costs `n` integers per event. A real system keeps the vector only on what it stores or sends (versions, messages), and here the events are what the questions ask about.
- `read` recomputes the siblings from all the writes of the key, `O(w^2 n)`. A replica in a real store keeps the current siblings per key and updates them on each write and each message, at the price of storing versions per replica and shipping them in messages. The rule is the same: drop a version when an incoming one dominates it, and ignore an incoming one that is dominated.
- Lamport timestamps are one integer and give a total order that respects causality; vectors are `n` integers and decide causality exactly; hybrid pairs are two integers that respect causality and stay close to physical time, and the paper notes that they fit a 64-bit timestamp. None of the three alone gives all of these at once.
- Siblings push the merge to the application, which must know how to combine two carts or two documents. Keeping only the write with the latest timestamp is simpler and loses data whenever two writes are concurrent.

### Pitfalls and edge cases

- The receive rule is `max(C, T) + 1`. Taking only the message (`T + 1`), only the process (`C + 1`) or forgetting the `+ 1` breaks hidden case `h1`.
- A refused call records nothing and moves no clock, and a receive that fails because its own name is taken leaves the message waiting for a later receive: `h3`.
- Ties in an order go by process number as a number. Comparing the numbers as text puts `10` before `2`, and sorting by name or by call order differs too: `h2` and `h13`.
- A vector event must keep a copy. In languages where lists are shared by reference, storing the process's own list lets later events change earlier ones.
- `compare` checks for unknown names before `"same"`: an unknown name compared with itself is `""` (`h7`).
- A smaller Lamport timestamp is not "before" (`ex3`, `h6`). Using Lamport timestamps in `compare` passes examples where events happen to be ordered.
- `read` uses what the process knows, not every write in the history (`h11`). Superseding every write of the key on a new write, or picking the one with the latest wall reading or timestamp, fails `h9`.
- Two siblings with the same value are two entries (`h9`), and values are sorted by value, not by event name (`h11`).
- The hybrid receive rule checks both equalities first. Testing `l == old` before `l == old == lm` gives `c + 1` where `max(c, cm) + 1` is due (`h12`, `ex8`).
- The first event at reading `0` is `(0, 1)`, not `(0, 0)`: `l` equals the old `l` of `0`, so `c` counts (`h13`).
- A clock that goes backwards leaves `l` where it was and keeps `c` counting (`h14`).

### Language notes

- Python keeps vectors as tuples, so a record cannot change after it is stored; TypeScript and Java copy with `slice()` and `clone()`, Kotlin with `copyOf()`, Go with `append([]int(nil), v...)` and Rust with `clone()`. Go's slices alias their backing array, so a stored slice must be a fresh one.
- `wall` and `l` are `long` (up to `10^12`): `number` in TypeScript is exact up to `2^53`, `int64` in Go and `i64` in Rust. `c` is small but travels in the same `list<long>`.
- Sorting by several keys: a tuple key in Python, a comparator in TypeScript and Java (`Comparator.comparingInt(...).thenComparingInt(...)`), `compareBy` in Kotlin, `sort.Slice` with a chained `less` in Go, and a tuple key with `sort_by_key` in Rust. Names never tie, because every event has its own name and process numbers break all ties.
- Rust methods take `&mut self` as the bridge requires, and the event records are cloned out of the map before the process state they update is borrowed mutably.

## Further reading

- Leslie Lamport, "Time, Clocks, and the Ordering of Events in a Distributed System", Communications of the ACM 21(7), pages 558 to 565, July 1978, [doi:10.1145/359545.359563](https://doi.org/10.1145/359545.359563): the happened-before relation, the clock condition and its implementation rules IR1 and IR2, the total order with ties broken by an order of the processes, and the mutual exclusion algorithm built on it.
- Colin J. Fidge, "Timestamps in Message-Passing Systems That Preserve the Partial Ordering", Proceedings of the 11th Australian Computer Science Conference, pages 56 to 66, February 1988: vector timestamps, proposed independently of Mattern.
- Friedemann Mattern, "Virtual Time and Global States of Distributed Systems", Proceedings of the International Workshop on Parallel and Distributed Algorithms (Chateau de Bonas, October 1988), North-Holland, 1989: section 7 gives the vector clock rules (tick the own entry, merge by the entry-wise maximum) and the theorem that `e` happened before `e'` exactly when `C(e) < C(e')`.
- Sandeep S. Kulkarni, Murat Demirbas, Deepak Madappa, Bharadwaj Avva and Marcelo Leone, "Logical Physical Clocks", Principles of Distributed Systems (OPODIS 2014), Lecture Notes in Computer Science, Springer, pages 17 to 32, [doi:10.1007/978-3-319-14472-6_2](https://doi.org/10.1007/978-3-319-14472-6_2). The algorithm of this problem and the theorems quoted (causality, `l >= pt`, `l` as the largest clock value heard of, and `|l - pt| <= ε`) were checked in the authors' technical report "Logical Physical Clocks and Consistent Snapshots in Globally Distributed Databases", [University at Buffalo, 2014-04](https://cse.buffalo.edu/tech-reports/2014-04.pdf), Figure 5 and section 3.
- Giuseppe DeCandia and others, "Dynamo: Amazon's Highly Available Key-value Store", Proceedings of the 21st ACM Symposium on Operating Systems Principles (SOSP 2007), pages 205 to 220, [doi:10.1145/1294261.1294281](https://doi.org/10.1145/1294261.1294281): section 4.4 keeps concurrent versions of an object, tells them apart by vector clocks, returns every version that is not an ancestor of another on a read, and lets a later write that saw them all reconcile them.
