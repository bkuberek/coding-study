# Content-Addressed Store: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| store-and-walk | optimal | O(b) per object put or read; diff opens only changed folders; O(n) per chunked file; O(live bytes + objects) per collection | O(stored bytes) | default answer; one map of objects carries all four levels |

Here `b` is the size of the object put or read, `n` the size of the file being chunked, and "live" means what the refs reach. Hashing costs time in proportion to the bytes hashed, and every read hashes the object it reads once.

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | Put and get by address | a map from address to bytes; every read hashes the bytes again |
| 2 | Folder snapshots | nothing new: a folder is an object whose text lists its entries by address |
| 3 | Chunking | per method, the total size of the files put and a map from chunk address to size, for the ratio; manifests are objects |
| 4 | Refs and garbage collection | a map from ref name to kind and address; the collector walks from the refs and deletes the rest |

The choice that carries the later levels is level 1's: one map, keyed by digest, with a read that checks. Folders, manifests and refs never get a store of their own. They are objects, or names for objects, so dedup, checking and freeing work on them for free.

## Approach: store-and-walk (Object map with tree walks and a mark-and-sweep collector)

### Intuition

When the key of a value is the digest of the value, three problems solve themselves. Equal data has one key, so it is stored once. A read can be checked by hashing what was read and comparing it with the key that was asked for. And a structure that refers to its parts by key has a key that changes exactly when some part changes: a folder that lists its files by address has an address that stands for everything under it, so two folders with the same address are equal without looking inside. The diff, the chunk sharing and the collector are all walks over such references.

### Algorithm

1. Keep `objects`, a map from address to bytes. `put` encodes the text as UTF-8, hashes it, and stores it unless the address already holds bytes that still hash to it, which also repairs a damaged object. `get` and `check` hash the stored bytes again and compare with the address. `damage` replaces the bytes and keeps the key. `count` and `bytesStored` read the map.
2. `snapshot` splits each path at `/` and groups the files by their first name: a name with nothing after it is a file of this folder, and the rest form a subfolder, built first, the same way. A folder's text is one line `kind address name` per entry, sorted by name and ended by line feeds, and it is put like any data.
3. `readPath` starts at the root and, for each name, opens the current folder (a checked read), finds the name and moves to its entry; it answers `""` for a damaged folder, a missing name, a file in the middle or a folder at the end.
4. `diff` compares two folder addresses. Equal addresses end the comparison. Otherwise it opens both folders and, for each name in either, skips an equal entry, reports `M` for two files, compares two folders one level down, and lists every file under a one-sided entry as `A` or `D`. A damaged folder anywhere it must open turns the whole answer into `[]`. The changes are sorted by path at the end.
5. `"fixed"` cuts every 64 bytes. `"cdc"` walks the data once, keeping the window hash of the last 16 bytes: before adding a byte, once the window is full, it subtracts the leaving byte times `257^15 mod M` and adds `M` back when the result is negative, then multiplies by 257 and adds the new byte. It cuts after the byte when the chunk reaches 256 bytes, or holds at least 32 and the hash is a multiple of 64.
6. `putFile` puts each chunk, records its size under its address for the method, adds the file's size to the method's total, and puts the manifest, one address and a line feed per chunk. `readFile` reads the manifest and each chunk with checks. `dedupRatio` divides the method's total by the sum of its recorded chunk sizes.
7. `collectGarbage` marks from every ref with a stack of (kind, address) pairs and a visited set of pairs. A popped tree is opened and its lines pushed; a manifest is opened and its chunks pushed as blobs; a blob is only marked. Failing to open a tree or a manifest aborts with `-1` before anything is deleted. Then every unmarked object is deleted and its bytes added up.

### Correctness

Addresses: SHA-256 is deterministic, so equal bytes give equal addresses, and different bytes give different addresses unless the hash collides, which is what a cryptographic hash is chosen to make practically impossible. Dedup and the check on read follow: a stored object is intact exactly when its bytes hash to its key.

Canonical folders: the text of a folder is a function of its entries alone, since the lines are sorted by name and their format is fixed, and each entry's address is, by induction from the files up, a function of what is under it. So the root address depends on the set of paths and data and on nothing else, not the order of `files`, and two folders are equal exactly when their addresses are. That is why `diff` may skip equal addresses: by induction over the depth, comparing two folders reports exactly the paths under them whose files differ, and an equal pair contributes nothing. Sorting at the end makes the order independent of the walk.

Chunking: the window hash at a position is a function of the 16 bytes that end there. The rolled value equals the hash computed from scratch, because subtracting `out · 257^15` removes exactly the oldest byte's term and multiplying by 257 shifts the others before the new byte is added, all modulo `M`. Since a cut needs at least 32 bytes in the chunk, the window lies inside it, so a cut depends only on the bytes around it and on the distance from the previous cut. After an insertion, a position whose window lies past the inserted bytes matches exactly when it matched before, so the cuts soon fall on the same bytes again, and once one cut coincides, every later chunk is the same, since the cuts from there depend only on the bytes that follow.

Collection: the mark visits a pair once and pushes everything the object reaches, so on success the marked set is exactly the set of objects reachable from the refs, through any number of folders, and a shared object is marked once whichever way it is reached. Keying the visited set by kind as well as address matters when one object is reached as a blob and as a tree: it is opened as a tree. Deleting only unmarked objects never frees a reachable one. When a tree or a manifest cannot be opened, the mark cannot know what it reached, so stopping before the sweep is the only safe answer.

### Complexity

- Time: O(b) per object put or read; diff opens only changed folders; O(n) per chunked file; O(live bytes + objects) per collection — a put or a read hashes the object once; `diff` opens the folders on the paths of the changes, and the folders under added or deleted entries, never a folder whose address is unchanged; chunking rolls the hash in O(1) per byte; the collector opens each live tree and manifest once and looks at every stored object once in the sweep.
- Space: O(stored bytes) — the objects themselves, plus a size per chunk for the ratio and a set of live addresses during a collection.

### Trade-offs

- Checking on every read costs one hash of the data read, the same order as reading it. Skipping it would make reads faster and damage silent. A real store also checks in the background, so damage to objects nobody reads is found too.
- A folder's text is readable, with addresses in hexadecimal. Raw 32-byte digests would halve its size, but the text could then not be returned by `get` as text, and it would be harder to debug.
- Keeping the whole store in memory and walking all live objects keeps the collector simple. Real collectors keep the marks of folders that did not change, or count references, at the price of more state to keep right.
- Content-defined chunking costs a hash update per byte and gives chunks of varied size. Fixed-size chunking is cheaper and gives chunks of one size, and is the better choice for data that changes in place without shifting, such as disk images.

### Pitfalls and edge cases

- Level 1, bytes. The address and the size are of the UTF-8 bytes: hashing a language's internal string form, or counting characters, breaks on `é`, `😀` and text in other scripts. Text is used as given: `é` written as one character and as `e` and a combining accent are two objects (`h2`).
- Level 1, trusting the disk. `get` and `check` must hash the stored bytes on every call; a flag set at `put` time cannot see `damage`. Dedup must check too: a store that sees the address taken and does nothing leaves a damaged object damaged forever, where putting the data again should repair it (`h5`). Damage keeps the old address; the damaged bytes are not filed under a new one (`h4`, `h8`).
- Level 2, the exact text. Lines sorted by name with character codes, single spaces, a line feed after every line, the last included. Sorting without case, folders first, or as if a folder's name ended with `/`, gives other addresses (`h9`, `h18`). A flat list of full paths is another encoding and shares nothing between snapshots (`h12`).
- Level 2, what to open. `readPath` opens only the folders on its path, so damage elsewhere does not matter (`h14`). `diff` never opens a pair of folders with the same address, so damage inside a shared folder changes nothing (`h15`), and it checks every folder it does open (`h16`). An added or deleted folder is listed file by file, and a name that is a file on one side and a folder on the other is a delete and adds (`h17`).
- Level 3, the rolling hash. The `%` of C, Java, Go, Rust and JavaScript keeps the sign of a negative value, so `(h - out · P) % M` can be negative; add `M`. The product `h · 257` reaches about `2.6 · 10^11`, beyond 32 bits. The leaving byte weighs `257^15`, not `257^16`. A hash that never removes the leaving byte is a hash of the whole chunk so far, which cannot resynchronize after an edit (`h21`, `h24`, `h29`).
- Level 3, the sizes. A chunk is at least 32 bytes unless it is the last, and at most 256; a run of one repeated byte, whose window never matches, is cut at 256 (`h22`). Empty data has no chunks, not one chunk of size 0 (`h20`, `h23`).
- Level 3, the ratio. Every call's bytes count, but each distinct chunk once, per method; integer division and counting a repeated chunk each time it appears both give the wrong ratio (`h27`).
- Level 4, the mark. It must follow folders all the way down and manifests to their chunks; a blob ref keeps only its own object, even when its bytes read like a folder (`h32`, `h33`, `h34`). Objects shared by several refs stay until none reaches them, so deleting a ref must not free what it reached at once (`h35`).
- Level 4, damage. A damaged tree or manifest that the mark must open stops the whole collection with nothing deleted; damaged garbage and a damaged file that is only marked do not (`h36`).

### Language notes

- Python: `hashlib.sha256(data).hexdigest()` gives the address; `str.encode("utf-8")` the bytes. `%` already returns a value in `0 .. M - 1` for a positive `M`, and integers do not overflow, so the rolling hash needs no care beyond the formula.
- TypeScript: `createHash("sha256").update(buffer).digest("hex")` from `node:crypto`; `Buffer.from(text, "utf8")` gives the bytes, whose `length` is the byte count. Numbers are exact integers up to `2^53`, and every product here stays below `2.6 · 10^11`, so plain numbers work, with `M` added before `%` since `%` keeps the sign. The default `sort()` compares UTF-16 code units, which is the character code order for ASCII names.
- Java: `MessageDigest.getInstance("SHA-256")` and `HexFormat.of().formatHex` (Java 17). Bytes are signed, so `Byte.toUnsignedLong` reads a byte as 0 to 255, and `Math.floorMod` gives the non-negative remainder. `long` holds every product. A `TreeMap` keeps a folder's entries sorted by `String.compareTo`, which compares UTF-16 code units.
- Kotlin: the same JVM classes; `byte.toLong() and 0xff` for an unsigned byte, and `mod` (not `%`) for the non-negative remainder. `toSortedMap()` sorts by `String` order.
- Go: `crypto/sha256` and `encoding/hex`. A Go string indexes and measures bytes, so `len(data)` is already the byte count. Map iteration order is random, so the names of a folder are sorted with `sort.Strings` before the text is written, and the changes of a diff are sorted at the end. `int64` holds the products, and `%` keeps the sign.
- Rust: the standard library has no SHA-256, so the starter ends with `sha256` and `sha256_hex`, written from FIPS 180-4 and tested against its examples; the reference carries the same helper. A `BTreeMap` keeps a folder's entries sorted by byte order, and `rem_euclid` gives the non-negative remainder of an `i64`.
