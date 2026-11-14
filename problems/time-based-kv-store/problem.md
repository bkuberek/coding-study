# Time-Based Key-Value Store

## Statement

Design a store that remembers every version of every key. Each write records a value for a key at a moment in time, and a read asks what the key held at a given moment: the value of the latest write for that key made at or before that moment.

Implement the class `TimeMap`:

- `TimeMap()` creates an empty store.
- `set(key, value, timestamp)` records that `key` took the value `value` at time `timestamp`. Earlier versions of the key are kept.
- `get(key, timestamp)` returns the value of the write to `key` with the largest timestamp that is less than or equal to `timestamp`. If `key` has no write at or before `timestamp` (or no write at all), it returns the empty string `""`.

Writes arrive in time order: every `set` call uses a strictly larger timestamp than all `set` calls before it, across all keys. Reads may ask about any moment, including moments before the first write or after the last one.

Reference: this is our own wording of LeetCode problem 981, [Time Based Key-Value Store](https://leetcode.com/problems/time-based-key-value-store/).

## Input

- Constructor: no arguments.
- `set(key, value, timestamp)`: the key, its new value, and the time of the write.
- `get(key, timestamp)`: the key and the moment to look up.

Each test is a sequence of calls: the constructor first, then `set` and `get` calls in order.

## Output

- `get` returns the value that was current for `key` at `timestamp`, or `""` when there is none.
- `set` returns nothing.

The expected output lists one result per call, with `null` for the constructor and for every `set`.

## Examples

### Example 1

<!-- case: ex1 -->

`mood` is `calm` from time 2 on. A read at time 5 still sees `calm`, because nothing was written between 2 and 5. After `busy` is written at time 6, a read at time 5 still answers `calm` (it asks about the past), while a read at time 9 answers `busy`.

### Example 2

<!-- case: ex2 -->

A read at time 9 comes before the only write to `door` (time 10), so it gets `""`. `window` has never been written when it is first read, so it also gets `""`. The last read sees `open`, written at time 10 and still current at time 12.

## Constraints

- `1 <= key.length, value.length <= 20`
- `key` and `value` consist of lowercase English letters and digits.
- `1 <= timestamp <= 10^7`
- The timestamps of `set` calls are strictly increasing.
- At most `10^5` calls to `set` and `get` in total.

## Follow-ups

- What changes if writes may arrive out of time order?
- How would you also support deleting a key as of a given time?
- How much memory does the store use, and how could old versions be compacted?

## Hints

### Hint 1

Keep a separate history per key. In what order do the entries of one key's history arrive?

### Hint 2

Because writes come in time order, each history is already sorted by timestamp, so you never need to sort it.

### Hint 3

A read is a search in a sorted list for the last timestamp that is not greater than the query: one binary search per `get`.
