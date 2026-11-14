# Tamper-Evident Ledger

## Statement

Build `Ledger`, the core of an audit log: a list of records that nobody should be able to change afterwards without being noticed. Each record says that `sender` paid `receiver` an `amount`, under a unique `id`. Records are collected in batches, and the whole point of the ledger is to answer questions about those batches quickly: are two batches the same, do two histories agree, and does this record really belong to this batch? The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**What is a digest?** A hash function turns any piece of data into a short, fixed-size fingerprint called a digest. This problem uses SHA-256, whose digest is always 32 bytes, written as 64 hexadecimal characters (`0-9` and `a-f`, in lowercase). A hash function behaves the same way every time: the same data always gives the same digest, and a change to the data, even one character, gives a completely different digest. In practice two different pieces of data never share a digest, so equal digests mean equal data. You do not need to know how SHA-256 works inside. Every language here ships one: `hashlib.sha256` in Python, `createHash("sha256")` from `node:crypto` in TypeScript, `MessageDigest.getInstance("SHA-256")` in Java and Kotlin, and `crypto/sha256` in Go.

**Why digests make comparisons fast.** To tell whether two batches of `n` records are equal, you could compare them record by record, which looks at up to `n` records: O(n). Instead, compute each batch's digest once, when the batch is built, and keep it. Comparing two batches is then comparing two 64-character strings, which takes the same time for a batch of 3 records and a batch of 3 million: O(1). The work of reading every record happens once, at construction, not at every comparison. The later levels use the same idea to compare whole histories and to prove that one record is in a batch.

The digests must be exactly the ones the statement defines, character for character, in every language, so the statement fixes how a record is turned into bytes before it is hashed. The expected values in the examples are real digests that you can check your code against.

Aim to finish in 90 minutes. A good split: read the statement in the first 10 minutes, then finish level 1 by about minute 30, level 2 by 45, level 3 by 60 and level 4 by 85, keeping the last minutes for a final run.

## Input

- `Ledger()`: creates an empty ledger. It holds named batches and named chains; the two sets of names are separate, and a name is a non-empty string.
- A record is a list of four strings, in this order: `id`, `sender`, `receiver` and `amount`. The first three are any text, empty included. The amount is a decimal number written as text, such as `"25"`, `"10.50"` or `"-3"`, so that every language reads it the same way.
- Each level's section describes the methods it adds and their parameters.

## Output

Methods that build something return nothing. Every digest or hash the ledger returns is 64 lowercase hexadecimal characters. Questions return a `bool` or an `int`.

## Level 1: Batch fingerprint

A batch is a named list of records.

- `addBatch(name, records)`: stores a batch under `name`, with `records` in the order given and possibly empty. Adding a batch under a name that is already used replaces that batch.
- `batchDigest(name)`: the digest of the batch, as defined below.
- `sameBatch(first, second)`: whether the two batches have the same digest. It must take O(1) time however many records the batches hold, so compute the digest in `addBatch` and keep it.

**How a batch becomes a digest.** The steps are exact:

1. **The amount, canonical form.** `1`, `1.0` and `1.00` are the same amount, and so are `0.5` and `0.50`. Write the amount in canonical form: when it has a decimal point, remove the zeros at the end of the fractional part, and then the point itself if nothing is left after it. `-0` (and `-0.0`) becomes `0`. A number without a point is left alone, so `100` stays `100`, not `1`. Examples: `10.50` becomes `10.5`, `12.00` becomes `12`, `100.0` becomes `100`, `0.05` stays `0.05`.
2. **A field, as bytes.** Write the field's text as UTF-8 bytes, and put the number of those bytes in front of them as a 4-byte unsigned big-endian integer. The field `ab` is `00 00 00 02 61 62`, and an empty field is `00 00 00 00`. The length counts bytes, not characters: `é` is two bytes, and `😀` is four. Text is used exactly as given, with no case folding and no Unicode normalization.
3. **A record, as bytes.** Write the four fields in the order `id`, `sender`, `receiver`, `amount` (canonical), one after the other.
4. **A record digest.** SHA-256 of the record's bytes: 32 raw bytes.
5. **A batch digest.** SHA-256 of all the record digests, as raw bytes, one after the other, in the order of the records. A batch with no records is the SHA-256 of nothing, `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`. The result is written as lowercase hexadecimal.

The order of the records matters: the same records in another order are another batch.

**The trap this encoding avoids.** The first idea is often to join the fields into one text and hash that: `id + sender + receiver + amount`. Then the record `("a", "bc", "d", "1")` and the record `("ab", "c", "d", "1")` both become `abcd1`, and two different records get the same digest. The same happens when fields are joined with a separator such as `|`, as soon as a field contains that separator. A digest is only as good as the bytes behind it. Putting each field's length in front removes the ambiguity, because where each field ends is always known. Hidden cases check records that collide when joined naively.

### Example 1

<!-- case: ex1 -->

`mon` and `tue` hold the same two records in the same order, so they are the same batch. `wed` holds them in the other order, which is another batch. The last call shows the digest of `mon`.

### Example 2

<!-- case: ex2 -->

The two records would both read `abcd1` if their fields were joined, but their encodings differ, so the batches differ and have different digests.

## Level 2: Chain

A chain is a history that grows record by record and is cut into sealed batches of a fixed size. A digest of the chain is a fingerprint of everything sealed so far, so two long histories can be compared in O(1).

- `newChain(name, batchSize)`: creates an empty chain that seals a batch every `batchSize` records. Creating a chain under a name that is already used replaces that chain.
- `addRecord(name, record)`: appends the record to the chain's pending records. When the pending records reach `batchSize`, they are sealed into a batch, in the order added, and the pending list starts empty again.
- `sealedCount(name)`: the number of sealed batches.
- `chainDigest(name)`: the digest of the chain's last sealed batch, as defined below.
- `sameChain(first, second)`: whether the two chains have the same history. It must take O(1) time.

**The chain digest.** A sealed batch has its level 1 digest, computed from its records. The digest of the chain after its `k`-th batch is the SHA-256 of two raw digests, one after the other: the chain digest after batch `k - 1`, and the digest of batch `k`. Before the first batch, the previous chain digest is 32 zero bytes. A chain with no sealed batch therefore has the digest `000...0` (64 zeros), and `chainDigest` returns the digest after the last sealed batch.

Because each chain digest includes the one before it, it stands for the whole history up to that batch: change any record anywhere, and every digest from that batch onwards changes.

- Two chains are the same when they have the same sealed batches in the same order. Pending records do not count, and neither does the batch size, except through the batches it produced: two empty chains are equal whatever their batch sizes, and the same records sealed in different groupings are different histories.
- The amounts in a chain's records are canonical, as in level 1.

### Example 1

<!-- case: ex3 -->

With batches of 2, chains `A`, `B` and `C` all seal the batch `[t-1001, t-1002]`. `A` and `B` differ in their pending third record, which does not count, so all three chains are the same. `chainDigest(A)` shows the digest of the one sealed batch.

### Example 2

<!-- case: ex4 -->

With one record per batch, `x` seals `t-1001` then `t-1002`, `y` seals `t-1003` then `t-1002`, and `z` seals `t-1002` then `t-1001`. `x` and `y` end with the same batch but a different history, and `x` and `z` hold the same batches in a different order, so neither pair is the same chain.

## Level 3: Common prefix

- `commonPrefix(first, second)`: the number of leading sealed batches that the two chains share, that is, the largest `k` such that both chains' first `k` sealed batches are the same. It must take O(log n) time, where `n` is the number of sealed batches of the shorter chain.

Do not compare the batches one by one from the start. The chain digest after batch `k` stands for the first `k` batches, so the chains agree on their first `k` batches exactly when their digests after batch `k` are equal. If they agree on `k` batches, they agree on every smaller number; if they differ at `k`, they differ at every larger number. That makes the answer something you can find by binary search over the chain digests after each batch, so keep the chain digest after every sealed batch, not only the last one.

Careful with what you compare: the digests of the batches alone are not enough. Two chains can differ in the middle and hold the same batch again later, so their later batch digests are equal while their histories are not.

- The answer is at most the sealed count of each chain. Pending records are ignored. Two chains with no sealed batch share 0.

### Example 1

<!-- case: ex5 -->

`A` and `B` seal `t-1001` and `t-1002` and then different batches, so they share 2 batches, in either order of the arguments. A chain shares all of its own batches with itself.

## Level 4: Inclusion proofs

An inclusion proof shows that a record belongs to a sealed batch without handing over the other records. It is built on a Merkle tree: a tree of digests, where each node is the digest of its two children, so the one digest at the top, the root, depends on every record under it.

**The tree of a sealed batch.** The tree uses the record digests of level 1 (before they are combined into the batch digest) and works on raw bytes:

- A **leaf** is SHA-256 of the byte `0x00` followed by the record digest, one leaf per record, in the order of the records.
- A **node** above two nodes `left` and `right` is SHA-256 of the byte `0x01`, then `left`, then `right`.
- A level with an odd number of nodes is paired by **duplicating its last node**: the last node is paired with a copy of itself. This applies on every level, not only the first.
- The **root** is the one node left at the top. For a batch of a single record, the root is its leaf, and its proof is empty.

The `0x00` and `0x01` prefixes keep a leaf from ever being mistaken for a node. The tree never changes the digests of levels 1 to 3.

**Methods.** Batches are numbered from 0 in the order they were sealed, and so are the records of a batch.

- `merkleRoot(name, batchIndex)`: the root of that sealed batch, in hexadecimal.
- `proof(name, batchIndex, recordIndex)`: the proof for that record, a list of steps from the leaf up to just below the root. Each step is a list of two strings, `[side, hash]`: `hash` is the sibling node at that level, in hexadecimal, and `side` is `"L"` when the sibling is the left one of the pair and `"R"` when it is the right one. When a node is the duplicated last one, its sibling is itself.
- `verify(root, record, proof)`: whether `record` belongs to a batch whose root is `root`, using only these three arguments, not the ledger's stored data. Start from the record's leaf, combine it with each step of the proof in order (`left = hash` when `side` is `"L"`, `right = hash` when it is `"R"`), and compare the result to `root`. The record is canonicalized as in level 1, so `1.0` verifies where `1` was stored.

`verify` returns `false`, and never fails the call, for a proof that is not well formed: a step that is not a list of two strings, a side other than `"L"` or `"R"`, or a hash that is not exactly 64 lowercase hexadecimal characters. The root must also match exactly, as 64 lowercase characters.

Indices passed to `merkleRoot` and `proof` always name a sealed batch and a record in it.

### Example 1

<!-- case: ex6 -->

A batch of three records has an odd count, so the third leaf is paired with itself. The proof of the first record has two steps: its right sibling, the leaf of the second record, and then the node over the third record and its copy. The record with the amount changed from `25` to `250` has another leaf, so the same proof does not lead to the root. The proof of the third record starts with its own copy, on the right.

## Constraints

- At most 5,000 calls per test.
- A batch holds at most 1,000 records, and `1 <= batchSize <= 1000`.
- `id`, `sender` and `receiver` are at most 40 characters; a name is 1 to 20 characters.
- An `amount` matches `-?(0|[1-9][0-9]*)(\.[0-9]+)?` and has at most 30 characters.
- Every name used by a call has been created by an earlier call.

## Follow-ups

- Change the amount of one record in a sealed batch and recompute its root. How many hashes does that take with the tree kept in memory, and how many with only the digests of the records?
- Append a record to a chain with no batches and no limit: how would you keep one Merkle root over every record ever added, with proofs that grow as O(log n)?
- Two parties each hold a chain and want to find the first record on which they differ by exchanging as little as possible. What would they send?
- The root of `[a, b, c]` equals the root of `[a, b, c, c]` under the duplicate-the-last-node rule. Does the chain digest tell those batches apart? Why do real systems add the record count to what they hash, or avoid duplicating?

## Hints

### Hint 1

A digest is a fingerprint of some data: the same data always gives the same fingerprint, and different data gives a different one. You do not need to know how it is computed; your language has a function that takes bytes and returns 32 bytes. The speed-up comes from using it once: compute a batch's fingerprint when the batch is created and store it, and then comparing two batches means comparing two stored strings.

### Hint 2

Before hashing, turn each record into bytes in a way where two different records can never give the same bytes. Putting the length of each field in front of it does that, and the length is the number of bytes of the UTF-8 text, not the number of characters. Check your code against the digests in the examples.

### Hint 3

Hash the pieces in the exact order the statement lists them, and keep raw bytes between steps; convert to hexadecimal only when you return a value. Mixing hexadecimal text and raw bytes inside a hash gives a different digest.

### Hint 4

For the chain, keep a list with the chain digest after each sealed batch. The next entry is the hash of the previous entry (32 zero bytes at first) followed by the new batch's digest. The last entry is `chainDigest`.

### Hint 5

"The first `k` batches are the same" is true for the small values of `k` and false from some point on, never the other way around. Binary search for the last `k` where the two lists of chain digests are equal at position `k - 1`.

### Hint 6

For the tree, keep the level of leaves and build each level above it by pairing neighbours, copying the last node when the level has an odd length. The sibling of the node at position `i` is at position `i xor 1`, and its side is `"L"` when that position is smaller than `i`. Move up with `i = i / 2`.

### Hint 7

`verify` repeats on the way up what building did on the way down: start from the leaf of the record and apply each step in order, placing the sibling on the side the step names. Return `false` for a malformed step before you use it.
