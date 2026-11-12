# B-Tree Index

## Statement

Build `BTreeIndex`, the structure a database uses to find rows by the value of a column without reading the whole table. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working with the rules of the later levels applied.

**What is an index?** A table stores its rows wherever they fit, in no useful order. To answer "which row has the order number 4711?" without help, the database has to read every row. An index is a second structure, kept sorted by one column, that maps each value of that column, the *key*, to the place where its row lives, the *row id*. It works like the index at the back of a book: you look up a word and get a page number, instead of reading the book.

**Why a tree of pages?** A database keeps its data on disk, and a disk is read in blocks of a fixed size, such as 8 kilobytes, called *pages*. Fetching a page takes far longer than searching the keys inside it once it is in memory, so what decides the speed of a lookup is how many pages it reads. A balanced binary search tree reads one node per level, and with a million keys it is about 20 levels deep: 20 page reads. A *B-tree* puts many keys in one node, a page's worth, so each node has many children and the tree is very shallow. With 100 children per node, three levels already reach 100 × 100 × 100 = one million keys: three page reads. It stays that shallow under every insert and delete, because it only ever grows or shrinks at the root, so every leaf is always at the same depth.

**The variant built here.** This problem builds a popular variant called a *B+ tree*:

- every entry, a key with its row id, lives in a *leaf*, and the leaves are linked from left to right, so that the entries can be read in key order without going back up the tree;
- the nodes above the leaves, the *inner nodes*, hold only *separator keys*, which say which child to go down to.

**Shape.** The constructor gets a number `d`, called `minKeys`. Every node except the root holds at least `d` and at most `2d` keys; the root holds at most `2d`, a root leaf may hold none, and a root inner node holds at least one. A leaf holds its entries sorted by key. An inner node holds sorted separators `s1 < s2 < ... < sk` and `k + 1` children `c0, c1, ..., ck`: every key below `c0` is smaller than `s1`, every key below `ci` is at least `si` and smaller than `s(i+1)`, and every key below `ck` is at least `sk`. All the leaves are at the same depth.

For example, with `d = 1` this tree holds the keys 10, 20, 30, 50, 60, 80 and 90. The root sends keys below 50 to the left and the others to the right, and the leaves at the bottom hold the entries.

```text
                 [50]
          [20]          [60 80]
   [10]  [20 30]   [50]  [60]  [80 90]
```

Aim to finish in 150 minutes. A good split: read the statement in the first 15 minutes, then finish level 1 by about minute 50, level 2 by 70, level 3 by 115 and level 4 by 140, keeping the last minutes for a final run.

## Input

- `BTreeIndex(minKeys)`: creates an empty index whose nodes hold from `minKeys` to `2 * minKeys` keys, as described above. The empty index is one empty leaf, which is the root.
- A **key** is a list of integers, one per indexed column. Levels 1 to 3 index one column, so every key there is a list of one integer, such as `[42]`, and keys compare by that integer. Within one test, every key has the same number of integers.
- A **row id** is a non-negative integer. The index stores it next to its key and gives it back; it never interprets it.
- Each level's section describes the methods it adds and their parameters.

## Output

Methods that change the index return a `bool`: `true` when they changed it, `false` when they changed nothing. A search for a key that is not in the index returns `-1`. Lists of row ids are in key order.

## Level 1: Search and insert

- `search(key)`: the row id stored with `key`, or `-1`.
- `insert(key, rowId)`: adds the entry. The index is *unique*: if `key` is already in it, nothing changes and the answer is `false`, and the old row id stays. Otherwise the answer is `true`.
- `levels()`: the tree, one string per depth, from the root down to the leaves. A node prints as its keys in order, separated by single spaces, inside square brackets: `[20 30]`. A leaf prints its keys only, not the row ids. The nodes of one depth are listed from left to right, separated by single spaces. The empty index prints as `["[]"]`. The example tree above prints as `["[50]", "[20] [60 80]", "[10] [20 30] [50] [60] [80 90]"]`.

**Going down.** Search and insert both start at the root. In an inner node, count the separators that are less than or equal to the key you look for; if that count is `i`, go down to child `ci`. A key equal to a separator goes right, because a separator is a copy of the first key of the leaf it was made from. Repeat until you reach a leaf.

**Inserting.** Go down to the leaf where the key belongs and put the entry there, in order. If the leaf now holds `2d + 1` entries, it is *full* and splits:

1. **A leaf splits.** The left leaf keeps the first `d` entries, and a new leaf right after it gets the other `d + 1`, the middle entry included. The new leaf is linked between the old leaf and the leaf that came after it. A *copy* of the new leaf's first key is inserted into the parent as a separator, just before the pointer to the new leaf. The key stays in the leaf: leaves hold every entry.
2. **An inner node splits.** If the parent now holds `2d + 1` keys, it splits too. The left node keeps the first `d` keys and their `d + 1` children, the middle key *moves* up into its own parent (it stays in neither half), and a new node right after it gets the last `d` keys and their `d + 1` children. This can repeat up the tree.
3. **The root splits.** When the root splits, a new root is made with the one key that moved up and two children. This is the only way the tree gets taller.

### Example 1

<!-- case: ex1 -->

With `d = 2` a node holds up to four keys, so the first four inserts fill the root leaf. The fifth makes it full with `[10 20 30 40 50]`: the left leaf keeps `[10 20]`, the new leaf gets the middle key and the rest, `[30 40 50]`, and a new root holds a copy of `30`. Searching `40` goes right of `30` and finds the row id `400`. Inserting `30` again is refused, and the row id stays `300`.

### Example 2

<!-- case: ex2 -->

With `d = 1` a node holds one or two keys. The third insert makes the root leaf `[20 50 80]` full: it splits into `[20]` and `[50 80]`, under a new root that holds a copy of `50`. Then `10` and `30` make `[10 20 30]` full, which splits into `[10]` and `[20 30]` and puts a copy of `20` next to `50` in the root. Inserting `60` splits `[50 60 80]`, and the copy of `60` makes the root `[20 50 60]` full: as an inner node it splits by moving `50` up into a new root, and the tree is three levels deep. Inserting `90` splits `[60 80 90]`, and `80` joins `60` in their parent. This is the tree drawn in the statement.

## Level 2: Range scans and page reads

- `rangeScan(low, high)`: the row ids of every entry whose key is at least `low` and at most `high`, in key order. It is `[]` when `low > high`.
- `scanVisits(low, high)`: how many nodes the scan of `rangeScan(low, high)` reads, counted as below. This is the number of pages the scan would read from disk.
- `height()`: the number of depths of the tree: 1 for a tree that is one leaf. Every `search` reads exactly this many nodes.

**How a scan reads the tree.** The scan goes down from the root to a leaf, as a search for `low` does, and each node on the way counts as one visit, so the leaf it reaches makes `height()` visits. In that leaf, it starts at the first key that is at least `low` and reads the entries in order. It stops at the first key greater than `high`. When it has read past the last entry of a leaf without stopping, it follows the link to the next leaf, which counts as one more visit, and goes on there from the first entry; when there is no next leaf, it stops. So a scan that ends exactly on the last key of a leaf still reads the next leaf, to find out that it is done, and a leaf with no key at least `low` is passed over the same way.

### Example 1

<!-- case: ex3 -->

The tree has two depths, so a scan starts with two visits. The scan from `15` to `45` starts in the leaf `[10 20]` at `20`, steps to `[30 40]` (three visits), reads `30` and `40`, steps to `[50 60 70]` (four visits) and stops at `50`. The scan from `60` to `60` stops at `70` without leaving its leaf: two visits. Nothing lies between `71` and `99`.

### Example 2

<!-- case: ex4 -->

Twenty keys inserted in a mixed order give a tree three levels deep with seven leaves. A scan of three keys reads four nodes: three on the way down and one more leaf, because `[7 8]` ends before `9`. A scan of every key reads the three nodes on the way down and the six other leaves, nine in all. It never reads the inner node `[13 16 18]`: the leaf links lead past it. With `d = 50`, a million keys fit in a tree at most four levels deep, so a search reads at most four pages.

## Level 3: Delete with borrow and merge

- `remove(key)`: removes the entry with `key`. It is `false`, and nothing changes, when the key is not in the index.

**Removing.** Go down to the leaf as a search does and remove the entry. The separators above are *not* changed, even when one of them is a copy of the removed key: it still separates the keys correctly, and a search for it still goes to the right leaf. If the leaf is the root, or it still holds at least `d` entries, you are done.

Otherwise the leaf holds `d - 1` entries: it has *underflowed*. Its *siblings* are the children of the same parent just before and just after it (a child at either end of its parent has only one). The fix tries these cases in order and uses the first that applies:

1. **Borrow from the left sibling**, if it holds more than `d` entries: move its last entry to the front of this leaf. The separator in the parent between the two becomes the new first key of this leaf.
2. **Borrow from the right sibling**, if it holds more than `d` entries: move its first entry to the end of this leaf. The separator between the two becomes the new first key of the right sibling.
3. **Merge with the left sibling**, if there is one: move every entry of this leaf to the end of the left sibling, then remove this leaf from the leaf links and remove it and the separator between the two from the parent.
4. **Merge with the right sibling**: move every entry of the right sibling to the end of this leaf, then remove the right sibling from the leaf links and remove it and the separator between the two from the parent.

A merge takes a key out of the parent. If the parent is the root and has no key left, its only child becomes the root, and the tree gets one level shorter. If the parent is not the root and now holds `d - 1` keys, it is fixed the same way, with the cases in the same order, as inner nodes do it:

1. **Borrow from the left sibling** (more than `d` keys): the separator between the two in their parent moves down to the front of this node's keys, the left sibling's last key moves up to take its place, and the left sibling's last child moves to the front of this node's children.
2. **Borrow from the right sibling** (more than `d` keys): the separator between the two moves down to the end of this node's keys, the right sibling's first key moves up to take its place, and the right sibling's first child moves to the end of this node's children.
3. **Merge with the left sibling**: pull the separator between the two down from the parent and append it to the left sibling's keys, then append this node's keys and children to the left sibling's. This node and the separator leave the parent.
4. **Merge with the right sibling**: the same, with this node in the place of the left sibling and the right sibling in the place of this node: the separator, then the right sibling's keys and children, are appended to this node.

This can repeat up to the root, where the rule about an empty root applies.

### Example 1

<!-- case: ex5 -->

Removing `30` leaves `[40]` with one entry, below `d = 2`. The left sibling `[10 20]` holds exactly `d` entries and cannot lend, but the right sibling `[50 60 70]` holds three, so `50` moves left and the separator becomes `60`, the new first key on the right. The separator `30` stays, though the key is gone. Removing `40` leaves `[50]`; neither sibling can lend, so it merges into the left sibling, `[10 20 50]`, and the separator `30` leaves the root. Removing `60` then borrows from the left: `50` moves right and becomes the separator.

### Example 2

<!-- case: ex6 -->

With `d = 1` an inner node holds one or two keys, so one merge below it can leave it with none. Removing `1` empties the leftmost leaf; it has only a right sibling, `[2]`, which cannot lend, so they merge and the parent `[2]` loses its only key. That inner node then borrows through the root from its right sibling `[4 5]`: `3` comes down from the root, `4` goes up to replace it, and the sibling's first child, the leaf `[3]`, moves across. Removing `6` changes nothing above its leaf. Removing `2` empties a leaf again, and this time the inner node cannot borrow, so it merges with its sibling `[5]` and pulls `4` down from the root. The root is left with no key, its only child becomes the root, and the tree loses a level.

## Level 4: Bulk loading and composite keys

**Bulk loading.** Inserting the keys of a new index one at a time costs a walk down the tree for every key, and in increasing order it splits leaf after leaf, leaving every leaf but the last exactly half full (`d` entries out of `2d`). When all the keys are known and sorted, the tree can be built from the bottom up instead, in one pass, with each node filled to a chosen *fill factor*, a percentage. A fill factor below 100 leaves room in every leaf, so the next inserts do not split at once.

- `bulkLoad(keys, rowIds, fillPercent)`: builds the index from the entries `keys[i]` with `rowIds[i]`, where `50 <= fillPercent <= 100`. It is `false`, and nothing changes, when the index already holds an entry or when the keys are not strictly increasing. An empty list of keys loads nothing and is `true`.

The tree is built level by level. Let `c` be `2d * fillPercent / 100`, rounded down; it is between `d` and `2d`.

1. **Leaves.** Cut the entries, in order, into groups of `c`, the last group taking what is left. Each group is a leaf, and the leaves are linked in order.
2. **Inner levels.** Cut the nodes of the level below, in order, into groups of `c + 1` children, the last group taking what is left. Each group becomes an inner node over those children. Its separators are the smallest keys of its children, except the first child: the smallest key of a child is the first key of the leftmost leaf below it.
3. **A short last group.** On every level, if there is more than one group and the last one is too small (fewer than `d` entries for a leaf, fewer than `d + 1` children for an inner node), it is combined with the group before it. When the two fit in one node (at most `2d` entries, or `2d + 1` children), they become one node; otherwise they are split in two halves, the first half taking one more when the number is odd.
4. **The root.** Repeat step 2 until a level has one node: it is the root.

**Composite keys.** An index often covers several columns, such as a department and a hire date, and from this level on a key may hold up to three integers. Keys compare *field by field*: compare the first integers; only if they are equal, compare the second ones; and so on. So `[1, 9]` comes before `[2, 0]`. All the methods of the earlier levels work with such keys. A key prints as its integers joined by commas, without spaces: `[1,9 2,0]` is a node with two keys.

- `prefixScan(prefix)`: the row ids of every entry whose key starts with the integers of `prefix`, in key order. `prefix` holds from one integer up to as many as the keys have.

Because the keys are sorted field by field, all the keys that start with the same prefix sit next to each other in the leaves. That is why an index on (department, hire date) answers "everyone in department 2" quickly, but cannot help with "everyone hired on a given date" across departments.

### Example 1

<!-- case: ex7 -->

With `d = 2` and a fill factor of 100, `c = 4`: the ten entries make leaves of four, four and two (two is not fewer than `d`, so it stays alone). The three leaves make one inner node, the root, with the separators `50` and `90`. Inserting `40` again is refused, as always. The leaves are full, so the very next new key splits one: inserting `35` splits `[10 20 30 35 40]`. A second bulk load is refused because the index is not empty.

### Example 2

<!-- case: ex8 -->

Two-column keys, inserted one by one. They are sorted field by field: every key starting with `1` comes before every key starting with `2`, whatever the second field. The prefix `[2]` finds the three keys that start with `2`, in key order. The range from `[1, 5]` to `[2, 6]` holds `[1, 9]`, `[2, 3]` and `[2, 5]`. The prefix `[4]` matches nothing, and a prefix as long as the key is an exact match.

## Constraints

- `1 <= minKeys <= 32`.
- At most `3 * 10^4` calls per test, and at most `2 * 10^4` entries in the index at any time.
- A key holds from 1 to 3 integers, each between `-10^6` and `10^6`; at levels 1 to 3, exactly 1.
- `0 <= rowId <= 10^9`.
- A bulk load has at most `2 * 10^4` keys, and as many row ids as keys.

## Follow-ups

- A leaf split leaves two half-full leaves, so an index filled in increasing key order ends up about half empty. How could a split favor that pattern, and what would it cost for random keys?
- Borrowing one entry fixes an underflow, but the next remove from the same leaf underflows again. What changes if a borrow evens out the two siblings instead?
- The separators only steer the search, so they need not be real keys. For text keys, how short could a separator be, and what does that buy?
- How would you support a scan from high to low keys, and what would the leaves need?
- Several threads reading and changing the tree at once must not see a node half split. Which nodes does an insert need to lock, and for how long?

## Hints

### Hint 1

Start with a tree that is only one leaf: a sorted list of keys and a list of row ids next to it. A binary search gives the position of a key for both `search` and `insert`. Get these right, then add splitting.

### Hint 2

You need two kinds of node: a leaf (keys, row ids, a link to the next leaf) and an inner node (separator keys, children). To go down from an inner node, count the separators that are less than or equal to the key. That count is the position of the child to visit, and the same binary search gives it.

### Hint 3

Remember the path on the way down: every inner node you pass and the position of the child you took. After the leaf changes, walk that path backwards to repair the nodes above, one level at a time. You need no pointer from a child to its parent.

### Hint 4

The two splits differ only in what happens to the middle key. A leaf split copies it up and keeps it in the right leaf, because leaves must hold every entry. An inner split moves it up and keeps it in neither half, because an inner node with `k` keys must have exactly `k + 1` children.

### Hint 5

`rangeScan` and `scanVisits` are the same walk: one function can return both the row ids and the count. Go down as for a search with `low`, then follow the leaf links. Count the nodes on the way down, and one more for every link you follow.

### Hint 6

For `remove`, the parent and the position in it are all you need to find the siblings: they are the children just before and just after. Write one repair for a leaf and one for an inner node, each with its four cases in the order of the statement, and call the right one for every node on the path that has too few keys.

### Hint 7

An inner node borrows by rotating through the parent: the separator between the two siblings comes down into the node, the sibling's key at the near end goes up to replace it, and the sibling's child at the near end moves across with it. An inner merge pulls the separator down between the two lists of keys.

### Hint 8

For `bulkLoad`, write one function that turns a count into group sizes: groups of a given size, the last one combined with the one before it when it is too small. Build the leaves with it, then each inner level from the list of nodes below. Keep, next to each node of the current level, the smallest key below it: an inner node's separators are those of its children after the first, and its own smallest key is its first child's. For composite keys, compare field by field (a tuple in Python, a small comparison function elsewhere), and for `prefixScan` go down to the first key whose first fields are at least the prefix, then read leaves until the first fields are greater than it.
