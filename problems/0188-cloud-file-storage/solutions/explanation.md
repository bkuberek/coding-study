# Cloud File Storage: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| owned-files | optimal | O(1) per file operation; O(m log m) per listing, quota change, backup or restore | O(n + b) | default answer; the file map stays the single source of truth |

Here `n` is the number of stored files, `m` the number of files a listing or a user operation looks at, and `b` the number of files kept in backups.

## How the design grows level by level

| Level | New requirement | What the design adds |
|-------|-----------------|----------------------|
| 1 | Add, size and delete files by name | `files: name -> File(name, size)` |
| 2 | Largest files under a prefix | Nothing stored: filter by prefix, sort by `(-size, name)`, cut at `limit` |
| 3 | Users with capacities | `owner` on each file; `User(capacity, used, names)`; every add and delete goes through `store` and `discard`, which keep `used` and `names` in step |
| 4 | Backups and restores | `backups: user -> list of (name, size)`; a restore is a `discard` of every owned file followed by `store` of each saved file that still fits |

The move that makes level 3 and level 4 easy is funneling every mutation through two private methods. Once `store` and `discard` are the only code that touches `files`, the per-user counters cannot drift, and later levels (shrinking quotas, restores) are short loops over those two calls.

## Approach: owned-files (File map with per-user ownership)

### Intuition

Names are global, so one map from name to file decides every "is this name taken" question, for owned and unowned files alike. Quotas are per user, so each user keeps a running total and the set of names they own; a file records its owner so that deleting it by name knows whose total to reduce. Every ordering the problem asks for is the same one, size descending and then name, so one comparator serves listings and quota shrinking alike.

### Algorithm

1. `store(file)`: put it in `files`; when it has an owner, add its size to the owner's `used` and its name to the owner's set. `discard(file)` does the reverse.
2. Level 1: `addFile` rejects a taken name and stores an unowned file. `getFileSize` reads the map. `deleteFile` discards the file and returns its size.
3. Level 2: `listLargest` filters the files by prefix, sorts them by `(-size, name)` and formats the first `limit`.
4. Level 3: `addUser` creates a user with `used = 0`. `addFileBy` checks that the user exists, the name is free and `used + size <= capacity`, then stores the file and returns `capacity - used`. `updateCapacity` sets the capacity, then walks the user's files in `(-size, name)` order, discarding until `used <= capacity`, and returns how many it discarded.
5. Level 4: `backupUser` copies the user's current files into `backups[user]`. `restoreUser` discards every file the user owns, then visits the saved files in name order and stores each one whose name is free and that fits.

### Correctness

Invariant: for every user, `used` is the total size and `names` the set of names of the files in `files` whose owner is that user. It holds initially, and `store` and `discard` are the only operations that change `files`, each updating the owner by exactly the file's size and name. Every capacity check therefore compares against the true usage.

`updateCapacity` removes files in the required order and stops as soon as the remainder fits, so it removes the fewest files that order allows. In `restoreUser`, the user owns nothing after the first loop, so a saved name can only be taken by someone else; the name check plus the capacity check, applied in name order, is exactly the rule in the statement. A backup is a copy, so later changes to the user's files cannot alter it.

### Complexity

- Time: O(1) per file operation; O(m log m) per listing, quota change, backup or restore — map operations are O(1) on average; listings sort the `m` matching files, and user operations sort or copy the user's `m` files.
- Space: O(n + b) — one entry per stored file plus one per file kept in a backup.

### Trade-offs

- Sorting on every `listLargest` is simple and fast for a few thousand files. A sorted structure keyed by `(-size, name)` per prefix is impossible in general (prefixes are arbitrary); a trie of names with a size-ordered set at each node answers short prefixes faster but multiplies memory and write cost by the name length.
- Scanning every file for a prefix is O(n). A `TreeMap` or sorted list of names finds the prefix range in O(log n + matches), then the matches still need sorting by size. Worth it only when prefixes are selective.
- Copying the user's file list at backup time costs O(m) memory per backup. Copy-on-write sharing would avoid the copy when files rarely change, at the price of a more subtle model.

### Pitfalls and edge cases

- Names are shared: a user file and an unowned file can never have the same name, in either direction.
- `deleteFile` must reduce the owner's usage, or the user slowly loses capacity.
- The fit check is `used + size <= capacity`; a file that exactly fills the quota is allowed.
- Raising a capacity removes nothing and returns 0; capacity 0 removes every file of the user.
- Restore deletes the current files first, even when the backup is empty or missing.
- Restore order matters when the quota shrank after the backup: in name order, a large early file can crowd out later ones.
- Sizes exceed 32 bits: use `long` in Java and Kotlin.

### Language notes

- Python: a frozen dataclass for files and a mutable one for users; `sorted(..., key=lambda f: (-f.size, f.name))` builds the ordering from a tuple key.
- TypeScript: `b.size - a.size || compareNames(a.name, b.name)` chains the two keys, because `0` is falsy; sizes up to `10^10` are exact in `number`.
- Java: a nested `record StoredFile` with a nullable `owner`, and `Comparator.comparingLong(StoredFile::size).reversed().thenComparing(StoredFile::name)`. `reversed()` applies to everything before it, which is why it sits before `thenComparing`.
- Kotlin: `compareByDescending<StoredFile> { it.size }.thenBy { it.name }` reads like the rule. `file.owner?.let(users::getValue) ?: return` skips unowned files in one line.
