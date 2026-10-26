# Transactional Key-Value Store: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| undo-log | optimal | O(1) per read, write and count; O(c) per rollback or commit; O(log h) per snapshot read | O(n + u + h) | default answer; reads never look past the live map |

Here `c` is the number of keys a transaction changed, `n` the number of keys stored, `u` the entries in open undo logs, and `h` the number of permanent values ever written for one key.

## How the design grows level by level

| Level | New requirement | What the design adds |
|-------|-----------------|----------------------|
| 1 | Set, get, remove, count by value | `data: key -> value` plus `counts: value -> number of keys`; one `assign` helper updates both |
| 2 | Begin and rollback | An undo log: for each key the transaction touched, the value it had before the first touch |
| 3 | Nesting | A stack of undo logs; `rollback` pops and replays only the innermost |
| 4 | Commits and numbered snapshots | Nested commit merges its log into the parent; outermost commit appends the touched keys' values to a per-key history under a new sequence number and records that number as the snapshot |

There are two classic ways to build transactions, and the choice decides how hard each level is:

- **Overlay**: keep the committed map untouched and stack one map of pending changes per transaction. Reads look through the stack from the top. Rollback is O(1), but every `get` costs O(depth) and `count` is hard, because a value's count depends on every layer.
- **Undo log** (the reference): apply changes to the live map at once and remember how to undo them. Reads and `count` stay O(1) because the live map is always the current view, and rollback replays the remembered values. Level 1 code does not change at all when transactions arrive.

## Approach: undo-log (Live map with an undo log per transaction)

### Intuition

Readers always want the newest view, transactions included, so make the live map that view and keep the per-value counts on it. A transaction then only needs to remember what to put back: for each key it touched, the value before its first change. Nesting is a stack of such logs. Committing a nested transaction means the parent now owns those changes, so the parent's log must also be able to undo them: it inherits every remembered value for keys it had not touched itself.

### Algorithm

1. `assign(key, value or absent)`: update `data`, decrement the count of the old value and increment the count of the new one.
2. `change(key, value or absent)`: if a transaction is open and its log has no entry for `key`, remember `data[key]` (possibly absent). Then `assign`. If no transaction is open, `assign` and make the key's new value permanent (step 6).
3. Level 1: `set` and `remove` call `change` (`remove` first checks the key exists); `get` and `count` read the maps.
4. Levels 2 and 3: `begin` pushes an empty log. `rollback` pops the innermost log and `assign`s every remembered value back. `depth` is the stack size.
5. Level 4, `commit`: pop the innermost log. If a log remains, copy into it every entry for a key it does not already have, and return 0. Otherwise make all keys of the popped log permanent, record the current sequence number as a new snapshot, and return the number of snapshots.
6. Making keys permanent: increase the sequence number once, then append `(sequence, data[key])` to each key's history.
7. `getSnapshot(version, key)`: look up the snapshot's sequence number and binary-search the key's history for the last entry at or before it.

### Correctness

Invariant 1: `data` is the current view and `counts[v]` is the number of keys whose value in `data` is `v`. Only `assign` writes `data`, and it adjusts both counts.

Invariant 2: for each open transaction `T`, replaying `T`'s log over `data` yields the state just before `T` began, provided all transactions inside `T` were already undone. The log records the value before `T`'s first change of each key, and later changes of that key inside `T` do not overwrite it. When a nested transaction `I` commits into `T`, `I`'s changes become `T`'s: for a key that `T` already touched, `T`'s entry is older and stays; for a key only `I` touched, `I`'s entry is the value before `T` touched it either, because `T` had not. So the invariant still holds for `T`.

Invariant 3: each key's history lists its permanent values in sequence order, and a snapshot's sequence number `s` captures exactly the permanent state at its commit: every permanent change before the commit has a sequence at most `s`, and every later change has a larger one. Changes inside open transactions never reach the history until the outermost commit.

### Complexity

- Time: O(1) per read, write and count; O(c) per rollback or commit; O(log h) per snapshot read — reads and writes are map operations; rollback and commit visit each key the transaction changed once; a snapshot read is one binary search. Java and Kotlin use a `TreeMap` per key for the history, which makes a permanent write O(log h).
- Space: O(n + u + h) — the live map and counts, one log entry per key per open transaction, and every permanent value ever written.

### Trade-offs

- The overlay design makes rollback O(1) and leaves the committed map clean, which is what you want when another reader must not see uncommitted data. It makes `get` O(depth) and `count` expensive. Ask which operations the interviewer expects to be hot before choosing.
- Snapshots by full copy are simpler but cost O(n) per commit. The per-key history costs O(c) per commit and O(log h) per read, and never copies untouched keys.
- History grows forever. A bound (keep the last `k` snapshots) would need pruning of history entries older than the oldest kept snapshot, per key.

### Pitfalls and edge cases

- Remember the value before the first change only. Recording the value before every change would make rollback restore an intermediate value.
- Remember absence explicitly. A key created inside a transaction must disappear on rollback, so the log needs an "absent" marker, not just a missing entry.
- A nested commit must not let the child's entry replace the parent's older one, and must not treat a remembered "absent" as a missing entry (see the Kotlin note).
- `count` must be updated on rollback as well as on writes.
- An outermost commit with no changes still takes a snapshot and returns its number.
- `rollback` and `commit` with no open transaction return `false` and `-1` and change nothing.

### Language notes

- Python: `dict.setdefault(key, previous)` adds a log entry only if the key is new, and checks presence, not truthiness, so a remembered `None` (absent) is kept. `collections.Counter` returns 0 for unseen values.
- TypeScript: `Map.has` distinguishes "remembered as absent" (`null`) from "not remembered"; `Array.prototype.at(-1)` reads the innermost log.
- Java: an `ArrayDeque` of `HashMap`s is the stack (`push` and `peek` work on the innermost); `HashMap` accepts `null` values for "absent", and `containsKey` tells the two cases apart. The history stores `Optional<String>` so that a removal is a value in the `TreeMap`.
- Kotlin: `HashMap.putIfAbsent` treats a key mapped to `null` as absent and would overwrite the parent's remembered absence during a nested commit, so the reference checks `key !in enclosing` instead. `ArrayDeque.removeLastOrNull()` keeps the guard clauses short.
