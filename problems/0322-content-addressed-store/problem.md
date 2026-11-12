# Content-Addressed Store

## Statement

Build `ContentStore`, the storage engine under a backup tool or a version control system: a store that files every piece of data under its own fingerprint, so that the same data is never stored twice and damage is always noticed. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**Content addressing.** An ordinary store lets you choose a key for each value. A content-addressed store does not: the key of a value is computed from the value itself, and it is called the value's **address**. Here the address is the SHA-256 digest of the value's bytes. A hash function such as SHA-256 turns any data into a short fingerprint of fixed size, 32 bytes, written as 64 hexadecimal characters (`0-9` and `a-f`, in lowercase). The same data always gives the same digest, and a change to the data, even one character, gives a completely different one. In practice two different pieces of data never share a digest. You do not need to know how SHA-256 works inside: Python has `hashlib.sha256`, TypeScript `createHash("sha256")` from `node:crypto`, Java and Kotlin `MessageDigest.getInstance("SHA-256")` and Go `crypto/sha256`. Rust's standard library has none, so the Rust starter ends with two helpers that implement the standard: `sha256(data: &[u8]) -> [u8; 32]` and `sha256_hex(data: &[u8]) -> String`. Use them as they are.

**Why it is useful.** Three things come for free. Storing the same data twice costs nothing, because it lands at the same address (deduplication). Reading can be checked: hash the bytes you read and compare the digest with the address you asked for, and any damage shows. And two large structures can be compared in one step: when each part refers to its sub-parts by address, equal addresses mean equal parts, however large they are. The levels build exactly these three ideas, up to a garbage collector that frees what nothing uses any more.

The addresses must be exactly the ones the statement defines, character for character, in every language, so the statement fixes the bytes of everything that is stored. The expected values in the examples are real digests that you can check your code against.

Aim to finish in 120 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 25, level 2 by 55, level 3 by 85 and level 4 by 115, keeping the last minutes for a final run.

## Input

- `ContentStore()`: creates an empty store.
- Data is text, and its **bytes** are its UTF-8 bytes: `é` is 2 bytes and `😀` is 4. Text is used exactly as given, with no case folding and no Unicode normalization.
- An address is 64 lowercase hexadecimal characters. A method that takes an address may get any string; a string that is not the address of a stored object finds nothing.
- Each level's section describes the methods it adds and their parameters.

## Output

Every address the store returns is 64 lowercase hexadecimal characters. Methods that change the store return what their level says. Questions about something that is not there get the empty answer: `""` for text, `[]` for a list, and the value their level names for a number.

## Level 1: Put and get by address

The store holds **objects**: an object is a sequence of bytes, filed under its address, the SHA-256 digest of those bytes.

- `put(data)`: stores the bytes of `data` as an object and returns its address. When the address already holds an intact object, nothing changes: the same data is stored once, however often it is put. When it holds a damaged object (see `damage`), the damaged bytes are replaced by the bytes of `data`, which repairs it.
- `get(address)`: the data of the object at `address`, **checked on the way out**: hash the stored bytes, and return the data only when the digest equals `address`. The answer is `""` when nothing is stored at `address`, and also when the object is damaged, so that damaged data is never handed out.
- `check(address)`: `"missing"` when nothing is stored at `address`, `"damaged"` when the digest of the stored bytes differs from `address`, and `"ok"` otherwise.
- `damage(address, data)`: simulates damage on a disk. It replaces the bytes stored at `address` with the bytes of `data`, and leaves the object filed under its old address. It returns `false`, and changes nothing, when nothing is stored at `address`; otherwise `true`. Damage with the object's own data changes nothing.
- `count()`: the number of objects stored, damaged ones included.
- `bytesStored()`: the total number of bytes of the stored objects, as they are now.

A store that trusted its disk would return whatever bytes it finds. Checking on read is cheap, since one hash of the bytes you already have tells you whether they are still the bytes the address names. Everything that reads an object in the later levels checks it the same way.

### Example 1

<!-- case: ex1 -->

`hello` is put twice and lands at the same address both times, so the store holds two objects, `hello` and `world`, 10 bytes in all. The address of `hello` is the SHA-256 digest of its five bytes. The last two calls ask about an address that holds nothing.

### Example 2

<!-- case: ex2 -->

The object of `backup` is damaged into `backuq`. It is still filed under the address of `backup`, but its bytes no longer hash to that address, so `check` reports it and `get` refuses to return it. Putting `backup` again repairs it.

## Level 2: Folder snapshots

A **snapshot** stores a whole folder of files and returns one address that stands for all of it. It is built from **tree objects**, one per folder, which name their files and subfolders by address, so the address of the top folder depends on every file below it.

**Paths.** A file is given by a path: names joined by `/`, such as `src/lib/util.py`. Each name is 1 to 30 printable ASCII characters (codes 32 to 126) other than `/`, and is neither `.` nor `..`. The folders of a snapshot are the ones its paths pass through; there are no empty folders.

**The tree object of a folder.** The text of a folder has one line for each entry directly inside it, each line ended by a line feed (`\n`):

- a file `name` is the line `blob <address> <name>`, where the address is the address of the file's data;
- a subfolder `name` is the line `tree <address> <name>`, where the address is the address of the subfolder's tree object.

The fields are separated by single spaces, and the lines are sorted by name, comparing character codes, so `B` comes before `a`, `a` before `a-b` and `a-b` before `a.txt`. A folder's address is the address of its text. The text is the object: `get` of a folder's address returns it.

- `snapshot(files)`: `files` is a list of `[path, data]` pairs. It stores each file's data as an object, and each folder's text as an object, both as `put` does, and returns the address of the top folder, the **root**. The order of `files` does not matter. A snapshot of no files is the empty text, whose address is the address of the empty string.

Because a folder refers to its subfolders by address, a folder that did not change between two snapshots has the same text and the same address, and is stored once. A second snapshot that changes one file adds only that file's data and the folders on its path.

- `readPath(root, path)`: the data of the file at `path` in the snapshot `root`. Start at the root's tree object and follow the names of `path` one by one. Every object you open is checked as `get` checks it. The answer is `""` when an object on the way is missing or damaged, or when `path` does not name a file: a name that is not there, a name that is a folder at the end, or a file in the middle.
- `diff(oldRoot, newRoot)`: the files that differ from the snapshot `oldRoot` to the snapshot `newRoot`, one string per file: `"A <path>"` for a file that is only in the new snapshot, `"D <path>"` for one that is only in the old one, and `"M <path>"` for one in both with other data. The list is sorted by path, comparing character codes.

**How `diff` compares.** Two folders with the same address are equal, and `diff` never opens them: `diff(root, root)` is `[]` at once. Otherwise it opens both tree objects and compares their entries by name:

- an entry in both with the same kind and the same address is unchanged;
- a file in both with different addresses is `M`;
- a folder in both with different addresses is compared the same way, one level down;
- an entry in only one of them gives `A` or `D` for the file, or for every file under the folder, which `diff` opens to list them;
- a name that is a file on one side and a folder on the other is a file deleted (or added) and the folder's files added (or deleted).

`diff` never opens a file: equal addresses mean equal data. It checks each tree object it opens as `get` does, and when one of them is missing or damaged, it answers `[]`. Damage inside a folder that is the same in both snapshots does not change the answer, since `diff` never opens it.

The roots given to `readPath` and `diff` are always addresses that `snapshot` returned, though the object may have been damaged since, or addresses where nothing is stored. The path given to `readPath` is names joined by `/`, each 1 to 30 printable ASCII characters other than `/`.

### Example 1

<!-- case: ex3 -->

Three files make five objects: three files and two folders. The root's text lists `README.md` and the folder `src` by address, sorted by name. `readPath` finds a file, and answers `""` for a folder and for a path that is not there.

### Example 2

<!-- case: ex4 -->

The second snapshot changes `README.md` and adds `docs/guide.md`, and keeps `src` as it was. It adds four objects: the new `README.md`, `guide.md`, the folder `docs` and a new root. The folder `src` keeps its address, so it is shared, and `diff` does not open it. In the other direction the guide is deleted.

## Level 3: Chunking

A large file that changes a little should not be stored again in full. The store cuts a file into **chunks**, stores each chunk as an object, and stores the list of their addresses, the **manifest**. Two versions of a file then share every chunk that did not change. How much they share depends on where the cuts are, and this level compares two ways of cutting.

The data of this level's methods is ASCII text: line feeds and printable characters (codes 32 to 126), one byte each.

**Fixed-size chunking**, the method `"fixed"`, cuts every 64 bytes from the start: chunks of 64 bytes, and a last chunk with the rest, 1 to 64 bytes. Empty data has no chunks. It is simple, but one byte inserted near the start shifts every later byte, so every later chunk changes.

**Content-defined chunking**, the method `"cdc"`, cuts where the content says, so a cut moves with the bytes around it, and an insertion changes only the chunks near it. It decides at each byte from a **rolling hash** of the 16 bytes that end there:

1. **The window hash.** For a window of 16 bytes `w[0]` (the oldest) to `w[15]` (the newest), `H = (w[0]·257^15 + w[1]·257^14 + … + w[14]·257 + w[15]) mod 1000000007`. Computed from scratch, that is `h = 0`, then for each byte `b` of the window in order, `h = (h·257 + b) mod 1000000007`.
2. **Rolling it.** You do not need to hash 16 bytes at every position. When the window moves one byte forward, dropping `out` and taking `in`, `H' = ((H − out·P)·257 + in) mod 1000000007`, where `P = 257^15 mod 1000000007`. Keep every value in `0 .. 1000000006`: `H − out·P` can be negative, and the `%` operator of most languages then gives a negative result, where this statement means the remainder from 0 to 1000000006. Products reach about 2.6·10^11, which does not fit a 32-bit integer.
3. **The cuts.** A chunk starts at position `s`. For each position `i = s, s + 1, …`, let `len = i − s + 1`, the length of the chunk if it ended at `i`. Cut after position `i` when `len` is 256, or when `len` is at least 32 and the window hash of the 16 bytes ending at `i` is a multiple of 64. The next chunk starts at `i + 1`. When the data ends first, the rest is the last chunk. Empty data has no chunks.

So a chunk holds 32 to 256 bytes, except the last, which may be shorter. A window of 16 bytes always fits inside a chunk of at least 32, so the hash only ever looks at the chunk's own bytes, and the same 16 bytes give the same hash wherever they are in the file.

- `chunkSizes(data, method)`: the sizes of the chunks that `method` cuts `data` into, in order. It stores nothing.
- `putFile(data, method)`: cuts `data` with `method`, stores each chunk as an object, as `put` does, and then stores the manifest: one line per chunk, in order, each the chunk's address followed by a line feed. It returns the address of the manifest. Empty data has the empty manifest.
- `readFile(manifest)`: the data of the file whose manifest is at `manifest`: the manifest, then each of its chunks in order, joined. Every object is checked as `get` checks it, and the answer is `""` when any of them is missing or damaged. The argument is always an address that `putFile` returned.
- `dedupRatio(method)`: how well `method` has deduplicated so far: the total size of the data of every `putFile` call with this method, each call counted, divided by the total size of the distinct chunks those calls produced, each distinct chunk counted once, whatever other objects the store holds. It is `0` while that total is 0.

### Example 1

<!-- case: ex5 -->

The fixed method cuts every 64 bytes. The content-defined method cuts where the window hash allows, so its chunks have different sizes, each at least 32 bytes except the last.

### Example 2

<!-- case: ex6 -->

The second version adds a few words near the start. With fixed-size chunks every chunk after the insertion shifts, and the two versions share only what comes before it. With content-defined chunks the cuts after the insertion fall at the same bytes as before, so the versions share most chunks, and the ratio is higher. Either way the file reads back whole.

## Level 4: Refs and garbage collection

An address is hard to remember, and a store that only ever grows fills up. A **ref** gives a name to an object, and the garbage collector frees every object that no ref can reach.

A ref also says what kind of object it names, `"blob"`, `"tree"` or `"manifest"`, because the bytes alone do not say it: the empty text is at once the empty file, the empty folder and the empty manifest, and it is one object.

- `setRef(name, kind, address)`: points the ref `name` at `address`, as an object of `kind`, and returns `true`. A ref that exists already is moved. It returns `false`, and changes nothing, when `kind` is none of the three, or when nothing is stored at `address` (a damaged object is stored).
- `getRef(name)`: the address of the ref, or `""` when there is no such ref.
- `deleteRef(name)`: removes the ref and returns `true`, or returns `false` when there is no such ref. It frees nothing by itself.
- `collectGarbage()`: frees what no ref reaches, in two phases, and returns the number of bytes freed.

**Mark.** Every object that a ref reaches is live. A ref reaches its own object. A tree reaches every object its lines name, files and folders, and through each folder everything below it. A manifest reaches its chunks. A blob reaches nothing, even when its bytes happen to read like a folder. An object that several refs or folders reach is one object, and it is live if any of them reaches it. To follow a tree or a manifest, the collector opens it, checked as `get` checks it. Files and chunks are marked by their address and never opened.

**Sweep.** Every object that is not live is deleted, damaged or not, and the answer is the total of their bytes, as they are now.

**When the mark fails.** If a tree or a manifest that the mark must open is missing or damaged, the collector cannot know what that object reached, so it deletes nothing and returns `-1`. Damage to an object that no ref reaches does not stop it: that object is garbage, and it is freed.

A ref of kind `"tree"` always names a tree object made by `snapshot`, and one of kind `"manifest"` a manifest made by `putFile`, though either may have been damaged since. A ref of kind `"blob"` may name any object.

### Example 1

<!-- case: ex7 -->

`main` names the second snapshot and `old` the first. While both refs exist, every object is live and nothing is freed. Once `old` is deleted, the collector frees the old `README.md` and the old root, but keeps `src`, which the second snapshot shares, and the new snapshot still reads.

### Example 2

<!-- case: ex8 -->

The folder `src` is damaged, and `main` reaches it, so the collector cannot tell what `src` reached and frees nothing. Putting the text of `src` again repairs it, and the collector then frees the note that no ref names.

## Constraints

- At most 5,000 calls per test.
- A text passed to any method is at most 20,000 characters, and the data of `chunkSizes` and `putFile` at most 50,000.
- A snapshot has at most 500 files, a path at most 10 names, and the paths of a snapshot are distinct, with no file's path being a folder of another (`a` and `a/b` never in the same snapshot).
- `method` is always `"fixed"` or `"cdc"`.
- A ref name is 1 to 20 printable ASCII characters.
- The store never holds more than 10,000,000 bytes.

## Follow-ups

- `diff` opens only the folders that changed. How many tree objects does it open for a snapshot of a million files where one file changed, ten folders deep?
- Two snapshots that differ in one file share every other folder. How many bytes does the second snapshot add, as a function of the depth of that file and the size of each folder's text?
- Content-defined chunks average about 96 bytes here. What changes when the cut condition is a multiple of 4096 instead of 64? What do the minimum and maximum sizes protect against?
- The collector reads every live tree on every run. How would you keep it from rereading the folders that did not change since the last run?
- A real store writes objects to disk while a collection runs. Which order of writing an object and moving a ref keeps the collector from freeing an object that is about to be named?

## Hints

### Hint 1

Keep a dictionary from address to the stored bytes. To put data, turn it into bytes with UTF-8, hash them with your language's SHA-256, and write the 32-byte digest as 64 lowercase hexadecimal characters: that string is the key. Dedup is then a lookup before you store. To get, look the address up, hash the bytes you found, and hand them back only when the digest is the address again.

### Hint 2

Count bytes, not characters: in Python `len(data.encode("utf-8"))`, in TypeScript `Buffer.byteLength(data, "utf8")`, in Java and Kotlin the length of `getBytes(StandardCharsets.UTF_8)`. `damage` changes the bytes under an address without moving them, so `check` and `get` must hash the bytes again every time rather than trust a flag.

### Hint 3

Build a snapshot from the bottom up. Group the paths by their first name: a name with nothing after it is a file of this folder, and the others form a subfolder, which you build first, the same way, to get its address. Then write this folder's lines, sorted by name, and put the text.

### Hint 4

`diff` is a walk over two trees at once. Compare the root addresses first; if they differ, open both folders, take the union of their names, and for each name look at the two entries. Recurse only into a pair of folders whose addresses differ. Collect the changes and sort them by path at the end.

### Hint 5

For `"cdc"`, compute `P = 257^15 mod 1000000007` once. Walk the data keeping the window hash of the last 16 bytes: add the new byte with `h = (h·257 + b) mod M`, and before that, once the window is full, remove the byte that leaves with `h = (h − out·P) mod M`, adding `M` if the result is negative. Use 64-bit integers. A cut needs a chunk of 256 bytes, or a chunk of at least 32 bytes whose window hash is a multiple of 64.

### Hint 6

For `dedupRatio`, keep two things per method: a running total of the data sizes, and a dictionary from chunk address to chunk size. The ratio is the total divided by the sum of the dictionary's sizes, as a floating-point division.

### Hint 7

The mark is a walk from every ref with a stack and a set of what has been visited. Push each ref with its kind; when you pop a tree, open it and push its lines with their kinds, and when you pop a manifest, push its chunks as blobs. Remember the visited pairs of kind and address, not addresses alone, so that a tree reached first through a blob ref is still opened when a tree ref reaches it. Finish the whole mark before you delete anything.
