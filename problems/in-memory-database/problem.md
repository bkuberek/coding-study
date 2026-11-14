# In-Memory Database

## Statement

Build `InMemoryDatabase`, a store of records. Each record has a string key and holds named fields, and each field holds a string value. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

Every method takes the current time as its first argument, `timestamp`. Nothing reads a clock: time is whatever the caller passes.

## Input

- `InMemoryDatabase()`: creates an empty database.
- `timestamp`: the time of the call. Within one test, timestamps strictly increase from call to call.
- `key`: the record a call reads or writes.
- `field`: a field inside that record.
- Each level's section describes the methods it adds and their other parameters.

## Output

Each method returns what its level describes. A missing value is reported as `""` for strings, never with an exception. A record exists while it has at least one field; reading a record that does not exist is the same as reading an empty one.

## Level 1: Records and fields

- `set(timestamp, key, field, value)`: stores `value` in `field` of record `key`, creating the record or the field when needed and replacing any earlier value.
- `get(timestamp, key, field)`: the value of `field` in record `key`, or `""` when the record or the field is missing.
- `remove(timestamp, key, field)`: removes `field` from record `key`. Returns `true` when the field existed, `false` otherwise.

### Example 1

<!-- case: ex1 -->

The second `set` of `name` replaces `ana` with `bo`. `age` was never stored, so it reads as `""`. The first `remove` of `city` removes it and returns `true`; the second finds nothing and returns `false`.

## Level 2: Field scans

- `scan(timestamp, key)`: every field of record `key` as a string `"<field>(<value>)"`, ordered by field name in ascending string order. An empty list when the record has no fields.
- `scanByPrefix(timestamp, key, prefix)`: the same, restricted to the fields whose name starts with `prefix`. The empty prefix matches every field.

### Example 1

<!-- case: ex2 -->

`color` sorts before `colorcode`, which sorts before `model`. Two fields start with `col`, none starts with `x`, and the record `bike` does not exist, so its scan is empty.

## Level 3: Expiring fields

- `setWithTtl(timestamp, key, field, value, ttl)`: like `set`, but the field lives only for `ttl` time units. It is visible at every time `t` with `timestamp <= t < timestamp + ttl` and missing from `timestamp + ttl` on.
- An expired field behaves exactly like a missing one in every method: `get` returns `""`, `remove` returns `false` and changes nothing, and scans leave it out.
- Writing a field again replaces its expiry: after `set` it never expires, and after another `setWithTtl` it expires at the new time.

### Example 1

<!-- case: ex3 -->

`token` is written at 10 with a lifetime of 5, so it is visible up to 14 and gone at 15. The scan at 16 shows only `user`, and removing the expired `token` returns `false`.

## Level 4: Point-in-time reads

- `getAt(timestamp, key, field, atTimestamp)`: the value `field` of record `key` had at time `atTimestamp`, or `""` when it was missing then. The state at time `t` is the result of every call with a timestamp at most `t`; expiry is judged at `atTimestamp`, not at `timestamp`.
- `scanAt(timestamp, key, atTimestamp)`: what `scan` would have returned at time `atTimestamp`.
- `atTimestamp` is never later than `timestamp`, and may be earlier than the first call.

### Example 1

<!-- case: ex4 -->

`plan` was `free` from 1 to 4, `pro` from 5 to 8, and deleted at 9. At time 0 nothing was stored yet. At 7 the record held `plan` and the still-live `promo`; at 10 `plan` was deleted and `promo`, written at 6 with a lifetime of 4, had expired.

## Constraints

- At most 1000 calls per test.
- `1 <= timestamp <= 10^9`, strictly increasing within a test.
- Keys, fields and values are 1 to 10 lowercase letters or digits; a prefix is 0 to 10 of them.

## Follow-ups

- How would you bound memory if history only had to be kept for the last hour?
- How would `scanAt` change if records had thousands of fields but each scan read only a few?

## Hints

### Hint 1

A map of maps answers level 1 and level 2. Sort the matching fields when you scan.

### Hint 2

Store an expiry time next to each value, and compare it with the time you are reading at.

### Hint 3

For level 4, never overwrite: append every write and every deletion to the field's history. Timestamps only grow, so each history is already sorted by time and a binary search finds the version in force at any moment.
