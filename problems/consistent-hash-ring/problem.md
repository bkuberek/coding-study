# Consistent Hash Ring

## Statement

Build `HashRing`, which decides which *node* (a server) stores each *key* (the name of a piece of data, such as `user:42`), in a way that moves as few keys as possible when nodes join or leave. The API grows over four levels: every level adds methods to the same class, and the methods of earlier levels keep working.

**Partitioning.** When there is more data than one machine can hold, it is split across several nodes. Every client must then find the node of a key on its own, quickly, without asking a central directory, and all clients must agree. The usual start is a hash function: it turns the key into a number, and the number picks the node.

**Why plain modulo moves almost everything.** The simplest rule is "node number `hash(key) mod N`" for `N` nodes. It spreads keys evenly, but look at what happens when a fourth node joins three. A key keeps its node only when `hash mod 3` equals `hash mod 4`:

| hash | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
|------|---|---|---|---|---|---|---|---|---|---|----|----|
| mod 3 | 0 | 1 | 2 | 0 | 1 | 2 | 0 | 1 | 2 | 0 | 1 | 2 |
| mod 4 | 0 | 1 | 2 | 3 | 0 | 1 | 2 | 3 | 0 | 1 | 2 | 3 |

Only 3 of the 12 hash values keep their node; the pattern repeats every 12. In general only about one key in `N + 1` stays, so adding one node moves nearly all the data, and a cache in front of it would suddenly miss on almost every key.

**The ring.** *Consistent hashing* (David Karger and others, 1997) avoids this. Bend the hash values into a circle: positions `0` to `2^32 - 1`, with `2^32 - 1` followed by `0` again. Hash every node to a position too. A key belongs to the first node at or after its own position, going clockwise (towards larger numbers) and wrapping around at the end. When a node joins, it takes only the keys between its position and the node before it; when it leaves, only its own keys go to the next node. Every other key stays where it is. (The paper assigns an item to the nearest node point; this problem uses the form with the next node clockwise, as later papers describe it.)

**Hashing, exactly.** Positions are 32-bit FNV-1a hashes of the UTF-8 bytes of a text:

```text
h = 2166136261
for each byte b of the UTF-8 encoding of the text:
    h = h XOR b
    h = (h * 16777619) mod 2^32
the position is h, from 0 to 4294967295
```

The multiplication must wrap at 32 bits: keep the low 32 bits of the product, read as an unsigned number. Three values from the FNV reference let you check your hash: the empty text gives `2166136261`, `"a"` gives `3826002220` and `"foobar"` gives `3214735720`.

Aim to finish in 90 minutes. A good split: read the statement in the first 10 minutes, finish level 1 by about minute 35, level 2 by 55, level 3 by 70 and level 4 by 85, keeping the last minutes for a final run.

## Input

- `HashRing()`: an empty ring.
- A **node** name is 1 to 20 printable ASCII characters (codes 33 to 126) other than `#`.
- A **key** is 1 to 30 printable ASCII characters (codes 33 to 126).
- `positionOf` takes any text of 0 to 60 characters, Unicode included.
- Each level's section describes the methods it adds and their parameters.

## Output

Positions are integers from `0` to `4294967295`. A method that changes the ring returns `-1` or `false` when it is refused, and then **nothing changes**. A question that has no answer gets the empty answer: `""` for a node and `[]` for a list.

Texts are compared by the numeric codes of their characters, so `B` comes before `a` and `user:10` before `user:2`. A list with one entry per node follows the order of `nodes()`.

## Level 1: Nodes on a ring

- `positionOf(text)`: the FNV-1a position of the text.
- `addNode(node)`: puts the node on the ring at `positionOf(node)` and returns that position. `-1` when the node is on the ring already.
- `removeNode(node)`: takes the node off the ring. `false` when it is not on the ring.
- `nodes()`: the nodes on the ring, sorted.
- `nodeFor(key)`: the node that owns the key, `""` on an empty ring.
- `moduloNodeFor(key)`: the node that plain modulo placement would choose, `""` on an empty ring. The nodes are listed in the order they joined; a node that leaves is taken out of the list and the ones after it move up, and a node that joins again goes to the end. The key goes to the node at index `positionOf(key) mod N` of that list, for `N` nodes.
- `countMoves(keys, node)`: how many entries of `keys` would change owner if `node` joined now, as `[on the ring, under modulo placement]`, with the node at `positionOf(node)` on the ring and at the end of the join order. Nothing changes. `[]` when `node` is on the ring already. On an empty ring every key would move, from no owner to the new node.

**Which node owns a key.** Each node puts a *point* on the ring, labelled with its name. The owner of a key is the node of the first point whose position is greater than or equal to the key's position; when there is none, it wraps around to the point with the smallest position. A key exactly at a point's position belongs to that point. Two points at the same position are ordered by label, by character codes: the first owns the keys up to that position, and the second owns nothing until the first one leaves.

### Example 1

<!-- case: ex1 -->

The first three calls check the hash against the reference values. The three nodes sit at about 37%, 63% and 81% of the way round. `cherry` (position `1232791672`) goes clockwise to `alpha`, and `elder` to `bravo`. `pear` (`3491742317`) sits just before `charlie` (`3495339073`), so `charlie` owns it. `banana` (`3649609552`) is past the last point, so it wraps around to the first one, `alpha`.

### Example 2

<!-- case: ex2 -->

If `echo` joined, at `3567113348`, only one of the fourteen fruit keys would move on the ring (`date`, at `3564297305`, just before it), while modulo placement would move ten. After `echo` joins, `date` belongs to it, and its modulo node changes from `charlie` (`3564297305 mod 3 = 2`) to `bravo` (`mod 4 = 1`). Adding `echo` again is refused. When `bravo` leaves, its keys go to the next point clockwise: `elder` now belongs to `charlie`.

## Level 2: Virtual nodes

With one point each, the arcs that nodes own are very uneven: in Example 1, `alpha` owns everything from `charlie` round to `alpha`, more than half of the ring. The fix is *virtual nodes*: each node puts many points on the ring, each owning a small arc, so that the total of each node's arcs gets close to an equal share. It also spreads the work of a join or a leave over many nodes, as level 3 shows.

**Point labels.** A node with `count` points labels them `node`, `1#node`, `2#node`, up to `(count - 1)#node`, with the number in decimal; point `i` sits at `positionOf` of its label. So `addNode(node)` is a node with one point. The number goes first for a reason: FNV-1a mixes the last bytes of a text weakly. `alpha#1` and `alpha#2` differ only in their last byte, and their positions differ by exactly `16777619`, the FNV prime, less than 0.4% of the ring, so all the points of a node labelled that way would crowd together. A difference in the first bytes is multiplied again by every byte that follows, and lands far away.

- `addVirtualNode(node, count)`: puts the node on the ring with `count` points and appends it to the join order. `false` when the node is on the ring already or `count` is below 1.
- `positions(node)`: the positions of the node's points, point 0 first. `[]` for a node that is not on the ring.
- `arcShare()`: for each node, how many of the `2^32` positions it owns, that is, how many positions a key could have and land on that node. The shares add up to `4294967296`.
- `keyCounts(keys)`: for each node, how many entries of `keys` it owns. A key listed twice counts twice.

The tie rule of level 1 applies to labels: two points at the same position are ordered by their labels.

### Example 1

<!-- case: ex3 -->

Going round the ring, the six points are `2#bravo` (`168442882`), `1#alpha` (`449765251`), `alpha`, `bravo`, `2#alpha` (`3266031418`) and `1#bravo` (`4264744715`). Each point owns the arc from the point before it, so `alpha`'s share is `(449765251 - 168442882) + (1569418667 - 449765251) + (3266031418 - 2718755907)`, and `2#bravo` owns the arc that wraps round from `1#bravo` past the top to `168442882`. Each node owns seven of the fourteen fruits.

### Example 2

<!-- case: ex4 -->

With one point each, the three nodes own about 55%, 27% and 18% of the ring, and a hundred keys `user:1` to `user:100` split `61`, `9` and `30`. With a hundred points each, the shares come to about 32%, 32% and 36%, and the keys split `25`, `38` and `37`.

## Level 3: Keys that move

When a node joins, every key that moves goes to the new node, and it comes from whichever node owned that arc before. When a node leaves, every key that moves comes from it, and each goes to the node of the next point clockwise. No key ever moves between two nodes that both stay. Karger and others call this *monotonicity*. With virtual nodes, a new node takes a little from many nodes, and a leaving node hands its keys to many nodes, instead of loading one neighbour.

- `trackKeys(keys)`: adds the keys to the set of keys the ring follows, and returns how many different keys it follows.
- `lastMoves()`: the report of the latest change of the ring that was not refused (`addNode`, `addVirtualNode` or `removeNode`): one row `[key, from, to]` for each followed key whose owner changed, sorted by key. `from` is `""` when the ring was empty before the change, and `to` is `""` when it is empty after. `[]` before the first change. A refused call keeps the previous report.
- `ownedKeys(node)`: the followed keys that the node owns now, sorted. `[]` for a node that is not on the ring.

The report is made when the change happens, over the keys followed at that moment; keys followed later do not enter it. `countMoves` asks a question and makes no report.

### Example 1

<!-- case: ex5 -->

Three nodes with five points each. Nothing is followed yet, so the report of the last join is empty. When `delta` joins with five points, three of the fourteen followed keys move, all to `delta`, but from two different nodes: `banana` from `bravo`, `grape` and `plum` from `alpha`.

### Example 2

<!-- case: ex6 -->

`bravo` owns `banana` and `peach`. When it leaves, both move away from it, and to different nodes: each goes to the node of the next point after it. Removing `bravo` again is refused, and the report stays the same.

## Level 4: Replicas and bounded loads

**Replicas.** A key stored on one node is lost when that node fails, so a store keeps copies on several nodes. A common rule is to put them on the owner and the next nodes clockwise. With virtual nodes the next point often belongs to a node that is listed already, so the walk skips it, to have the copies on different machines.

- `replicas(key, count)`: start at the key's owner point and walk clockwise, point by point, listing each node the first time you meet it, until `count` nodes are listed or every node is. `[]` when `count` is below 1 or the ring is empty.

**Bounded loads.** Even with virtual nodes, some node can get many more keys than the average, for example when many keys hash close together. Vahab Mirrokni, Mikkel Thorup and Morteza Zadimoghaddam (2016; SODA 2018) give every node a *capacity*, a little above the average, and send a key that arrives at a full node on clockwise to the first node that still has room, as linear probing does in a hash table.

- `assignBounded(keys, numerator, denominator)`: places the entries of `keys`, one at a time in list order, with `ε = numerator / denominator`, and returns the node of each entry, in list order. With `m` entries and `N` nodes, every node has the capacity `ceil((1 + ε) * m / N)`. An entry starts at its owner point and walks clockwise past every point whose node already holds `capacity` entries, to the first point whose node holds fewer. `[]` when the ring is empty or `keys` is empty. Nothing changes: not the ring, not the followed keys, not the report.

Compute the capacity exactly, with integers: `ceil(((denominator + numerator) * m) / (denominator * N))`. Floating point can round a capacity that is exactly an integer up by one. Since `N` times the capacity is more than `m`, some node always has room.

### Example 1

<!-- case: ex7 -->

Going round the ring from `lemon` (`3368108496`), the points are `charlie`, `1#charlie`, `1#bravo`, then past the top `2#bravo`, `1#alpha`. The walk lists `charlie`, skips `1#charlie`, lists `bravo`, skips `2#bravo` and lists `alpha`. Asking for five nodes gives the three there are. `kiwi` starts at `2#alpha`, so its list is `alpha`, `charlie`, `bravo`.

### Example 2

<!-- case: ex8 -->

Without bounds, the fourteen fruits split `5`, `3` and `6`. With `ε = 1/20`, the capacity is `ceil(21 * 14 / (20 * 3)) = ceil(294 / 60) = 5`. The keys are placed in order, and when `plum`, the last one, reaches `charlie`, it already holds five. The next point clockwise is `alpha`, past the top of the ring, which is full too, and then `bravo`, which has room. With `ε = 1/4` the capacity is `ceil(70 / 12) = 6`, no node is full, and every key stays with its owner.

## Constraints

- At most 200 nodes and 10,000 points on the ring at a time; `count` is at most 200, and a count below 1 is refused.
- At most 1,000 calls per test. A list of keys has at most 1,000 entries, and the ring follows at most 1,000 keys.
- `1 <= numerator <= 1000` and `1 <= denominator <= 1000`.

## Follow-ups

- A node with twice the memory should hold about twice the keys. How would you choose its number of points, and what does `arcShare` then show?
- Every join here inserts points into a sorted list. With 10,000 points and frequent changes, which structure keeps both lookups and changes fast?
- When a node leaves, which keys get a new set of `replicas`, and how many copies must be made?
- `assignBounded` places a fixed list once. When keys arrive and leave over time, which placed keys may have to move after a key is deleted, so that no key has walked past a node that now has room?
- FNV-1a is fast and simple, but its last bytes mix weakly, as level 2 shows. Keys such as `user:1` to `user:9` differ only in their last byte too. What would you measure before trusting a hash function to spread your keys?

## Hints

### Hint 1

Start with `positionOf`, and check it against the three reference values before anything else. Encode the text to UTF-8 bytes first: hashing characters instead of bytes gives the same answers for `"a"` and `"foobar"` and different ones for `"café"`. Make sure the multiplication cannot overflow into a negative number or lose its low bits.

### Hint 2

Keep the points in one list sorted by position, and by label for equal positions, each with the node it belongs to. The owner of a key is then the first point at or after the key's position: a binary search finds it, and when the search runs off the end, the answer is the first point.

### Hint 3

Keep a second list of the node names in the order they joined, for modulo placement. For `countMoves`, compute each key's owner twice, once for the ring as it is and once for a copy with the extra point, and the same for the join order with the extra name.

### Hint 4

For `arcShare`, walk the sorted points once. Each point owns the positions after the previous point, up to and including its own, so its arc is the difference of the two positions. The first point's arc wraps round: it also owns everything after the last point.

### Hint 5

For the report of a change, record the owner of every followed key before the change and again after it, and keep the keys whose owners differ. A change that is refused must return before it touches the report.

### Hint 6

For `assignBounded`, compute the capacity as `(a + b - 1) / b` in integers, with `a = (denominator + numerator) * m` and `b = denominator * N`. Keep a count per node, start each key at the index of its owner point, and step the index forward, wrapping to `0` at the end, while the node at that index holds `capacity` keys. For `replicas`, walk the same way from the owner, but skip the nodes already listed.
