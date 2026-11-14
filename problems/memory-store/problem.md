# Memory Store

## Statement

Build `MemoryStore`, the service that keeps short memories for an assistant: facts and notes it should remember about each user, such as `prefers metric units`. Every memory belongs to one user and has an id chosen by the caller. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

Every method takes the current time as its first argument, `timestamp`. Nothing reads a clock: time is whatever the caller passes.

Aim to finish in 90 minutes. A good split: read the statement and pick the core data structure in the first 5 minutes, then finish level 1 by about minute 20, level 2 by 40, level 3 by 65 and level 4 by 88, keeping the last minutes for a final run.

## Input

- `MemoryStore()`: creates an empty store.
- `timestamp`: the time of the call. Within one test, timestamps never decrease from call to call, and consecutive calls may share a timestamp.
- `userId`: the user a call reads or writes. Users are independent: two users may use the same memory id for different memories.
- `memoryId`: a memory of that user.
- `text`: the content of a memory, lowercase words separated by single spaces.
- Each level's section describes the methods it adds and their other parameters.

## Output

Each method returns what its level describes. A missing memory is reported with a sentinel, never with an exception: `""` for strings, `false` for booleans and an empty list for lists.

## Level 1: Memories per user

- `add(timestamp, userId, memoryId, text)`: stores a new memory. Returns `false` and changes nothing when the user already has a memory with that id.
- `get(timestamp, userId, memoryId)`: the text of the memory, or `""` when it does not exist.
- `update(timestamp, userId, memoryId, text)`: replaces the text of the memory. Returns `false` and changes nothing when it does not exist.
- `remove(timestamp, userId, memoryId)`: deletes the memory. Returns `true` when it existed, `false` otherwise. The id is free again afterwards.

### Example 1

<!-- case: ex1 -->

The second `add` of `m1` fails because `u1` already has it, so `get` still reads the first text. `u2` has no memories, even though `u1` has an `m1`. Once `m2` is removed, removing or updating it again fails.

## Level 2: Keyword search

- `search(timestamp, userId, query, k)`: the ids of the user's best `k` memories for `query`, best first. `query` is one or more lowercase words separated by single spaces, and `k` is from 1 to 100.
- The score of a memory is the number of distinct query words that are also words of its text. A word matches only a whole word: `cat` does not match `category`. Repeating a word, in the query or in the text, does not raise the score.
- Only memories with a score of at least 1 are results. Order them by score, highest first; equal scores put the memory written more recently first (the last `add` or `update` decides when it was written); memories written at the same timestamp go in ascending string order of id. Return all of them when fewer than `k` match.

### Example 1

<!-- case: ex2 -->

For `green tea morning`, `m1` matches all three words, `m4` two and `m2` one; `m3` matches none and `m5` belongs to another user. For `coffee`, `m2` and `m4` both score 1, and `m4` was written later. `peanut` is not the word `peanuts`, so it finds nothing.

## Level 3: Expiring memories

- `addWithTtl(timestamp, userId, memoryId, text, ttl)`: like `add`, but the memory lives only for `ttl` time units, from 1 to 10^9. It exists at every time `t` with `timestamp <= t < timestamp + ttl` and is gone from `timestamp + ttl` on.
- An expired memory behaves exactly like one that was never stored, in every method: `get` returns `""`, `update` and `remove` return `false`, `search` leaves it out, and `add` or `addWithTtl` may use its id again.
- `update` changes the text and keeps the expiry. A memory stored with `add` never expires.
- Keep the expiry check in one helper that every method calls, so no method can forget it.

### Example 1

<!-- case: ex3 -->

`m2` is written at 2 with a lifetime of 5, so it exists up to time 6 and is gone at 7: it leaves the search results, `update` fails, and its id can be added again at 9.

## Level 4: History and quotas

- Every memory keeps its versions: `add` or `addWithTtl` writes version 1, and every successful `update` or `rollback` writes the next one.
- `history(timestamp, userId, memoryId)`: the texts of all versions of the memory, oldest first, or an empty list when it does not exist.
- `rollback(timestamp, userId, memoryId, version)`: writes the text of an earlier version as a new version, which becomes the current one; the expiry does not change. `version` counts from 1 and must be lower than the current version's number. Returns `false` and changes nothing when the memory does not exist or `version` is out of that range. For `search`, a rollback writes the memory like an `update` does.
- `setQuota(timestamp, userId, limit)`: from now on, the user keeps at most `limit` memories, from 1 to 1000; there is no limit before the first call. Expired memories never count. When the user already has more than `limit`, it evicts the least recently used ones until `limit` remain, and returns their ids in eviction order (an empty list when nothing was evicted).
- While a quota is set, an `add` or `addWithTtl` that would take the user over the limit first evicts the user's least recently used memory. A call that fails evicts nothing.
- A memory is used when it is added, read with `get`, updated or rolled back. `search`, `history` and failed calls do not count as uses. Uses at the same timestamp are ordered by call order: the later call is the more recent use.
- An evicted memory is removed, history included: adding its id again starts a new memory at version 1.

### Example 1

<!-- case: ex4 -->

After two updates, `m1` has three versions. The rollback to version 1 writes `likes tea` again as version 4. Version 4 is now the current one, so rolling back to it fails. `m9` does not exist, so it has no history.

### Example 2

<!-- case: ex5 -->

The quota of 2 evicts `m1`, the least recently used of three memories. Reading `m2` at 5 makes `m3` the least recently used, so adding `m4` evicts `m3`.

## Constraints

- At most 1000 calls per test.
- `1 <= timestamp <= 10^9`, never decreasing within a test.
- Ids are 1 to 10 lowercase letters or digits.
- A text is 1 to 20 words, and a word is 1 to 10 lowercase letters.

## Follow-ups

- How would `search` stay fast with a million memories per user?
- How would you expire memories when nobody reads them, so they stop taking memory?

## Hints

### Hint 1

A map from user to a map from memory id to memory covers level 1. Store each memory's words as a set when its text changes, so a search only intersects sets.

### Hint 2

Store the expiry next to each memory, and route every read and write through one helper that returns the memory only while it is live.

### Hint 3

Keep each user's memories in order of use: an insertion-ordered map moves a memory to the end when it is used, so the least recently used one is always first.
