# Transactional Key-Value Store

## Statement

Build `TransactionalStore`, a map from string keys to string values that supports transactions. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

Every method takes the current time as its first argument, `timestamp`. No rule depends on it, but it keeps the API uniform with the other practical problems.

## Input

- `TransactionalStore()`: creates an empty store.
- `timestamp`: the time of the call. Within one test, timestamps strictly increase from call to call.
- `key`, `value`: strings.
- Each level's section describes the methods it adds and their other parameters.

## Output

Each method returns what its level describes. A missing value is reported as `""`, and failure with `false` or `-1`, never with an exception.

## Level 1: Keys and value counts

- `set(timestamp, key, value)`: stores `value` under `key`, replacing any earlier value.
- `get(timestamp, key)`: the value under `key`, or `""` when there is none.
- `remove(timestamp, key)`: deletes `key`. Returns `true` when it was present, `false` otherwise.
- `count(timestamp, value)`: how many keys currently hold exactly `value`.

### Example 1

<!-- case: ex1 -->

`a` and `b` both hold `10`, so the count is 2. After `a` changes to `20` only `b` holds `10`, and after removing `b` nobody does. The second `remove` of `b` finds nothing.

## Level 2: Begin and rollback

- `begin(timestamp)`: opens a transaction. Every change made while it is open belongs to it, and every read, `count` included, already sees those changes.
- `rollback(timestamp)`: undoes every change made since the matching `begin` and closes the transaction. Returns `false` when no transaction is open.
- Changes made while no transaction is open are permanent: no `rollback` undoes them.
- This level's tests never call `begin` while a transaction is open.

### Example 1

<!-- case: ex2 -->

Inside the transaction `x` reads `2` and `y` exists. The rollback restores `x` to `1` and removes `y` again, and a second rollback finds no open transaction.

## Level 3: Nested transactions

- `begin` while a transaction is open opens a nested transaction inside it, to any depth.
- `rollback` undoes only the changes of the innermost open transaction and closes it; the enclosing transactions stay open with their own changes.
- `depth(timestamp)`: the number of open transactions.

### Example 1

<!-- case: ex3 -->

The inner transaction changes `a` from `1` to `2`; rolling it back restores `1` and leaves the outer transaction open. Rolling back the outer one removes `a`, which did not exist before.

## Level 4: Commits and snapshots

- `commit(timestamp)`: closes the innermost open transaction and keeps its changes.
  - When it is nested, its changes now belong to the enclosing transaction, so rolling that one back undoes them too. Returns `0`.
  - When it is the outermost, its changes become permanent and the store takes a snapshot of all permanent data at that moment. Snapshots are numbered 1, 2, 3, ... in commit order, and the number is returned.
  - Returns `-1` when no transaction is open.
- `getSnapshot(timestamp, version, key)`: the value `key` had in snapshot `version`, or `""` when it had none or the snapshot does not exist.
- Permanent changes made outside any transaction are part of every later snapshot, but they do not take a snapshot themselves.

### Example 1

<!-- case: ex4 -->

The inner commit returns `0` and leaves one transaction open; the outer commit makes `a = 2` and `b = 5` permanent as snapshot 1. Setting `a` to `3` afterwards changes the store, not the snapshot, and there is no snapshot 2.

## Constraints

- At most 1000 calls per test.
- `1 <= timestamp <= 10^9`, strictly increasing within a test.
- `1 <= version <= 1000`.
- Keys and values are 1 to 10 letters or digits.

## Follow-ups

- How would two clients with separate transactions over the same store see each other's changes?
- Can you make `commit` of an outermost transaction O(1), independent of how many keys it changed?

## Hints

### Hint 1

Keep a count per value next to the map, and update it on every change, so `count` is a lookup.

### Hint 2

Change the live map directly and remember, per transaction, the value each key had before the transaction first touched it. A rollback writes those values back.

### Hint 3

A nested commit hands its remembered values to the enclosing transaction, keeping the older one when both touched a key. For snapshots, record each permanent value with an increasing sequence number and remember the sequence number of each snapshot.
