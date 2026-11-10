# Memory Facts with Merge: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| versioned-facts | optimal | O(1) per remember or recall, O(log v) per recallAt, O(v) per history, O(f log f) per listFacts or merge, O(h log h) per exportFacts, O(l) per importFacts | O(w) | default answer; it survives all four levels without a rewrite |

Here `v` is the number of versions of one subject and attribute, `f` the number of subjects and attributes of one user, `h` the number of versions in all of one user's histories, `l` the number of imported lines, and `w` the number of facts the store has created.

## How the design grows level by level

| Level | Change | Structure after the level |
|-------|--------|---------------------------|
| 1 | `remember`, `recall`, `listFacts`, with ids from one counter | `users: user -> ((subject, attribute) -> current fact)`, and `lastNumber` |
| 2 | Keep every version, read at a moment | The current fact becomes a history of facts `(number, time, value)`, oldest first; a read binary-searches it |
| 3 | Merge two users by time, then priority | A map `user -> priority`; a merge reads the two current facts and appends a copy that keeps the original's time |
| 4 | Export every version, import with fresh ids | Nothing new is stored: an export walks the histories, and an import maps old ids to new ones before it writes |

Two choices made at level 1 decide whether level 4 is easy. The counter belongs to the store, not to a user, so an id names one fact wherever it is. And the id is a number with a letter in front, so you sort by the number and never by the text.

## Approach: versioned-facts (Per-fact version history with ids from one counter for the whole store)

### Intuition

A memory that can be merged and copied has to keep two things apart that a simple store mixes up: *which* fact this is, and *when* it was learned. The id answers the first question, and it is local: each store hands out its own. The time answers the second, and it travels with the fact. A merge or an import makes a new fact here, so it gets a new id, but it is still the same knowledge, so it keeps its time.

Once those two are apart, every level is a small step. History is a list of facts per subject and attribute, appended in time order. "As of" is a binary search on that list. A merge compares the times of two current facts, and only on a tie looks at priorities. An import is a dictionary from the old ids to the new ones, filled before any value is rewritten.

### Algorithm

1. Keep `users`, a map from user to a map from `(subject, attribute)` to that fact's history, and `lastNumber`, the last id number given out by the store.
2. A fact is `(number, time, value)`, and its id is `f` followed by the number.
3. `remember` adds the fact `(next number, timestamp, value)` to the end of its history and returns its id. `recall` reads the last fact of the history, and `listFacts` sorts the user's keys and formats the last fact of each.
4. `history` formats every fact of one history. `recallAt(at)` binary-searches the history for the last fact whose time is at most `at` (an upper bound, so the last of several equal times wins).
5. `setPriority` stores a number per user, 0 when missing. `merge` decides once whether `fromUser` wins ties (its priority is strictly higher). Then, for each of `fromUser`'s keys in sorted order, it takes the current fact when `intoUser` has no history for the key, or when the incoming time is later, or when the times are equal and `fromUser` wins ties. The decisions are made first, and each taken fact is then appended to `intoUser` as `(next number, original time, value)`.
6. `exportFacts` collects every fact of every history of the user, sorts them by number, and formats `id time subject attribute value`.
7. `importFacts` returns nothing when the user has facts. Otherwise it splits the lines, gives every old id the next number in line order, and only then appends each line's fact with its new number, its own time, and its value with a reference rewritten through the map of old ids to new ids.

### Correctness

Invariant: every history is sorted by time, oldest first. `remember` appends the call's timestamp, and timestamps never decrease, so it is at least every time already stored (copies and imports carry times from earlier calls or at most the import's timestamp). A merge appends a copy only when its time is at least the current fact's time, which is the largest in that history. An import writes into a user with no histories, and its lines of one key come in history order. So the upper-bound binary search finds the fact in force at any moment, and the last fact is the current one.

Ids are unique because only `nextNumber` creates them, and an import maps every old id to a number taken from it. The export of a user holds every fact that one of its values can refer to, since a reference names a fact of the same user and every fact stays in its history. During an import, every old id has its new id before the first value is rewritten, so a reference to any line of the import, earlier or later, resolves. A reference is replaced only when its whole id is a key of the map, so `@f1` never matches a part of `@f12`, and a plain value such as `f1` is no reference at all.

A merge decides from the state before it writes anything, so its own copies never take part in its comparisons, and a merge of a user into itself compares each fact with itself: equal times, equal priorities, nothing taken.

### Complexity

- Time: O(1) per remember or recall, O(log v) per recallAt, O(v) per history, O(f log f) per listFacts or merge, O(h log h) per exportFacts, O(l) per importFacts — appending and reading the last fact are constant time; `recallAt` is one binary search; `listFacts` and `merge` sort the user's keys; an export sorts all of the user's versions by number; an import makes two passes over its lines.
- Space: O(w) — every fact the store has created stays in some history.

### Trade-offs

- Sorting on every `listFacts`, `merge` and export keeps the writes O(1). A sorted map per user (a `TreeMap`, or a sorted list in Python) would make the reads cheaper and the writes O(log f); with a few hundred facts per user the sort is simpler and fast enough.
- An export could be kept in id order all along by appending each fact to a per-user list as it is created. That makes the export O(h), costs a second copy of every fact, and has to be kept right by every write. Sorting at export time has one place to be right.
- Keeping only the current fact (levels 1 and 3 alone) would need far less memory, but level 2 reads the past and level 4 exports it, because a reference can name a replaced fact.
- A two-number id (device and counter) would let stores share ids without remapping, which is how real sync systems avoid the problem. The statement fixes ids per store, and remapping is the price.

### Pitfalls and edge cases

- **Stamping a copy with the merge's time.** The copy looks newer than it is, so it beats a fact that was really remembered later (`h8`), and `recallAt` misses it before the merge.
- **Ids per user.** The counter is one for the whole store; two users never get the same id (`h1`).
- **Equal times.** Calls may share a timestamp: the later call wins in `recall` and in `recallAt` (`h3`, `h5`). An upper-bound search gets this for free; a lower bound returns the older fact or nothing.
- **Priority as more than a tie-breaker.** A higher priority never beats a later time (`h10`), and equal priorities leave `intoUser` its fact (`h7`, `ex4`).
- **Merging whole histories.** Only the current fact of each key travels (`h10`), and `fromUser` stays as it was (`ex3`).
- **Copy ids in map order.** Sort the keys before you give out ids (`h9`).
- **Merging a user into itself** takes nothing; deciding before writing makes this safe (`h9`).
- **Exporting only current facts.** A reference may name a replaced fact, and its history is lost (`ex5`).
- **Sorting ids as text.** `f10` sorts before `f9` as a string; sort by the number (`h12`).
- **Keeping the imported ids.** They collide with this store's facts (`h11`, `h14`), and the counter must move past the new ids too (`ex5`, `h13`).
- **Rewriting references with a text search.** Replacing `@f1` inside `@f12` gives `@f32`; look up whole values. A forward reference needs the first pass (`h11`).
- **Rewriting values that only look like ids.** `f7` without `@` is plain text (`h13`).
- **Remapping in a merge.** Within one store, a copied reference already names the right fact (`h15`).
- **Importing into a user with facts.** Nothing changes and no ids are used (`h13`).

### Language notes

- Python: `bisect_right(facts, moment, key=lambda fact: fact.time)` (3.10 and later) is the upper-bound search. Tuple keys `(subject, attribute)` sort the way the statement orders facts, and `sorted(dict)` sorts them without a custom comparator.
- TypeScript: a `Map` cannot key on a pair, so the reference joins subject and attribute with a space, which neither may contain, and keeps both inside the history for sorting. Sort strings with `<` and `>`: `localeCompare` would order them by locale, not by code point. Sort ids by their number (`a.number - b.number`), since `sort()` with no comparator compares text.
