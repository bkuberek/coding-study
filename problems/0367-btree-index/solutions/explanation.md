# B-Tree Index: Explanation

## Overview

| Approach | Role | Time | Space | Use when |
|----------|------|------|-------|----------|
| bplus-tree | optimal | O(d log_d n) per search, insert or remove; O(d log_d n + k) per scan of k entries; O(n) per bulk load | O(n) | default answer; one tree with a path stack serves all four levels |

Here `n` is the number of entries, `d` is `minKeys`, and `k` is the number of entries a scan reads.

## How the design grows level by level

| Level | Change | State after the level |
|-------|--------|-----------------------|
| 1 | Two node kinds; go down by counting separators; split on the way back up | `Leaf` (keys, row ids, `next`) and `Inner` (keys, children); the root; a path of `(inner node, child position)` pairs from every descent |
| 2 | Scans follow `next`; visits are counted on the same walk | nothing new: the leaf links of level 1 are what make a scan cheap |
| 3 | Repair an underflow with the parent and the child position from the path | nothing new: the same path that drives splits drives borrows and merges |
| 4 | Build the levels from the bottom; compare keys field by field | a group-size function; keys were lists from the start, so composite keys change only the comparison |

The early choices that keep the later levels small: keep the leaf links from level 1 (a scan without them goes back up the tree for every leaf), remember the path during the descent instead of storing parent pointers (a split or merge would otherwise have to update the parent pointer of every child it moves), and compare keys with one function (level 4 then changes one place).

## Approach: bplus-tree (B+ tree with linked leaves)

### Intuition

A B-tree is a search tree whose nodes are as wide as a disk page, so the tree is shallow, and whose balance is kept by a simple trick: nodes split when they overflow and merge when they underflow, and the tree only grows or shrinks at the root, so every leaf stays at the same depth. The B+ variant keeps every entry in a leaf and links the leaves in order, so a search reads one node per level and a range scan, once it has found its first leaf, reads leaves only. The separators in the inner nodes are signposts, not data: a separator may outlive the key it was copied from, as long as it still divides the keys correctly.

### Algorithm

1. **Descend.** From the root, in an inner node take child `i`, where `i` is the number of separators less than or equal to the key (a binary search for the upper bound). Record the node and `i` on a path stack. Stop at a leaf.
2. **Insert.** Binary-search the leaf; refuse a key that is there. Otherwise insert the entry. While the current node has `2d + 1` keys, split it: a leaf keeps its first `d` entries, a new right leaf takes the other `d + 1` and is linked after it, and the right leaf's first key is the separator to insert; an inner node keeps its first `d` keys and `d + 1` children, its key `d` is the separator, and a new node takes the rest. Pop the parent from the path and insert the separator at the child position and the new node just after it. If the path is empty, make a new root over the two halves.
3. **Scan.** Descend with `low`, counting one visit per level. In the leaf, start at the first key at least `low`; read entries until a key exceeds `high`; at the end of a leaf, move to `next` and count a visit, or stop when there is none.
4. **Remove.** Descend, delete the entry, leave the separators alone. While the node is not the root and has `d - 1` keys, pop its parent and position `i` and repair it with the siblings at `i - 1` and `i + 1`: borrow from the left, borrow from the right, merge into the left, merge the right into it. Leaves move entries and set the separator to the first key on the right side of it; inner nodes rotate a key through the parent and move one child, or pull the separator down into a merge. Finally, an inner root with no keys is replaced by its only child.
5. **Bulk load.** With `c = 2d * fillPercent / 100` rounded down, cut the entries into leaves of `c` and each next level into inner nodes of `c + 1` children, combining a short last group with the one before it (one node if they fit, otherwise two halves, the first one larger). Carry the smallest key of every node upward: an inner node's separators are the smallest keys of its children after the first.
6. **Composite keys and prefixes.** Compare keys field by field. For a prefix of `p` fields, descend by counting the separators whose first `p` fields are smaller than the prefix, then read the leaves while the first `p` fields are not greater than the prefix, keeping those that are equal.

### Correctness

**Search finds every key.** Invariant: for an inner node with separators `s1..sk`, every key below child `ci` is at least `si` (when `i > 0`) and smaller than `s(i+1)` (when `i < k`). Going to the child after the separators that are less than or equal to the key respects it, so the descent reaches the only leaf that can hold the key. A leaf split puts a copy of the right leaf's first key in the parent: everything left of it is smaller, everything right of it is at least as large. An inner split moves the key that separated the two halves. Removing an entry from a leaf shrinks a range without crossing any separator, which is why a separator that copies a removed key is still correct. A leaf borrow sets the separator to the first key of the right side, which divides the two leaves again; an inner rotation moves the old separator down to the side whose range it bounds and lifts the sibling's end key, which bounds the child that moved across; a merge removes the separator between two ranges that become one.

**Balance and occupancy.** Splits and merges keep children at the depth of their siblings, and only the root adds or removes a level, so all leaves stay at the same depth. A split of `2d + 1` keys leaves `d` and `d + 1` for a leaf, and `d` and `d` for an inner node (one key moves up), so both halves hold at least `d`. A leaf merges only when the sibling holds exactly `d` entries, giving `d + (d - 1) = 2d - 1` entries; an inner merge adds the separator, giving `d + 1 + (d - 1) = 2d` keys: neither exceeds `2d`. A borrow takes from a sibling that holds more than `d`, so the sibling keeps at least `d`.

**Bulk loading builds a legal tree.** Because `fillPercent >= 50`, `c` is at least `d`, and at most `2d`, so every full group is a legal node. A short last group combined with its neighbour forms one node when the two fit, and otherwise holds more than `2d` entries (or `2d + 1` children), so both halves are at least `d` (or `d + 1`). The leaves and the inner nodes of one level are built in key order, so the smallest key of each child is a correct separator, and every level shrinks until one node is left.

**Composite keys.** Comparing field by field is a total order, and the tree uses no property of the keys other than that order. All the keys with a given prefix are contiguous in it, so a prefix scan can start at the first one and stop at the first key whose prefix is greater.

### Complexity

- Time: O(d log_d n) per search, insert or remove; O(d log_d n + k) per scan of k entries; O(n) per bulk load — every node holds at least `d` keys, so the tree has O(log_d n) levels; each level costs a binary search and, when a node changes, a shift of up to `2d + 1` keys and children; a split or merge touches one node per level at most. A scan adds the entries it reads and at most one leaf per `d` of them. A bulk load copies every entry once and builds each inner level from the one below, a geometric series that sums to O(n).
- Space: O(n) — the leaves hold the `n` entries and the inner nodes hold fewer than `n / d` separators in all.

### Trade-offs

- **Borrow one entry or even out the siblings.** Moving a single entry is the smallest repair, but the next remove from the same leaf underflows again. The original B-tree paper and later surveys repair an underflow by redistributing the keys of the two siblings evenly, which touches the same pages (the two siblings and their parent) and makes the next repair less likely.
- **Separators that may be stale.** Leaving separators alone on a remove keeps the remove to one leaf in most cases. The price is that `levels()` can show a key that is no longer in the index, which is correct but surprising.
- **Path stack or parent pointers.** A path stack costs `O(log_d n)` memory per call and nothing between calls. Parent pointers make the walk back up free, but every split, merge and borrow has to update the parent pointer of each child it moves.
- **B+ tree or plain B-tree.** A plain B-tree keeps entries in inner nodes too, so a search can stop early, but a range scan must walk up and down the tree, and the inner nodes, holding row ids, fit fewer keys per page.
- **Bulk loading or inserting.** Building from sorted keys writes each page once and fills it to a chosen level. Inserting the same keys one by one in increasing order leaves every leaf but the last half full; a fill factor of 100 packs the pages, but then the first insert into any leaf splits it.

### Pitfalls and edge cases

- A key equal to a separator goes right. Counting the separators strictly smaller than the key sends it left, and every search for a key that was copied into a separator fails (hidden cases `h1` and `h2` search for every separator).
- The middle key of a leaf split is copied and stays in the right leaf; the middle key of an inner split moves up and leaves both halves. Doing the inner split like the leaf split leaves a node with as many children as keys (`h1`, `h5`).
- A leaf with exactly `2d` entries is full but legal; only `2d + 1` splits it (`h4`). The left half keeps `d`, not `d + 1`.
- A refused insert leaves the old row id (`ex1`, `h2`).
- The scan counts the step into a leaf that only shows a key above `high`, and the step out of a leaf with no key at least `low` (`h6`, `h9`). It does not count the inner nodes it skips thanks to the leaf links.
- An empty index has height 1, prints `["[]"]` and a scan of it reads one leaf (`h7`, `h12`).
- The separators are not updated when their key is removed (`ex5`, `h14`, `h15`); a borrow does update the one separator between the two siblings, to the first key of the right side of it.
- The order of the repairs is fixed: left borrow, right borrow, left merge, right merge (`h10`, `h11`, `h16`, `h27`). Merging into the left sibling empties the right node, not the other way round.
- An inner borrow is a rotation through the parent; moving the sibling's key straight across instead breaks the order of the separators (`h12`).
- The root is exempt from the minimum: a root leaf may be empty, and an inner root survives with one key. It is replaced by its child only when it has none (`ex6`, `h12`).
- `c` is rounded down: with `d = 3` and a fill factor of 90 a node gets 5 keys, not 6 (`h19`). The short last group is checked on every level, against `d` entries for leaves and `d + 1` children for inner nodes (`h17`, `h24`, `h25`, `h26`).
- A bulk load is refused on a non-empty index and on keys that repeat or go down; it is allowed again after every entry has been removed (`h20`).
- Composite keys compare field by field, not by their sum or by the first field alone (`h21`), and negative fields sort before zero.
- A prefix scan must start at the first key that begins with the prefix. Padding the prefix with zeros to a full key and searching for that skips the keys whose next field is negative (`h21`); compare only the first fields, or use a comparison in which a prefix sorts before every longer key that starts with it, as Python tuples, `Arrays.compare`, `slices.Compare` and Rust's `Vec` do.

### Language notes

- Python compares tuples field by field, so converting each key list to a tuple once makes `bisect` work on composite keys unchanged.
- Java has `Arrays.compare(int[], int[])`, which compares lexicographically; Kotlin calls the same method on an `IntArray`. TypeScript has no array comparison, so write a loop that returns at the first differing field. Go has `slices.Compare` and Rust orders `Vec<i32>` lexicographically with its derived `Ord`.
- Binary search for "the number of separators less than or equal to the key" is `bisect_right` in Python and `partition_point(|s| s <= key)` in Rust. Java's `Collections.binarySearch` returns `-(insertion point) - 1` when the key is absent and any matching index when it is present, so the Java, Kotlin, TypeScript and Go references write the two small loops, lower bound and upper bound, by hand.
- The references use one node type with a `leaf` flag in every language, leaving the unused fields empty; a small class hierarchy or a Rust `enum` works as well. The Rust reference keeps the nodes in an arena (`Vec<Node>`) and refers to them by index, which makes the leaf links and the path stack plain integers instead of shared references; a merged node stays in the arena, unreachable.
- Go slices need care when a node splits: copy the right half into a new slice before truncating the left, or both nodes share one backing array and the next append to the left half overwrites the right one.

## Further reading

- R. Bayer and E. McCreight, "Organization and maintenance of large ordered indexes", Acta Informatica 1(3), 173-189, 1972, [doi:10.1007/BF00288683](https://doi.org/10.1007/BF00288683). The paper that introduced B-trees, for an index kept on a disc: every node but the root has between `k + 1` and `2k + 1` children, all leaves are at the same depth, a full page splits around its middle entry, and an underfull page either evens out with a neighbour or is concatenated with it.
- D. Comer, "The Ubiquitous B-Tree", ACM Computing Surveys 11(2), 121-137, 1979, [doi:10.1145/356770.356776](https://doi.org/10.1145/356770.356776). A survey of B-trees and their variants, with the B+-tree used here: keys only in the leaves, the leaves linked as a "sequence set", a leaf split that promotes a copy of the key, and separators left in place after a delete.
- [CREATE INDEX, storage parameters](https://www.postgresql.org/docs/current/sql-createindex.html) in the PostgreSQL documentation: what a B-tree fill factor does during an initial build and to later page splits.
- [Multicolumn indexes](https://www.postgresql.org/docs/current/indexes-multicolumn.html) in the PostgreSQL documentation: why a B-tree on several columns serves conditions on its leading columns best.
