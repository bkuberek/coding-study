# Consistent Hash Ring: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| sorted-points | optimal | O(log p) per lookup; O(p + k log p) per join or leave; O(m p) per assignBounded | O(p + k) | default answer; one sorted list of points serves all four levels |

Here `p` is the number of points on the ring, `k` the number of followed keys and `m` the number of keys passed to a call.

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | One point per node; a binary search finds a key's owner; a list in join order for modulo placement | `points`, sorted `(position, label, node)`; `joined` |
| 2 | Several points per node, labelled `node`, `1#node`, ... | the number of points of each node, to list its positions |
| 3 | A set of followed keys, and the report of the last change | `tracked`, `report` |
| 4 | Walks from the owner point: one skips nodes already listed, one skips full nodes | nothing new: both walk `points` |

The early choice that pays off is to store points, not nodes: a sorted list of `(position, label, node)`. Level 1's single point is the first point of level 2's virtual node, the arcs of level 2 are the gaps between neighbouring points, level 3 compares two lookups, and both walks of level 4 step through the same list.

## Approach: sorted-points (Sorted ring points with binary search)

### Intuition

A ring is a sorted list read in a circle. Sorting the points by position, and by label for equal positions, gives the ring order with its tie-break built in. The owner of a key is the first point at or after the key's position, which a binary search finds, and "wrapping around" is the index `0` when the search runs off the end. Everything else is a walk forward from that index, or a comparison of the answers before and after a change.

### Algorithm

1. `positionOf`: FNV-1a over the UTF-8 bytes, keeping 32 bits after every multiplication.
2. `addVirtualNode(node, count)`: refuse a known node or a count below 1; otherwise insert the `count` points `(positionOf(label), label, node)` into the sorted list, append the node to the join order, remember its count, and make the report. `addNode` calls it with `1` and returns the position.
3. `nodeFor(key)`: binary search for the first point whose `(position, label)` is at least `(positionOf(key), "")`; the empty label sorts before every real label, so this is the first point with a position at least the key's. Index past the end means `0`. `""` on an empty ring.
4. `moduloNodeFor(key)`: `joined[positionOf(key) mod len(joined)]`. `countMoves` evaluates both rules for each key twice: on the current state and on a copy with the new point and the new name.
5. `arcShare`: for each point in order, its arc is `position - previous position`; the first point's arc is `position - last position + 2^32`. Add the arcs per node.
6. Report: before a change, record `owner(key)` for every followed key; after it, keep the keys whose owner differs, sorted, as `[key, before, after]`.
7. `replicas`: from the owner index, step forward modulo the number of points, collecting nodes not collected yet, until `count` nodes or every node is collected.
8. `assignBounded`: `capacity = ceil((d + n) * m / (d * N))` in integers. For each key in order, step forward from its owner index while that point's node holds `capacity` keys, then place it there.

### Correctness

Ring order: sorting by `(position, label)` puts the points in clockwise order, and among points at the same position the one with the smaller label first, as the statement orders them. The first point at or after a key's position in this order is the owner by definition, and when no point has a position that large, the owner is the first point of the circle. Labels are distinct, because node names hold no `#` and each label `i#node` names its node and its index, so the order is total.

Arcs: point `j` owns exactly the positions after the previous point's position and up to its own, which number `position[j] - position[j - 1]`, `0` for a point that ties the one before it. The first point also owns the positions after the last point, through `2^32 - 1`, and from `0` up to its own, which is `position[0] - position[last] + 2^32`. These sets partition the ring, so the shares add up to `2^32`, and with one point the share is `2^32`.

Minimal movement: adding points can only change the owner of a key whose position is in an arc that a new point now ends, and the new owner is then the new node. So every move of a join goes to the joining node, and no key moves between two nodes that stay (monotonicity). Removing a node's points changes only the owner of keys whose owner point was removed, and each such key goes to the next remaining point clockwise. The report compares the owners before and after, so it lists exactly these keys.

Bounded loads: the capacity is at least `(1 + ε) m / N`, so `N` nodes hold more than `m` keys, and at most `m - 1` keys are placed before any given key: some node has room, and the walk, which visits every point within one round, stops. The integer formula is the exact ceiling of the fraction `(d + n) m / (d N)`, which is `(1 + n / d) m / N`.

### Complexity

- Time: O(log p) per lookup; O(p + k log p) per join or leave; O(m p) per assignBounded — a lookup is one binary search; a join or a leave rebuilds or shifts the list of `p` points and looks up every followed key twice; a bounded placement may walk the whole ring for a key when many nodes are full.
- Space: O(p + k) — one entry per point, one per node, and the followed keys with the report.

### Trade-offs

- A sorted array makes lookups fast and changes slow: inserting a node's points shifts the array. A balanced search tree (a `TreeMap` in Java, a B-tree map in Rust) makes both logarithmic. For a ring that changes rarely and is read for every request, the array is the usual choice.
- More points per node give fairer shares, and cost memory and a longer search: with `v` points per node the list is `v` times longer, and `log` of it grows only by `log v`.
- The report recomputes the owner of every followed key, which is simple and costs `O(k log p)`. Only keys in the arcs that changed can move, so a store with millions of keys walks just those arcs and their ranges of key positions.
- `assignBounded` places a fixed list once, with one capacity for every node. The paper keeps the loads bounded while keys and nodes come and go. To change few capacities at a time, it gives some bins the capacity `ceil(cm/n)` and the others `floor(cm/n)`, so that the total is `ceil(cm)`, and it moves the keys that have to move when a capacity or a membership changes.
- FNV-1a is simple and fast, and gives bit-exact answers in every language, which is why it is used here. Its last bytes mix weakly, which the label scheme works around. Keys that differ only at the end, such as `user:1` to `user:9`, still land close together, which is visible in the uneven `keyCounts` of the hidden cases.

### Pitfalls and edge cases

- 32-bit wraparound: in Java and Kotlin an `int` product turns negative, and in TypeScript a plain `*` of two large numbers loses the low bits beyond `2^53`. Positions above `2^31`, such as `"a"`, and longer texts catch both (`h1`).
- Hashing UTF-16 code units or code points instead of UTF-8 bytes fails only for texts outside ASCII, such as `"café"` and `"日本"` (`h1`).
- The boundary is inclusive: a key exactly at a point's position belongs to it. A key named like a node has that node's position, which tests it (`h2`). Searching for the first position strictly greater gives the next node.
- Equal positions: `glbvs` and `yacxa` collide under FNV-1a. The second point owns nothing and gets the keys only when the first leaves (`h2`, `h6`, `h11`).
- Modulo placement indexes the nodes in join order, not in sorted order, and a removed node shifts the ones after it (`h3`).
- Labels put the number first (`1#alpha`), point `0` is the bare name, and `positions` lists them in point order, not sorted (`h5`).
- Each point's arc ends at its own position; the first point's arc also wraps across the top. Forgetting the wrap leaves the shares short of `2^32` (`h6`).
- The report belongs to the last change that was not refused, and lists rows sorted by key with `B` before `a`; `""` stands for no owner on an empty ring (`h8`). `countMoves` is a question and must not touch the report (`h10`).
- `replicas` lists nodes in walk order from the owner, not sorted, and skips nodes already listed instead of stopping at them or listing them twice (`ex7`, `h11`, `h13`).
- The capacity is an exact integer ceiling: `ε = 5/3` with 9 keys on 3 nodes gives `8`, where floating point can give `9` (`h12`). Keys are placed in list order, and a reversed list fills the nodes differently (`h13`).

### Language notes

- FNV-1a: Python masks with `% 2**32` after each multiplication. TypeScript uses `Math.imul(h ^ byte, 16777619) >>> 0`, which multiplies in 32 bits; the bytes come from `new TextEncoder().encode(text)`. Java multiplies `int`s, which wrap, and converts with `Integer.toUnsignedLong`; Kotlin does the same with `Int` and `toLong() and 0xffffffffL`. Go uses `uint32`, whose multiplication wraps, and Rust `u32::wrapping_mul`. Java and Kotlin take the bytes from `getBytes(StandardCharsets.UTF_8)` and `toByteArray(Charsets.UTF_8)`, and mask each byte with `0xff` because their bytes are signed; Go and Rust strings are UTF-8 already.
- Binary search: `bisect_left` in Python on tuples; a hand-written lower bound in TypeScript; `Collections.binarySearch` with a comparator in Java, which returns `-(insertion point) - 1` for a missing key; `binarySearch` with a comparator in Kotlin, the same; `sort.Search` in Go; `partition_point` in Rust.
- Sorting points: tuples in Python and Rust, a comparator on `(position, label)` in the others. Labels are ASCII, so comparing by character code agrees in every language.
- The integer capacity: `-(-a // b)` in Python, `Math.floor((a + b - 1) / b)` in TypeScript (exact below `2^53`), and `(a + b - 1) / b` in integer division elsewhere. Products stay below `2^31`, given the limits.
- Rust methods take `&mut self` as the bridge requires; the node of a point is cloned out of the list before a count in a map is changed.

## Further reading

- David Karger, Eric Lehman, Tom Leighton, Rina Panigrahy, Matthew Levine and Daniel Lewin, "Consistent Hashing and Random Trees: Distributed Caching Protocols for Relieving Hot Spots on the World Wide Web", Proceedings of the 29th ACM Symposium on Theory of Computing (STOC 1997), pages 654 to 663, [doi:10.1145/258533.258660](https://doi.org/10.1145/258533.258660): why a standard hash function, such as a linear congruential one modulo `p`, sends almost every item to a new place when its range `p` changes, the properties balance, monotonicity, spread and load (section 4.1), and the construction that maps buckets and items to the unit interval, gives each bucket several points, and assigns an item to the closest one (section 4.2).
- Vahab Mirrokni, Mikkel Thorup and Morteza Zadimoghaddam, "Consistent Hashing with Bounded Loads", Proceedings of the 29th ACM-SIAM Symposium on Discrete Algorithms (SODA 2018), pages 587 to 604, [doi:10.1137/1.9781611975031.39](https://doi.org/10.1137/1.9781611975031.39), also [arXiv:1608.01350](https://arxiv.org/abs/1608.01350): the bound `ceil(cm/n)` with `c = 1 + ε`, forwarding a ball from a full bin to the next bin clockwise, the invariant that no ball passes a bin that is not full, and the capacities of big and small bins (section 1.2).
- Giuseppe DeCandia and others, "Dynamo: Amazon's Highly Available Key-value Store", Proceedings of the 21st ACM Symposium on Operating Systems Principles (SOSP 2007), pages 205 to 220, [doi:10.1145/1294261.1294281](https://doi.org/10.1145/1294261.1294281): section 4.2 walks the ring clockwise to the first node and gives each node several positions ("virtual nodes"); section 4.3 stores a key on the next nodes clockwise and skips positions so that the list holds distinct physical nodes.
- Landon Curt Noll, Kiem-Phong Vo, Donald E. Eastlake 3rd and Tony Hansen, "The FNV Non-Cryptographic Hash Algorithm", [RFC 9923](https://www.rfc-editor.org/rfc/rfc9923), February 2026, [doi:10.17487/RFC9923](https://doi.org/10.17487/RFC9923): the FNV-1a pseudo-code (section 2), the 32-bit prime `16777619` and offset basis `2166136261` (sections 2.1, 2.2 and 5), and the test values for `""`, `"a"` and `"foobar"` in its test code (section 8.3).
