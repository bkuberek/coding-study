# Cloud File Storage

## Statement

Build `CloudStorage`, a flat store of files. A file has a unique name, such as `/docs/report.pdf`, and a size in bytes; the slashes are part of the name, not real directories. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

Every method takes the current time as its first argument, `timestamp`. No rule depends on it, but it keeps the API uniform with the other practical problems.

## Input

- `CloudStorage()`: creates an empty store.
- `timestamp`: the time of the call. Within one test, timestamps strictly increase from call to call.
- `name`: a file name; names are case-sensitive.
- `size`, `capacity`: sizes in bytes.
- Each level's section describes the methods it adds and their other parameters.

## Output

Each method returns what its level describes. Failure is reported with a sentinel, never with an exception: `-1` for numbers and `false` for booleans.

## Level 1: Files

- `addFile(timestamp, name, size)`: stores a file. Returns `false` and changes nothing when a file with that name already exists.
- `getFileSize(timestamp, name)`: the size of the file, or `-1` when it does not exist.
- `deleteFile(timestamp, name)`: removes the file and returns its size, or `-1` when it does not exist.

### Example 1

<!-- case: ex1 -->

The second `addFile` of `/notes.txt` fails because the name is taken. Deleting it returns its size, 100; afterwards it is gone, so both a second delete and a size lookup return `-1`.

## Level 2: Largest files by prefix

- `listLargest(timestamp, prefix, limit)`: the files whose name starts with `prefix`, as strings `"<name>(<size>)"`, largest first; files of equal size go in ascending name order. At most `limit` entries. The empty prefix matches every file.

### Example 1

<!-- case: ex2 -->

Under `/docs/`, `c.pdf` is the largest; `a.pdf` and `b.pdf` tie at 300 and `a.pdf` comes first by name, so the limit of 2 cuts `b.pdf`. Nothing starts with `/video/`.

## Level 3: Users and quotas

- `addUser(timestamp, userId, capacity)`: creates a user who may own files with a total size of at most `capacity`. Returns `false` when the user already exists.
- `addFileBy(timestamp, userId, name, size)`: like `addFile`, but the file belongs to the user and counts toward their capacity. Returns the user's remaining capacity after adding it. Returns `-1` and changes nothing when the user does not exist, the name is taken (by anyone), or the file does not fit in the remaining capacity.
- `updateCapacity(timestamp, userId, capacity)`: sets a new capacity. When the user's files no longer fit, removes them one by one, largest first (equal sizes in ascending name order), until they fit. Returns the number of files removed, or `-1` when the user does not exist.
- Files added with `addFile` belong to nobody and have no limit. All files share one namespace, and `deleteFile` frees the owner's capacity.

### Example 1

<!-- case: ex3 -->

`ana` has 1000 bytes. After a 600-byte file 400 remain, so 500 bytes do not fit but 400 do, leaving 0. `bob` does not exist. Deleting the 600-byte file gives the space back, and a 100-byte file leaves 500.

## Level 4: Backup and restore

- `backupUser(timestamp, userId)`: saves a copy of the names and sizes of every file the user owns, replacing any earlier backup of that user. Returns the number of files saved, or `-1` when the user does not exist.
- `restoreUser(timestamp, userId)`: deletes every file the user owns now, then restores the files of the user's backup in ascending name order. A file is skipped when its name is used by another owner (or by an unowned file) or when it does not fit in the user's current capacity. Returns the number of files restored, or `-1` when the user does not exist. Without a backup, the user simply ends with no files and the result is 0.

### Example 1

<!-- case: ex4 -->

The backup holds `/k/a` and `/k/b`. Restoring removes `/k/b` and `/k/c` and brings back `/k/a` and `/k/b`, so 30 bytes remain free and a 31-byte file does not fit.

## Constraints

- At most 1000 calls per test.
- `1 <= timestamp <= 10^9`, strictly increasing within a test.
- `1 <= size <= 10^10` and `0 <= capacity <= 10^12`.
- `1 <= limit <= 1000`.
- Names are 1 to 30 characters from letters, digits, `/`, `.`, `-` and `_`; a prefix is 0 to 30 of them. User ids are 1 to 10 lowercase letters or digits.

## Follow-ups

- How would `listLargest` stay fast for millions of files and short prefixes?
- What changes if a backup must keep the file contents and several versions per user?

## Hints

### Hint 1

One map from name to file answers level 1. Sort by the pair (negated size, name) for every ordering this problem needs.

### Hint 2

Store the owner on each file and keep, per user, the used bytes and the set of names they own. Every add and every delete then updates exactly one user.

### Hint 3

A backup is just a list of `(name, size)` pairs. A restore is "delete mine, then add each saved file if it still fits and its name is free".
