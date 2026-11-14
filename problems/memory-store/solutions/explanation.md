# Memory Store: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| ordered-user-maps | optimal | O(1) per read, update or rollback; O(m) per add or quota change; O(m q + m log m) per search | O(t) | default answer; it survives all four levels without a rewrite |

Here `m` is the number of memories the user holds, `q` the number of words in the query, and `t` the total length of every version of every stored text.

## How the design grows level by level

| Level | Change | Structure after the level |
|-------|--------|---------------------------|
| 1 | Add, read, update and remove one memory | `users: userId -> (memoryId -> Memory(text))` |
| 2 | Rank a user's memories against a query | `Memory` gains `words` (a set, rebuilt when the text changes) and `writtenAt` |
| 3 | Memories expire | `Memory` gains `expiresAt`; one helper, `live(t)`, returns a memory only while it exists at `t` |
| 4 | Versions, rollback and a per-user quota | `Memory.text` becomes a list of versions; each user's map is kept in order of use; `quotas: userId -> limit` |

Two early choices make the later levels cheap. First, every method reaches a memory through the same helper, so the expiry check of level 3 is written once and the quota of level 4 never meets an expired memory by accident. Second, the user's map itself records the order of use: moving a memory to the end of an insertion-ordered map on every use makes the least recently used memory the first entry, with no clock comparisons and no separate list to keep in sync.

## Approach: ordered-user-maps (Per-user maps kept in order of use)

### Intuition

Everything the problem asks about is scoped to one user, so a map per user is the natural shape. Inside it, a memory is a small record: its versions, its word set, when it was last written and when it expires. The two orders the problem needs are different, and keeping them apart is the key: search breaks ties by when a memory was last written, which is a field of the memory, while eviction picks the least recently used memory, which is the position of the memory in its user's map.

### Algorithm

1. Keep `users`, a map from user id to an insertion-ordered map from memory id to `Memory`, and `quotas`, a map from user id to its limit.
2. A `Memory` holds `versions` (the last is current), `words` (the set of words of the current text), `writtenAt` and `expiresAt` (none for a memory that never expires). It is live at `t` when it never expires or `t < expiresAt`.
3. `live(t, user, id)` returns the memory when it exists and is live at `t`. When it exists but has expired, it deletes it for good, which is safe because time never goes back. `use(t, user, id)` calls `live` and moves the memory to the end of its user's map.
4. Level 1: `add` returns `false` when `live` finds the id; otherwise it inserts a new memory at the end. `get` and `update` go through `use`; `update` appends a version, rebuilds `words` and sets `writtenAt`. `remove` deletes what `live` finds.
5. Level 2: `search` turns the query into a set of terms, scores each live memory of the user by the size of the intersection with its `words`, keeps scores of at least 1, sorts by `(-score, -writtenAt, id)` and returns the first `k` ids. It does not move anything in the map.
6. Level 3: `addWithTtl` is `add` with `expiresAt = timestamp + ttl`. Every other method already goes through `live` or checks liveness in its loop.
7. Level 4: `history` copies the versions of the live memory. `rollback` checks `1 <= version < len(versions)`, moves the memory to the end and writes `versions[version - 1]` as a new version. `setQuota` stores the limit and evicts down to it. `add` and `addWithTtl`, under a quota, evict down to `limit - 1` before inserting. Evicting first deletes the user's expired memories, then pops the first entries of the map until the size fits.

### Correctness

Invariant: each user's map holds the user's memories ordered by their last use, least recent first. Insertion puts a new memory at the end, every successful `get`, `update` and `rollback` moves its memory to the end, and nothing else reorders the map; calls are processed in call order, so two uses at the same timestamp keep their call order, as the statement requires. Deleting expired memories before counting means the map's size is the number of memories that count toward the quota, and popping the first entry evicts exactly the least recently used one. Search reads `writtenAt`, which only writes change, so a `get` never alters a ranking. An expired memory is invisible everywhere because every method either goes through `live` or tests `isLiveAt` itself, and since timestamps never decrease, an expired memory can never become live again, so deleting it is the same as hiding it.

### Complexity

- Time: O(1) per read, update or rollback; O(m) per add or quota change; O(m q + m log m) per search — map lookups and moves to the end are O(1) on average, splitting a text is bounded by the 20-word limit, eviction sweeps the user's memories once for expired ones, and search intersects one set per memory before sorting the matches.
- Space: O(t) — every version of every text stays until its memory is removed, expires or is evicted.

### Trade-offs

- A doubly linked list beside a plain map is the textbook least-recently-used structure; an insertion-ordered map (`OrderedDict` in Python, `Map` in TypeScript) is the same thing built in, and saves the bookkeeping of keeping two structures in step.
- Recording a "last used" timestamp and searching for the minimum would be O(m) per eviction and gets ties wrong: two uses at the same timestamp must keep their call order. A counter that grows on every call fixes the ties but still pays O(m).
- Sweeping expired memories on each add under a quota costs O(m). A min-heap of expiry times per user makes the sweep O(log m) per expired memory; with at most 1000 calls it only adds code, but it is the answer to "what if users hold a million memories".
- An inverted index from word to memory ids would make search touch only the memories that share a word with the query, at the cost of updating it on every write, rollback, expiry and eviction. Mention it as the scaling step.

### Pitfalls and edge cases

- Level 1: `add` on an existing id must fail without touching the text, and `update` on a missing id must not create the memory. `remove` frees the id, so the next `add` succeeds.
- Level 2: score whole words, not substrings (`cat` against `category`), and count each distinct query word once, however often it appears in the query or the text. Break equal scores by the last write time, newest first, then by id in string order (`m10` before `m9`). Slice to `k` after sorting, never before.
- Level 3: the expiry is exclusive: a memory written at 10 with `ttl` 1 is visible at 10 and gone at 11. `update` must keep the expiry, and `search` must check liveness itself, because nothing may have read the memory since it expired.
- Level 4: `rollback` to the current version, to version 0 or past the end fails; a successful rollback is a write, so it makes the memory newer for search. Expired memories must not count toward a quota: deleting them before evicting stops an add from evicting a live memory to make room that already exists. `search` and `history` are not uses, so they must not reorder the map, and two uses at the same timestamp keep their call order. Eviction removes the history too.

### Language notes

- Python: `OrderedDict.move_to_end(id)` marks a use and `popitem(last=False)` pops the least recently used memory, both O(1). A plain `dict` keeps insertion order too, but moving a key to the end needs a delete and a re-insert. Sorting tuples `(-score, -writtenAt, id)` gives all three tie-breaks in one key.
- TypeScript: a `Map` iterates in insertion order, so `delete` followed by `set` moves a memory to the end, and the first key of `keys()` is the least recently used. Deleting entries of a `Map` while iterating it is safe. The comparator chains the three keys with `||` and compares ids with `<` and `>`, which match the other language for ASCII; `localeCompare` would not.
