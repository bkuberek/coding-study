# Review: the facts of the hashing guides

The seven guides of the path "Hashing: from your first hash map to tamper-evident ledgers" ([guides](../specs/guides.md), [ADR 0025](../decisions/0025-concept-guides-and-learning-paths.md)) state facts about languages, libraries and standards. This page lists each one with where it was checked, so that a later review starts from the sources, and records what the first independent accuracy review changed.

"Quote" means the exact text was read on that page. "Run" means an example of the guide, or a one-off program, printed it: on CPython 3.13, OpenJDK 21.0.2, Go 1.27.3 and Node 24.18.0. A fact that could not be checked was left out of the guides.

## Python

| # | Claim | Source |
|---|-------|--------|
| P1 | Dicts preserve insertion order, guaranteed since 3.7 and a CPython implementation detail in 3.6; updating a key keeps its place; a key added after deletion goes to the end | Quote: [stdtypes, dict](https://docs.python.org/3/library/stdtypes.html#mapping-types-dict); run: `keys_and_order.py` |
| P2 | Keys must be hashable; lists, dicts and other mutable types may not be keys; `1`, `1.0` and `True` index the same entry | Quote: stdtypes, dict; run: `python_hash.py`, `keys_and_order.py` |
| P3 | Numbers that compare equal must hash equal | Quote: [stdtypes](https://docs.python.org/3/library/stdtypes.html) |
| P4 | Objects that compare equal must have the same hash | Quote: [data model, `__hash__`](https://docs.python.org/3/reference/datamodel.html#object.__hash__) |
| P5 | A class that overrides `__eq__` without `__hash__` gets `__hash__ = None` | Quote: data model; run: `keys_and_order.py` |
| P6 | `str` and `bytes` hashes are salted per process against the O(n²) denial of service of oCERT-2011-003; default since 3.3; changing hashes changes set iteration order | Quote: data model |
| P7 | `PYTHONHASHSEED`: unset or `random` seeds randomly; an integer fixes the seed; 0 disables randomization | Quote: [command line](https://docs.python.org/3/using/cmdline.html#envvar-PYTHONHASHSEED); run: `python_hash.py` |
| P8 | Integer hashes are equal across seeds; tuples of strings are not | Run: `python_hash.py` |
| P9 | `Counter` is a dict subclass for counting hashable objects; a missing item counts 0; `most_common` orders equal counts by first appearance | Quote: [collections](https://docs.python.org/3/library/collections.html); run: `top_k.py` |
| P10 | `heapq.nlargest` equals `sorted(..., reverse=True)[:n]`; best for small n, `sorted` for large, `min` or `max` for 1; heapq is a min-heap | Quote: [heapq](https://docs.python.org/3/library/heapq.html) |
| P11 | `bisect_left` and `bisect_right`; `key` added in 3.10 | Quote: [bisect](https://docs.python.org/3/library/bisect.html); run: `event_ranges.py` |
| P12 | `itertools.accumulate(..., initial=...)` adds one leading element; added in 3.8 | Quote: [itertools](https://docs.python.org/3/library/itertools.html) |
| P13 | `hashlib`: `digest` and `hexdigest`; `sha256` always present; MD5 and SHA1 have known collision weaknesses; password hashing must be tunable, slow and salted; `pbkdf2_hmac` and `scrypt` | Quote: [hashlib](https://docs.python.org/3/library/hashlib.html); run: a SHA-256 digest is 32 bytes |
| P14 | `hmac` implements RFC 2104; `compare_digest` avoids content-based short circuiting against timing analysis | Quote: [hmac](https://docs.python.org/3/library/hmac.html); run: `digests_and_chains.py` |
| P15 | CPython's dict uses open addressing, preferred over chaining for the link overhead; compact and ordered as of 3.6 | Quote: [`Objects/dictobject.c`](https://github.com/python/cpython/blob/main/Objects/dictobject.c) |
| P16 | Changing a dict's size during iteration raises `RuntimeError: dictionary changed size during iteration` | Run |

## Java

| # | Claim | Source |
|---|-------|--------|
| J1 | `HashMap`: constant-time `get` and `put` assuming good dispersal; default load factor 0.75; rehash to about twice the buckets; default capacity 16; no order guarantee; `Comparable` keys may break ties | Quote: [HashMap, Java 21](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/HashMap.html) |
| J2 | A structural modification adds or deletes mappings, changing a value is not one; fail-fast iterators throw `ConcurrentModificationException` on a best-effort basis | Quote: HashMap, Java 21; run: adding keys during a loop throws |
| J3 | `HashMap.newHashMap(numMappings)`, since 19, sizes the map so that the expected mappings fit without resizing | Quote: HashMap, Java 21 |
| J4 | `new HashMap<>(100)` starts with 128 buckets and resizes at the 97th entry; `HashMap.newHashMap(100)` does not resize for 100 | Run (reflection with `--add-opens`) |
| J5 | OpenJDK: `TREEIFY_THRESHOLD = 8`, applied when adding to a bin that already holds 8 (`binCount >= TREEIFY_THRESHOLD - 1`); `MIN_TREEIFY_CAPACITY = 64`; `UNTREEIFY_THRESHOLD = 6`, applied when a resize splits a tree bin; removal untreeifies by a shape check; tree bins are red-black trees; `hash()` is `h ^ (h >>> 16)` | Quote: [OpenJDK `HashMap.java`](https://github.com/openjdk/jdk/blob/master/src/java.base/share/classes/java/util/HashMap.java) |
| J6 | `String.hashCode()` is `s[0]*31^(n-1) + ... + s[n-1]` in `int` arithmetic; the empty string hashes to 0; `"Aa"` and `"BB"` both hash to 2112 | Quote: String, Java 21; run: `StringHashes.java` |
| J7 | Mutable keys: a map's behavior is not specified if a key changes in a way that affects `equals` | Quote: Map, Java 21; run: `MutableKey.java` |
| J8 | `List.hashCode()` is defined from the elements | Quote: List, Java 21 |
| J9 | `ArrayList` capacity grows automatically; only constant amortized cost per added element is specified | Quote: [ArrayList, Java 21](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/ArrayList.html) |
| J10 | Arrays compare by identity as keys: a `HashSet` holds two equal `int[]` twice | Run |
| J11 | Left out: "since Java 8" for tree bins (JEP 180), because openjdk.org refused the request and the version could not be checked | |

## Go, JavaScript and Rust

| # | Claim | Source |
|---|-------|--------|
| G1 | Map iteration order is not specified and not guaranteed to be the same from one iteration to the next; entries added during iteration may or may not be produced | Quote: [the Go specification](https://go.dev/ref/spec#For_range) |
| G2 | Go 1 made map iteration order unpredictable on purpose | Quote: [Go 1 release notes](https://go.dev/doc/go1#iteration) |
| G3 | Since Go 1.12, `fmt` prints maps sorted by key | Quote: [Go 1.12 release notes](https://go.dev/doc/go1.12#fmt); run: `top_k.go` |
| G4 | Go 1.24's built-in map is based on Swiss Tables | Quote: [Go 1.24 release notes](https://go.dev/doc/go1.24) |
| G5 | `maps.Keys`, `slices.Collect` and `slices.Sorted` were added in Go 1.23; `maps.Keys` order is unspecified | Quote: [maps](https://pkg.go.dev/maps), [slices](https://pkg.go.dev/slices) |
| G6 | A missing map key reads as the zero value | Run: `top_k.go` |
| JS1 | `Map` iterates in insertion order; keys compare with SameValueZero, so `NaN` finds `NaN`; any value may be a key; object keys are strings or symbols; objects have prototype keys; `Map` has `size` and suits frequent additions and removals | Quote: [MDN, Map](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Map); run: `canonical_keys.mjs` |
| JS2 | Array keys of a `Map` compare by identity; plain-object keys become strings, every object `"[object Object]"` | Run: `canonical_keys.mjs` |
| R1 | `HashMap`'s default hasher resists HashDoS, is randomly seeded, and is currently SipHash 1-3, subject to change; other hashers are faster for small keys but typically lose that protection; the table is a port of SwissTable; equal keys must hash equal; changing a stored key is a logic error | Quote: [Rust `HashMap`](https://doc.rust-lang.org/std/collections/struct.HashMap.html) |
| R2 | The keys are generated once per thread, then one is incremented for every new `RandomState`, giving every map a different iteration order | Quote: [`library/std/src/hash/random.rs`](https://github.com/rust-lang/rust/blob/master/library/std/src/hash/random.rs) |

## Standards, designs and arithmetic

| # | Claim | Source |
|---|-------|--------|
| S1 | RFC 9162 Merkle tree: leaf `HASH(0x00 || d)`, node `HASH(0x01 || left || right)`, split at the largest power of two below n; the domain separation is required for second-preimage resistance; inclusion proofs | Quote: [RFC 9162](https://www.rfc-editor.org/rfc/rfc9162.html) §2.1.1, §2.1.3.1; run: `merkle_proofs.py` |
| S2 | Bitcoin duplicates the last hash on odd levels, so `[1,2,3,4,5,6]` and `[1,2,3,4,5,6,5,6]` share a root (CVE-2012-2459) | Quote: [`consensus/merkle.cpp`](https://github.com/bitcoin/bitcoin/blob/master/src/consensus/merkle.cpp) |
| S3 | Swiss tables keep one metadata byte per slot, a control bit and 7 bits of the hash, and use SSE to narrow 16 candidates | Quote: [Abseil design notes](https://abseil.io/about/design/swisstables) |
| S4 | oCERT-2011-003: predictable collisions let crafted POST parameters keep a CPU busy for hours on Java, PHP, Python, Ruby and other platforms | Quote: [oCERT-2011-003](https://ocert.org/advisories/ocert-2011-003.html) |
| S5 | 23 keys in 365 buckets collide with probability 50.7%; 2^(n/2) inputs give about 39% (1 − e^(−1/2)), and about 1.18 · 2^(n/2) give one half | Run: `buckets.py`; arithmetic |
| S6 | With a 0.75 limit and doubling from 4 buckets, resizes happen at 4, 7, 13, 25 and 49 entries, and copy fewer than 2 entries per insert overall | Run: `chaining.py` (1.54 at 1,000, 1.97 at 100,000) |
| S7 | SHA-256 digests are 32 bytes; a one-letter change flipped 113 of 256 bits | Run: `digests_and_chains.py` |
| S8 | Linear probing: about (1 + 1/(1 − α))/2 probes for a hit and (1 + 1/(1 − α)²)/2 for a miss | Knuth, The Art of Computer Programming, vol. 3, §6.4; recalled, the arithmetic at α = 0.5 and 0.9 checked |
| S9 | Generic attack costs of about 2ⁿ for preimages and 2^(n/2) for collisions; universal hashing bounds a pair's collision probability by 1/m | Standard results, stated without a fetched source |

## Changes from the first accuracy review (2026-11-11)

The review found no factual errors that needed rework; these are its findings and what changed.

| Finding | Change |
|---------|--------|
| Spoilers in designing-with-hash-maps: the registry example was nearly `randomized-set`, the flag history `time-based-kv-store`, and the ordered-map notes the full `lru-cache` recipe | The registry became a symbol table (map plus array, dense ids), the flag history a window query over page views (`bisect_left` at both ends); the LRU recipe, `move_to_end`, access-order `LinkedHashMap` and the random-member note were cut back to the idea |
| Spoilers in prefix-sums: remainders with first positions, the seed and the distance check together answered `continuous-subarray-sum` | The remainder row, the negative-remainder trap and the minimum-length trap were removed, with their `%` sources |
| Spoilers in canonical-keys: letter counts as a key, and tagged keys answering `valid-sudoku` | The letter-count note, the tagged-keys example and note were removed; the invariant note uses word shapes; practice lines name the question only |
| Spoiler in hash-maps-and-sets: the two-sum practice line was its third hint | Reworded to the problem's question |
| The MAC example did not verify the way a receiver does | `accept` recomputes the tag of the received message and compares it with `compare_digest`; an edited message fails with a guessed-key tag and with the original tag, and the original pair passes |
| The Merkle drawing lost which node owns which leaves | One subtree per row, with the root's row last |
| "Open addressing resizes at lower load factors" was too broad | Now "classic linear probing", with Swiss tables running fuller |
| Treeification details | On adding to a bin that already holds 8; the 6 applies when a resize splits a bin; removal uses a shape check |
| `new HashMap<>(n)` still resizes | `HashMap.newHashMap(n)` (Java 19), with the 128-bucket example |
| Resize sizes were 4, 8, 16 | 4, 7, 13, 25, 49 |
| `ConcurrentModificationException` | Only for structural changes, on a best-effort basis |
| Property order in the crypto table | "From the hardest attack to the easiest" |
| Rust keys per process | Per thread, changed for every new map; "currently" kept for SipHash 1-3 |
| "O(n log n) at worst overall" | "Given an O(n) count" |
| Misra-Gries | Survivors may include false positives; a second pass confirms |
| Dynamic arrays "double" | Any constant factor; Java only promises constant amortized cost |
| Birthday bound | 39% at 2^(n/2), one half at about 1.18 · 2^(n/2) |
| `JSON.stringify` and rounding | Canonical only for arrays of primitives; rounding still splits values across a boundary |
| `plum` seemed to bypass the hash box | One chain per key |
| "Head" and the odd node | "Chain digest", as the ledger problem says; duplicating the odd node is a trade-off, pointing to the problem's `[a, b, c]` and `[a, b, c, c]` follow-up |
| Duplicate job ids; salting of tuples | `submit` refuses a duplicate id; the guide and `python_hash.py` show tuples of strings change with the seed |
