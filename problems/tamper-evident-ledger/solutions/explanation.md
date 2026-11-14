# Tamper-Evident Ledger: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| precomputed-digests | optimal | O(1) per comparison; O(log n) per commonPrefix; O(log b) per proof | O(r) | default answer; it survives all four levels without a rewrite |

Here `r` is the number of records, `n` the number of sealed batches of the shorter chain, and `b` the number of records in a batch. Hashing a record, a batch or a tree node costs time in proportion to the bytes hashed, and that work is done once, when the value is created, not when it is asked for.

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | Fingerprint a batch | each batch keeps its record digests and its batch digest; `sameBatch` compares two stored digests |
| 2 | Chain batches | each chain keeps its pending records, its sealed batches and the chain digest after every sealed batch |
| 3 | Find where chains part | nothing new: the list of chain digests from level 2 is searched by bisection |
| 4 | Prove membership | each sealed batch builds its Merkle tree the first time it is asked, and keeps every level of it |

The choice that makes the later levels cheap is level 2 keeping the chain digest after every batch, not only the last one. Level 3 is then a search over a list that is already there, and the tree of level 4 hangs off the record digests that level 1 computed.

## Approach: precomputed-digests (Digests computed once and kept)

### Intuition

A digest is a fingerprint: equal data gives equal digests, and different data gives different ones. If every batch carries its fingerprint, comparing two batches no longer reads their records. Chaining extends the trick to a history: when each batch's digest is hashed together with the digest before it, the last digest is a fingerprint of everything before it too, so two long histories are compared with one equality check. The same property makes it searchable: the digests of two histories agree for the first `k` batches and then never again, so the point where they part can be bisected. A Merkle tree finally lets a batch be summarized by one root while a single record is proved against it with a handful of hashes.

### Algorithm

1. Encode a record: canonicalize the amount (when it has a point, strip the trailing zeros and then the point; `-0` becomes `0`), write each of `id`, `sender`, `receiver` and the amount as a 4-byte big-endian byte length followed by the UTF-8 bytes, and concatenate the four fields. The record digest is the SHA-256 of that.
2. A batch keeps its record digests and its digest, the SHA-256 of the record digests joined in order. `addBatch` builds one, and `sameBatch` compares the stored digests.
3. A chain keeps pending records, sealed batches and a list of chain digests. `addRecord` appends to pending; when pending reaches the batch size, it builds a batch, appends `SHA-256(previous chain digest || batch digest)` to the list (the previous digest is 32 zero bytes for the first batch) and clears pending. `chainDigest` is the last entry, or 64 zeros; `sameChain` compares the two last entries.
4. `commonPrefix` bisects on `k` in `0 .. min(len)`: if the digests at position `k - 1` are equal, the answer is at least `k`; otherwise it is below `k`.
5. A batch builds its tree on the first request: leaves are `SHA-256(0x00 || record digest)`, and each level above is `SHA-256(0x01 || left || right)` over neighbours, copying the last node of a level of odd length. The root is the single node at the top.
6. `proof` walks from the leaf up. At each level the sibling of position `i` is `i xor 1`, on the left when that position is smaller, and the next position is `i / 2`. `verify` starts from the leaf of the canonical record and applies each step on the side it names, rejecting a malformed step first, and compares the final hexadecimal to the root.

### Correctness

Equality: SHA-256 is deterministic, so equal records give equal digests. For the other direction the encoding must be injective, and it is: each field carries its byte length, so from the bytes of a record the four fields can be read back uniquely, and a batch digest hashes fixed-width record digests, so the sequence of records can be read back too. Different batches therefore hash different inputs, and a collision between different inputs is what a hash function is chosen to make practically impossible. The canonical amount makes `1`, `1.0` and `1.00` one input on purpose.

Chain: the chain digest after batch `k` is `H(d(k-1) || b(k))`, so by induction on `k` it is a function of `b(1) .. b(k)` in order, and different sequences give different digests. `sameChain` is therefore equal exactly when the sealed sequences are equal, and pending records, which are never hashed, cannot matter.

Bisection: let `P(k)` mean "the first `k` batches agree". `P(0)` holds, and if `P(k)` fails then `P(k + 1)` fails, because a difference in the first `k` batches is a difference in the first `k + 1`. `P(k)` is exactly "the chain digests after batch `k` are equal", which is why the chain digest, not the batch digest, is the thing to compare. A predicate that is true and then false is searched correctly by keeping `low` as a size known to agree and `high` as the largest size that might, and moving to the upper middle `(low + high + 1) / 2` so the range always shrinks.

Tree: a node is a function of the leaves under it, so the root depends on every record. A proof lists the sibling at every level, and hashing the record's leaf with them in order rebuilds the path to the root; a different record, or a sibling that was changed, gives a different value unless a hash collides. The `0x00` and `0x01` prefixes make leaves and nodes hash different inputs, so a node can never be passed off as a leaf.

### Complexity

- Time: O(1) per comparison; O(log n) per commonPrefix; O(log b) per proof — `sameBatch` and `sameChain` compare 32 bytes; `commonPrefix` halves a range of at most `n` positions with one comparison each; `proof` reads one sibling per level of a tree of height `log b`, and building the tree and the digests costs O(b) hashing once per batch.
- Space: O(r) — a record digest, a leaf and about one more node per record, plus one chain digest per sealed batch.

### Trade-offs

- Computing the digest in the constructor makes every comparison O(1) at the price of the hashing up front. Computing it lazily on the first comparison is just as correct and moves the cost, which matters only when most batches are never compared.
- Keeping the whole tree answers a proof in O(log b). Keeping only the record digests and rebuilding the tree for each proof costs O(b) per proof and saves about half the memory. With batches of up to 1,000 records either is fine.
- A linear scan from the start of two chains is simpler than bisection and also correct, but it is O(n) in the number of sealed batches. The bisection works only because each digest is chained to the one before it.
- The chain digest alone, with no tree, already detects any change. The tree adds what the chain cannot do: proving one record to someone who has only the root, without sending the batch.

### Pitfalls and edge cases

- Level 1, joining the fields. Hashing `id + sender + receiver + amount` as one string gives `abcd1` for both `("a", "bc", "d", "1")` and `("ab", "c", "d", "1")`. A separator such as `|` fails the same way as soon as a field contains it. Hidden case `h1` covers boundaries that move between id and sender, receiver and amount, and a field holding the separator, and empty fields that shift. Putting the length of each field in front is what makes the encoding unambiguous.
- Level 1, characters instead of bytes. The length is the number of UTF-8 bytes. `é` is 2 bytes and `😀` is 4, but JavaScript and Java count 1 and 2 UTF-16 units, and Go's `len` counts bytes while Python's `len` counts code points. Hidden case `h6` hashes accented text, an emoji and CJK text. The text is also used as given: `é` and `e` followed by a combining accent are different strings.
- Level 1, the amount. Stripping zeros only after a point keeps `100` as `100`; stripping every trailing zero turns it into `1` and makes `1` and `10` and `100` collide. Hidden cases `h2` and `h3` write the same amount several ways and different amounts that look alike, including `-0`. A floating-point number is the wrong tool here: `0.1` has no exact form and different languages print it differently, which is why the amount arrives as text.
- Level 1, order and counts. A digest that adds or xors the record digests, or sorts them, makes `[a, b]` and `[b, a]` equal; a set makes `[a]` and `[a, a]` equal. Hidden cases `h4` and `h5` check order, repeats and every field of every record.
- Level 1, hexadecimal and bytes. Hash raw bytes between steps and convert to hexadecimal only for the result. Hashing the hexadecimal text of the record digests, or of the previous chain digest, gives a valid digest of the wrong input.
- Level 2, what counts. Hashing pending records into the digest makes two chains with different tails unequal. Using only the last batch's digest, with no previous digest in it, makes `[x, y]` and `[z, y]` equal; hidden cases `h9` and `h12` check both. The first batch uses 32 zero bytes, not an empty input, and an empty chain digest is 64 zeros (`h11`).
- Level 2, sealing at the right moment. A batch seals when pending reaches the size, so the batch of 3 is sealed by the third record, not the fourth (`h13`). The batch size matters only through the batches it produced: the same four records in batches of 2 and in one batch of 4 are different histories (`h10`).
- Level 3, the wrong thing to search. Bisecting over the digests of single batches fails when two chains differ in the middle and hold the same batch later, since equality is then true, false, true. Hidden cases `h17` and `h21` do exactly this. The answer must also hold at every position of the divergence, including the first, the last and chains of uneven length (`h18`, `h19`), and the arguments must give the same answer in either order.
- Level 3, off-by-one in the search. Using the lower middle with `low = middle` never ends; using `high = middle` when the digests differ keeps one size too many. Test a range of 1, an uneven range, and chains that are identical or that share nothing.
- Level 4, the odd node. The last node of a level of odd length is paired with a copy of itself on every level, so its proof step has `"R"` and its own hash. Promoting it unchanged gives another root. A side effect of duplicating is that `[a, b, c]` and `[a, b, c, c]` have the same root (`h33`); the chain digest still tells them apart, because the batch digest hashes the record digests in order. Systems that need the root alone to be unique add the record count to what they hash, or never duplicate.
- Level 4, the prefixes. A tree that hashes a leaf and a node the same way lets someone present an internal node as a record. The `0x00` and `0x01` prefixes make the two inputs different (`h35`).
- Level 4, `verify` as an attack surface. It must reject, not crash on, a step with the wrong number of entries, a side that is not `"L"` or `"R"`, and a hash that is not 64 lowercase hexadecimal digits, which includes uppercase and trailing characters that a lenient hex parser would accept (`h32`). It must compare the result with the exact root, and apply `L` and `R` the right way round.
- Not a security proof. A hash tells you that data changed, not who changed it. Anyone who can rewrite the whole log can also recompute every digest, so the final chain digest or root has to be kept somewhere the writer cannot change, for example published or signed.

### Language notes

- Python: `hashlib.sha256` and `int.to_bytes(4, "big")` do the hashing and the length prefix; `str.encode("utf-8")` gives the bytes and `len` of those, not of the string. `str.rstrip("0")` and `bytes.hex()` cover the amount and the output.
- TypeScript: `Buffer.from(text, "utf8")` gives the bytes, whose `length` is the byte count, where `text.length` counts UTF-16 units. `createHash` from `node:crypto` returns a `Buffer`, and `Buffer.equals` compares two of them; `===` on buffers compares identity.
- Java: `getBytes(StandardCharsets.UTF_8)` and `MessageDigest.getInstance("SHA-256")`. `ByteBuffer.putInt` writes big-endian by default. `byte[]` has no value equality, so digests are compared with `Arrays.equals`, and a `List<byte[]>` cannot be compared with `equals`. `HexFormat` (Java 17) formats and parses hexadecimal; `Integer.toHexString` on a signed byte would print the wrong digits.
- Kotlin: the same JVM classes. `ByteArray.contentEquals` is the value comparison, where `==` on arrays is identity; `"%02x".format(byte)` formats a signed `Byte` correctly. `trimEnd('0')` and `trimEnd('.')` strip the amount.
- Go: `len` of a string is already the byte count, which is what the length prefix needs, and `binary.BigEndian.PutUint32` writes it. `crypto/sha256` hashes bytes; `bytes.Equal` compares digests; `hex.EncodeToString` formats them. A `[]byte` is not comparable with `==`, and a copy of a slice shares its backing array, so padding a level appends to a copy.
