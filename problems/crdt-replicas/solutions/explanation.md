# CRDT Replicas: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| join-per-entry | optimal | O(1) per write or add; O(S) per merge or sync | O(S) | default answer; it survives all four levels without a rewrite |

Here `S` is the number of entries in the source replica's state: two per counter and replica at most, one per register, and one or two per add.

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | Counters | per counter, a map from replica id to an up total and a down total; merge keeps the larger of each total |
| 2 | Registers | per register, the text with its timestamp and writer; merge keeps the greater `(timestamp, writer)` |
| 3 | Sets | per set and element, a map from tag to a removed flag; merge takes every tag and every removed flag |
| 4 | Delta sync | every entry also keeps the change number at which it last grew, and each replica keeps the change number each target last acknowledged |

Every level adds a structure of the same shape: a map whose values only grow, merged entry by entry by taking the larger value. That is why the merge of level 1 extends to every later level without changing what it already does, and why level 4 can treat all entries alike.

## Approach: join-per-entry (Every piece of state is an entry that only grows and joins by maximum)

### Intuition

A merge has to be safe to repeat, to reorder and to regroup. Taking the maximum of two numbers is all three: `max(x, x) = x`, `max(x, y) = max(y, x)`, and `max(max(x, y), z) = max(x, max(y, z))`. So the design gives every replica a state made only of values that grow, and a merge takes the larger of each. The art is choosing values that grow and still carry the meaning. One number per counter does not work: two replicas that each added 1 both hold 1, and the larger is 1, not 2. Keeping each replica's own total apart does work: a replica only raises its own total, so the larger of two copies of the same total is simply the newer one, and the value is the sum of the newest totals.

The same idea gives the register (the stamp only grows, and the larger stamp is the newer write in the order every replica agrees on) and the set (a set of tags only grows when tags are added, and a set of removed tags only grows when tags are removed). Level 4 then asks which entries grew since the last exchange, which a counter of changes answers.

### Algorithm

1. Each replica keeps a change counter `clock`, starting at 0. Every time an entry of its state appears or grows, the replica adds 1 to `clock` and stores the new value in the entry as the entry's last change.
2. Counters: `increment(replica, counter, amount)` adds `amount` to the replica's own up total for the counter; `decrement` adds to its own down total. `value` is the sum of the up totals minus the sum of the down totals.
3. Registers: `write` builds the stamp `(timestamp, replica)` and stores the text only when the register is empty or the stamp is greater than the stored one, comparing timestamps first and writers second. `read` returns the stored text or `""`.
4. Sets: `add` counts the replica's adds, builds the tag `"<replica>:<n>"` and stores it under the element with the removed flag off. `remove` sets the flag on every tag of the element that is not removed yet and returns how many. `contains` asks whether any tag of the element is not removed; `elements` sorts the elements that have one.
5. `absorb(source, since)` walks every entry of the source whose last change is greater than `since`, counts it, and joins it into the receiver: the larger total, the greater stamp, the tag if missing, the removed flag if set. An entry that grows at the receiver gets a new change number there.
6. `merge(source, target)` is `absorb` with `since = 0`, which walks every entry. `sync(source, target)` is `absorb` with `since = acked[target]` (0 at first), returns its count, and then sets `acked[target]` to the source's current `clock`.

### Correctness

Every piece of state is a value in an order where a join exists: totals ordered as numbers with `max`, stamps ordered as pairs with the larger pair, sets ordered by inclusion with union. A state is a map of such values, and merging two states joins them key by key, so the merge of whole states inherits the three properties of each join: it is commutative, associative and idempotent. Every change made at a replica only raises its own state in that order: an increment raises the replica's own total, a write that takes effect stores a greater stamp, an add or remove adds a tag or a flag. Together these are the monotonic semilattice conditions of Shapiro, Preguiça, Baquero and Zawirski, whose Theorem 1 states that such an object is strongly eventually consistent: replicas that have delivered the same updates have equivalent state, whatever the order of the merges.

The values mean what the levels promise. A replica's own total is the sum of the amounts it applied; another replica's total, as held anywhere, is the sum of a prefix of that replica's changes, and the larger of two prefixes of the same sequence is the longer one, so the merged value counts each change exactly once. A replica only stores a write that beats its stamp, so every stamp names one write, and the greater stamp is the same at every replica. A remove flags exactly the tags its replica has seen; a tag created elsewhere at the same time is not among them, so the add survives, which is the add-wins rule.

Delta sync: let `t` be the source's `clock` when the target last acknowledged it. Every entry of the source whose last change is at most `t` was sent to the target at that sync or an earlier one, by induction over the syncs between the two. The target's state only grows, so for each such entry it still holds a value at least as large. Joining only the entries changed after `t` therefore gives the same result as joining all of them, which is the full merge. An entry that changed several times since `t` holds its newest value, which is the join of all its intermediate values, so sending it once is enough.

### Complexity

- Time: O(1) per write or add; O(S) per merge or sync — a write, an add and a register read touch one map entry; an increment, a decrement and `value` sum the totals of one counter, at most one per replica; a remove visits the tags of one element; `elements` sorts the `k` elements of a set in O(k log k); a merge walks all `S` entries of the source, and so does a sync, which compares each entry's last change with the acknowledgement.
- Space: O(S) — every entry is stored once per replica that has seen it, with a constant number of numbers beside it, plus one acknowledgement per pair of replicas that has synced.

### Trade-offs

- A sync here still walks every entry of the source to find the changed ones. Keeping the entries in a list ordered by last change, or a buffer of the deltas of each change as Almeida, Shoker and Baquero do, makes the walk proportional to what changed. The saving that matters, the bytes on the network, is the same either way.
- Sending the whole state is the simplest protocol and tolerates anything: lost, repeated and reordered messages, and a replica that forgot everything it knew about its peers. Deltas need the acknowledgement bookkeeping, and an acknowledgement that is lost only means some entries are sent again, which is harmless because joining is idempotent.
- An operation-based design sends each operation instead of state, which is smaller still, but increments are not idempotent: the network must then deliver each operation exactly once, which is the guarantee that a state-based design never needs.
- Removed adds stay in the state for ever. Forgetting one safely needs every replica to have seen the remove, which needs knowledge of all replicas and of what each has seen.
- Last writer wins keeps the design simple and the register small, at the price of silently dropping one of two concurrent writes. A register that keeps every concurrent text is the alternative when no write may be lost.

### Pitfalls and edge cases

- Level 1, one number per counter. A counter merged by maximum loses concurrent increments: 3 and 2 merge to 3 instead of 5. Hidden case `h1` counts on three replicas at once and merges them pairwise.
- Level 1, adding instead of taking the maximum. A merge that adds two totals counts the same change again on every repeated or indirect merge. Hidden case `h2` merges the same state three times, and `h3` passes a change along a chain of replicas.
- Level 1, overwriting. Copying the source's total over the target's, even when the target's is newer, rolls back changes the target made since: `h4` merges an old copy of `a`'s own total back into `a`.
- Level 1, sending only the source's own total. A merge must pass on what the source learned from others too, or changes stop after one hop (`h3`, `h7`).
- Level 1, decrements. A decrement that lowers the replica's single total cannot survive a merge by maximum, because a smaller value always loses; that is why the down total is separate and only grows. Hidden case `h5` merges negative values across three replicas.
- Level 2, arrival order. The last merge to arrive must not win: `h8` merges the newer write before the older one. Equal timestamps go to the greater replica id at every replica, in both merge directions (`h9`), and a tie-break that keeps the target's text makes the result depend on the order.
- Level 2, local writes. A write with the same stamp as the current text, or an older one, is ignored and returns `false`; that includes a write whose timestamp equals that of a text from a greater replica id (`h10`). A fast clock wins later writes in real time (`h12`), which is the known cost of last writer wins.
- Level 3, removing by element. Recording "milk is removed" instead of the removed tags makes the element stay removed against an add the remover never saw, and makes adding it back impossible (`h13`, `h14`). Keying adds by replica and element instead of a unique tag has the same effect on a second add of the same element (`h14`).
- Level 3, tombstones in the merge. A merge that takes the adds but not the removed flags brings removed elements back (`h15`). A remove returns the number of tags it flagged, which can be more than one when several replicas added the element (`h16`, `h17`).
- Level 3, counting tags. The tag counter counts the replica's own adds in all sets, and merges do not move it (`h17`, `h18`). `elements` lists each element once, sorted (`h17`).
- Level 4, one acknowledgement per source. The acknowledgement belongs to the pair `(source, target)`: after `sync(a, b)`, `sync(a, c)` must still send everything `c` has not acknowledged (`h19`).
- Level 4, forwarding. Entries that arrived at the source through a merge or a sync have changed there and must be sent on, or changes stop after one hop (`h20`, `h21`). Entries the target already holds in a newer version are still sent, and change nothing (`h23`).
- Level 4, counting. The count is the number of distinct entries sent, not the number of changes since the acknowledgement (`h25`), and `stateSize` counts the up and down totals of a slot apart and a removed add twice (`h22`).

### Language notes

- Python: dataclasses keep the small records readable, and tuples compare element by element, so `(timestamp, writer)` comparisons are one `>`.
- TypeScript: `Map` keeps insertion order and never confuses a key with an inherited property; `sort()` without a comparator compares UTF-16 code units, which agrees with the other languages on these ASCII names, and the explicit comparator states the order. Timestamps up to `10^12` are exact in a `number`.
- Java: nested `HashMap`s with `computeIfAbsent` build the structure on first use; `String.compareTo` compares by character code, as the stamp order needs. Totals are `long` inside and returned as `int`.
- Kotlin: `getOrPut` plays the part of `computeIfAbsent`, and `>` on strings calls `compareTo`. The helper classes are `private` to the file.
- Go: maps of pointers to small structs let `absorb` update an entry in place. Map iteration order is random, which is harmless here because every result is a count, a sum, a single value or a sorted list. A parameter named like a type shadows it inside the function, so the helper types have names no parameter uses.
- Rust: a merge reads one replica and writes another from the same map, which the borrow checker refuses; the target is taken out of the map with `remove` and put back after the join. Tuples compare lexicographically, so `(timestamp, writer)` comparisons are one `>`.

## Further reading

- [Shapiro, Preguiça, Baquero and Zawirski, "Conflict-free Replicated Data Types", SSS 2011, LNCS 6976, pages 386 to 400](https://www.cs.tufts.edu/~nr/cs257/archive/marc-shapiro/CRDTs_SSS-2011.pdf): the definition of strong eventual consistency, the monotonic semilattice condition under which state-based replicas converge (their Theorem 1), and counters built from two increment-only vectors.
- [Shapiro, Preguiça, Baquero and Zawirski, "A comprehensive study of Convergent and Commutative Replicated Data Types", INRIA research report RR-7506, 2011](https://inria.hal.science/inria-00555588): the G-Counter and PN-Counter (Specifications 6 and 7), the state-based LWW-Register with timestamps made unique by a replica identifier (Specification 8 and section 3.2.1), the 2P-Set with its tombstone set (Specification 12), and the Observed-Remove Set, specified operation-based (Specification 15), whose state-based form the report leaves as an exercise; level 3 is that exercise.
- [Almeida, Shoker and Baquero, "Delta State Replicated Data Types", Journal of Parallel and Distributed Computing 111, 2018](https://arxiv.org/abs/1603.01529): delta-mutators that return a small state to join instead of the full state, delta-groups, and an anti-entropy algorithm that keeps an acknowledgement per neighbour and sends the join of the deltas since it (Algorithm 2). Level 4 records which entries changed instead of buffering deltas: where Algorithm 2 forwards a received delta whole when any part of it is new, level 4 forwards only the entries that grew.
