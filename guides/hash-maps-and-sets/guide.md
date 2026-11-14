# Hash maps and sets

## The idea

A **hash map** stores values under keys: `ages["ada"] = 30`, then `ages["ada"]` gives 30 back. A **hash set** is the same structure with keys and no values: it answers "is this key in here?". Python calls them `dict` and `set`, Java `HashMap` and `HashSet`, Go has `map`, JavaScript `Map` and `Set`, Rust `HashMap` and `HashSet`.

Both are built on an array of **buckets** and a [hash function](../hash-functions/guide.md). To find a key, hash it, take the hash modulo the number of buckets, and look in that one bucket. Because the hash spreads keys evenly, a bucket holds only a few keys, so a lookup checks a few keys instead of all of them. That is why a lookup takes constant time **on average**, however many keys the map holds.

Three questions make up the rest of the design, and this guide answers each:

1. **Collisions.** Two keys can land in the same bucket. Where does the second one go?
2. **Growth.** A table of 8 buckets holding a million keys would have long buckets. When does the table grow, and what does growing cost?
3. **Keys.** What may be a key, and what breaks if a key changes while it is stored?

## A worked example

### Separate chaining

The simplest answer to collisions: each bucket holds a small list, a **chain**, of the entries that landed there. To put a key, walk its chain; if the key is there, replace its value, otherwise append. To get a key, walk its chain and compare keys with `==`.

```mermaid
flowchart LR
  accTitle: Separate chaining
  accDescr: A table whose bucket 0 holds a chain of two entries, ada then di, whose bucket 2 holds bo, and whose bucket 3 holds cy. Bucket 1 is empty and is not drawn.
  b0["bucket 0"] --> ada["ada: 30"] --> di["di: 33"]
  b2["bucket 2"] --> bo["bo: 31"]
  b3["bucket 3"] --> cy["cy: 32"]
```

<!-- text-of-mermaid sha256:66a882b107efcc39767ea067f6c26cdeb066e4c861d27126d868f62f6a543bf6 -->
```text
┌────────┐    ┌───────┐    ┌──────┐
│bucket 0├───►│ada: 30├───►│di: 33│
└────────┘    └───────┘    └──────┘

┌────────┐    ┌───────┐
│bucket 2├───►│ bo: 31│
└────────┘    └───────┘

┌────────┐    ┌───────┐
│bucket 3├───►│ cy: 32│
└────────┘    └───────┘
```

In the drawing, `ada` and `di` collided in bucket 0, so they share a chain, and finding `di` costs two comparisons instead of one. Bucket 1 is empty. A lookup of a key that is not there, say `zed`, walks the chain of its bucket to the end and answers "not found".

The **load factor** is the number of entries divided by the number of buckets, often written α. If the hash spreads keys evenly, the average chain has length α. Keep α below a constant, and the average lookup checks a constant number of entries. So the table **resizes**: when α passes a limit, it allocates twice as many buckets and puts every entry in again, because each entry's bucket index, `hash mod m`, changes with `m`.

Here is a complete separate-chaining map that doubles when α passes 0.75, the same limit Java's `HashMap` uses by default. It counts how many entries every resize copies.

```python examples/chaining.py
"""A hash map with separate chaining that doubles its buckets when the load factor passes 0.75.

It hashes with zlib.crc32, which is the same in every run, so the output is too; Python's own
hash() of a str changes from run to run."""

import zlib

MAX_LOAD = 0.75


class ChainedMap:
    def __init__(self, buckets: int = 4) -> None:
        self.buckets: list[list[tuple[str, int]]] = [[] for _ in range(buckets)]
        self.size = 0
        self.moved = 0  # entries copied by every resize so far

    def bucket_of(self, key: str) -> list[tuple[str, int]]:
        return self.buckets[zlib.crc32(key.encode()) % len(self.buckets)]

    def put(self, key: str, value: int) -> None:
        chain = self.bucket_of(key)
        for position, (stored, _) in enumerate(chain):
            if stored == key:  # a collision is fine: compare the keys themselves
                chain[position] = (key, value)
                return
        chain.append((key, value))
        self.size += 1
        if self.size / len(self.buckets) > MAX_LOAD:
            self.resize(2 * len(self.buckets))

    def get(self, key: str) -> int | None:
        for stored, value in self.bucket_of(key):
            if stored == key:
                return value
        return None

    def resize(self, buckets: int) -> None:
        entries = [entry for chain in self.buckets for entry in chain]
        self.buckets = [[] for _ in range(buckets)]
        for key, value in entries:
            self.bucket_of(key).append((key, value))
        self.moved += len(entries)


ages = ChainedMap()
for number, name in enumerate(["ada", "bo", "cy", "di"], start=30):
    ages.put(name, number)
    print(f"put {name}: {ages.size} entries in {len(ages.buckets)} buckets")
print("get('cy') =", ages.get("cy"), "| get('zed') =", ages.get("zed"))

for count in (1_000, 100_000):
    table = ChainedMap()
    for number in range(count):
        table.put(f"key{number}", number)
    longest = max(len(chain) for chain in table.buckets)
    print(
        f"{count:>7} puts: {len(table.buckets):>6} buckets, "
        f"{table.moved / count:.2f} moves per put, longest chain {longest}"
    )
```

```output examples/chaining.py
put ada: 1 entries in 4 buckets
put bo: 2 entries in 4 buckets
put cy: 3 entries in 4 buckets
put di: 4 entries in 8 buckets
get('cy') = 32 | get('zed') = None
   1000 puts:   2048 buckets, 1.54 moves per put, longest chain 3
 100000 puts: 262144 buckets, 1.97 moves per put, longest chain 4
```

```typescript examples/chaining.ts
// A hash map with separate chaining that doubles its buckets when the load factor passes 0.75.
//
// It hashes with CRC-32, the checksum zlib computes, so every run, in every language, fills the
// same buckets.

import { crc32 } from "node:zlib";

const MAX_LOAD = 0.75;

type Entry = [key: string, value: number];

class ChainedMap {
  buckets: Entry[][];
  size = 0;
  moved = 0; // entries copied by every resize so far

  constructor(buckets = 4) {
    this.buckets = Array.from({ length: buckets }, () => []);
  }

  bucketOf(key: string): Entry[] {
    return this.buckets[crc32(key) % this.buckets.length]!;
  }

  put(key: string, value: number): void {
    const chain = this.bucketOf(key);
    for (const entry of chain) {
      if (entry[0] === key) { // a collision is fine: compare the keys themselves
        entry[1] = value;
        return;
      }
    }
    chain.push([key, value]);
    this.size += 1;
    if (this.size / this.buckets.length > MAX_LOAD) {
      this.resize(2 * this.buckets.length);
    }
  }

  get(key: string): number | null {
    for (const [stored, value] of this.bucketOf(key)) {
      if (stored === key) return value;
    }
    return null;
  }

  resize(buckets: number): void {
    const entries = this.buckets.flat();
    this.buckets = Array.from({ length: buckets }, () => []);
    for (const entry of entries) this.bucketOf(entry[0]).push(entry);
    this.moved += entries.length;
  }
}

const ages = new ChainedMap();
["ada", "bo", "cy", "di"].forEach((name, index) => {
  ages.put(name, 30 + index);
  console.log(`put ${name}: ${ages.size} entries in ${ages.buckets.length} buckets`);
});
console.log(`get('cy') = ${ages.get("cy")} | get('zed') = ${ages.get("zed")}`);

for (const count of [1_000, 100_000]) {
  const table = new ChainedMap();
  for (let number = 0; number < count; number++) table.put(`key${number}`, number);
  const longest = table.buckets.reduce((most, chain) => Math.max(most, chain.length), 0);
  console.log(
    `${String(count).padStart(7)} puts: ${String(table.buckets.length).padStart(6)} buckets, ` +
      `${(table.moved / count).toFixed(2)} moves per put, longest chain ${longest}`,
  );
}
```

```output examples/chaining.ts
put ada: 1 entries in 4 buckets
put bo: 2 entries in 4 buckets
put cy: 3 entries in 4 buckets
put di: 4 entries in 8 buckets
get('cy') = 32 | get('zed') = null
   1000 puts:   2048 buckets, 1.54 moves per put, longest chain 3
 100000 puts: 262144 buckets, 1.97 moves per put, longest chain 4
```

```java examples/chaining.java
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.zip.CRC32;

// A hash map with separate chaining that doubles its buckets when the load factor passes 0.75.
//
// It hashes with CRC-32, the checksum zlib computes, so every run, in every language, fills the
// same buckets.
public class Chaining {
    static final double MAX_LOAD = 0.75;

    static final class Entry {
        final String key;
        int value;

        Entry(String key, int value) {
            this.key = key;
            this.value = value;
        }
    }

    static final class ChainedMap {
        List<List<Entry>> buckets = emptyBuckets(4);
        int size = 0;
        long moved = 0; // entries copied by every resize so far

        static List<List<Entry>> emptyBuckets(int count) {
            List<List<Entry>> buckets = new ArrayList<>(count);
            for (int i = 0; i < count; i++) {
                buckets.add(new ArrayList<>());
            }
            return buckets;
        }

        List<Entry> bucketOf(String key) {
            CRC32 crc = new CRC32();
            crc.update(key.getBytes(StandardCharsets.UTF_8));
            return buckets.get((int) (crc.getValue() % buckets.size()));
        }

        void put(String key, int value) {
            List<Entry> chain = bucketOf(key);
            for (Entry entry : chain) {
                if (entry.key.equals(key)) { // a collision is fine: compare the keys themselves
                    entry.value = value;
                    return;
                }
            }
            chain.add(new Entry(key, value));
            size += 1;
            if ((double) size / buckets.size() > MAX_LOAD) {
                resize(2 * buckets.size());
            }
        }

        Integer get(String key) {
            for (Entry entry : bucketOf(key)) {
                if (entry.key.equals(key)) {
                    return entry.value;
                }
            }
            return null;
        }

        void resize(int count) {
            List<Entry> entries = new ArrayList<>();
            buckets.forEach(entries::addAll);
            buckets = emptyBuckets(count);
            for (Entry entry : entries) {
                bucketOf(entry.key).add(entry);
            }
            moved += entries.size();
        }
    }

    public static void main(String[] args) {
        ChainedMap ages = new ChainedMap();
        String[] names = {"ada", "bo", "cy", "di"};
        for (int i = 0; i < names.length; i++) {
            ages.put(names[i], 30 + i);
            System.out.printf(
                    "put %s: %d entries in %d buckets%n", names[i], ages.size, ages.buckets.size());
        }
        System.out.println("get('cy') = " + ages.get("cy") + " | get('zed') = " + ages.get("zed"));

        for (int count : new int[] {1_000, 100_000}) {
            ChainedMap table = new ChainedMap();
            for (int number = 0; number < count; number++) {
                table.put("key" + number, number);
            }
            int longest = table.buckets.stream().mapToInt(List::size).max().orElse(0);
            System.out.printf(
                    "%7d puts: %6d buckets, %.2f moves per put, longest chain %d%n",
                    count, table.buckets.size(), (double) table.moved / count, longest);
        }
    }
}
```

```output examples/chaining.java
put ada: 1 entries in 4 buckets
put bo: 2 entries in 4 buckets
put cy: 3 entries in 4 buckets
put di: 4 entries in 8 buckets
get('cy') = 32 | get('zed') = null
   1000 puts:   2048 buckets, 1.54 moves per put, longest chain 3
 100000 puts: 262144 buckets, 1.97 moves per put, longest chain 4
```

```kotlin examples/chaining.kt
import java.util.zip.CRC32

// A hash map with separate chaining that doubles its buckets when the load factor passes 0.75.
//
// It hashes with CRC-32, the checksum zlib computes, so every run, in every language, fills the
// same buckets.

const val MAX_LOAD = 0.75

class Entry(val key: String, var value: Int)

class ChainedMap(buckets: Int = 4) {
    var buckets: List<MutableList<Entry>> = List(buckets) { mutableListOf() }
        private set
    var size = 0
        private set
    var moved = 0L // entries copied by every resize so far
        private set

    private fun bucketOf(key: String): MutableList<Entry> {
        val crc = CRC32().apply { update(key.toByteArray()) }
        return buckets[(crc.value % buckets.size).toInt()]
    }

    fun put(key: String, value: Int) {
        val chain = bucketOf(key)
        // A collision is fine: compare the keys themselves.
        val stored = chain.find { it.key == key }
        if (stored != null) {
            stored.value = value
            return
        }
        chain.add(Entry(key, value))
        size += 1
        if (size.toDouble() / buckets.size > MAX_LOAD) resize(2 * buckets.size)
    }

    fun get(key: String): Int? = bucketOf(key).find { it.key == key }?.value

    private fun resize(count: Int) {
        val entries = buckets.flatten()
        buckets = List(count) { mutableListOf() }
        for (entry in entries) bucketOf(entry.key).add(entry)
        moved += entries.size
    }
}

fun main() {
    val ages = ChainedMap()
    listOf("ada", "bo", "cy", "di").forEachIndexed { index, name ->
        ages.put(name, 30 + index)
        println("put $name: ${ages.size} entries in ${ages.buckets.size} buckets")
    }
    println("get('cy') = ${ages.get("cy")} | get('zed') = ${ages.get("zed")}")

    for (count in listOf(1_000, 100_000)) {
        val table = ChainedMap()
        for (number in 0 until count) table.put("key$number", number)
        val longest = table.buckets.maxOf { it.size }
        println(
            "%7d puts: %6d buckets, %.2f moves per put, longest chain %d"
                .format(count, table.buckets.size, table.moved.toDouble() / count, longest),
        )
    }
}
```

```output examples/chaining.kt
put ada: 1 entries in 4 buckets
put bo: 2 entries in 4 buckets
put cy: 3 entries in 4 buckets
put di: 4 entries in 8 buckets
get('cy') = 32 | get('zed') = null
   1000 puts:   2048 buckets, 1.54 moves per put, longest chain 3
 100000 puts: 262144 buckets, 1.97 moves per put, longest chain 4
```

```go examples/chaining.go
// A hash map with separate chaining that doubles its buckets when the load factor passes 0.75.
//
// It hashes with CRC-32, the checksum zlib computes, so every run, in every language, fills the
// same buckets.
package main

import (
	"fmt"
	"hash/crc32"
)

const maxLoad = 0.75

type entry struct {
	key   string
	value int
}

type chainedMap struct {
	buckets [][]entry
	size    int
	moved   int // entries copied by every resize so far
}

func newChainedMap() *chainedMap {
	return &chainedMap{buckets: make([][]entry, 4)}
}

func (m *chainedMap) bucketOf(key string) int {
	return int(crc32.ChecksumIEEE([]byte(key)) % uint32(len(m.buckets)))
}

func (m *chainedMap) put(key string, value int) {
	b := m.bucketOf(key)
	for i, stored := range m.buckets[b] {
		if stored.key == key { // a collision is fine: compare the keys themselves
			m.buckets[b][i].value = value
			return
		}
	}
	m.buckets[b] = append(m.buckets[b], entry{key, value})
	m.size++
	if float64(m.size)/float64(len(m.buckets)) > maxLoad {
		m.resize(2 * len(m.buckets))
	}
}

// get returns the key's value, and whether the map holds the key.
func (m *chainedMap) get(key string) (int, bool) {
	for _, stored := range m.buckets[m.bucketOf(key)] {
		if stored.key == key {
			return stored.value, true
		}
	}
	return 0, false
}

func (m *chainedMap) resize(count int) {
	old := m.buckets
	m.buckets = make([][]entry, count)
	for _, chain := range old {
		for _, stored := range chain {
			b := m.bucketOf(stored.key)
			m.buckets[b] = append(m.buckets[b], stored)
			m.moved++
		}
	}
}

func main() {
	ages := newChainedMap()
	for i, name := range []string{"ada", "bo", "cy", "di"} {
		ages.put(name, 30+i)
		fmt.Printf("put %s: %d entries in %d buckets\n", name, ages.size, len(ages.buckets))
	}
	cy, hasCy := ages.get("cy")
	zed, hasZed := ages.get("zed")
	fmt.Printf("get('cy') = %d, %t | get('zed') = %d, %t\n", cy, hasCy, zed, hasZed)

	for _, count := range []int{1_000, 100_000} {
		table := newChainedMap()
		for number := range count {
			table.put(fmt.Sprintf("key%d", number), number)
		}
		longest := 0
		for _, chain := range table.buckets {
			longest = max(longest, len(chain))
		}
		fmt.Printf("%7d puts: %6d buckets, %.2f moves per put, longest chain %d\n",
			count, len(table.buckets), float64(table.moved)/float64(count), longest)
	}
}
```

```output examples/chaining.go
put ada: 1 entries in 4 buckets
put bo: 2 entries in 4 buckets
put cy: 3 entries in 4 buckets
put di: 4 entries in 8 buckets
get('cy') = 32, true | get('zed') = 0, false
   1000 puts:   2048 buckets, 1.54 moves per put, longest chain 3
 100000 puts: 262144 buckets, 1.97 moves per put, longest chain 4
```

The trace shows the resize: after the fourth `put`, four entries in four buckets is a load factor of 1.0, over 0.75, so the table doubles to eight buckets. Then look at the cost. A single resize copies every entry, so that one `put` is O(n). But resizes are rare: with a limit of 0.75 they happen when the table holds 4, 7, 13, 25, 49 entries and so on, each about twice the last, so the copies add up to less than `n + n/2 + n/4 + ...`, which is less than `2n`. Spread over all `n` puts, that is fewer than 2 copies per put: 1.54 at 1,000 puts and 1.97 at 100,000, never 2. This is an **amortized** O(1): any single put may be slow, but any sequence of `n` puts costs O(n) in total. And the chains stay short: the longest of 262,144 buckets holds 4 entries.

### Open addressing

The other answer stores every entry in the array itself, with no chains. A key whose **home slot** is taken tries other slots in a fixed order, its **probe sequence**, until it finds its key or an empty slot. The simplest order is **linear probing**: the home slot, then the next slot, then the one after, wrapping around at the end.

```mermaid
flowchart LR
  accTitle: Linear probing when adding 19
  accDescr: 19 hashes to home slot 3, which holds 3. The next slot, 4, holds 11. Slot 5 is empty, so 19 goes there after three probes.
  add["add 19, home slot 3"] --> s3["slot 3 holds 3"] --> s4["slot 4 holds 11"] --> s5["slot 5 empty: store 19"]
```

<!-- text-of-mermaid sha256:9288d32eb3b0db87c3a264c60319c22895bf3a4c0f23498931b9514e6e64dce2 -->
```text
┌───────────────────┐    ┌──────────────┐    ┌───────────────┐    ┌──────────────────────┐
│add 19, home slot 3├───►│slot 3 holds 3├───►│slot 4 holds 11├───►│slot 5 empty: store 19│
└───────────────────┘    └──────────────┘    └───────────────┘    └──────────────────────┘
```

Deleting is where open addressing gets subtle. A search stops at the first empty slot, since the key would have been stored there. So if you delete `11` by emptying slot 4, a later search for `19` stops at slot 4 and wrongly answers "not here". The fix is a **tombstone**: a marker that says "deleted, but keep searching past me". An insert may reuse a tombstone's slot.

```mermaid
flowchart LR
  accTitle: A search passes a tombstone
  accDescr: Searching for 19 starts at slot 3, which holds 3. Slot 4 holds a tombstone left by deleting 11, so the search continues. Slot 5 holds 19, so it is found.
  q["contains 19?"] --> t3["slot 3: 3, go on"] --> t4["slot 4: tombstone, go on"] --> t5["slot 5: 19, found"]
```

<!-- text-of-mermaid sha256:daf4a66d7f63226176ae93aa049dee2effe1b522998d1e81dc04509b0fe95b2e -->
```text
┌────────────┐    ┌────────────────┐    ┌────────────────────────┐    ┌─────────────────┐
│contains 19?├───►│slot 3: 3, go on├───►│slot 4: tombstone, go on├───►│slot 5: 19, found│
└────────────┘    └────────────────┘    └────────────────────────┘    └─────────────────┘
```

The example uses small integers hashed as `key % 8` so that every collision is easy to follow.

```python examples/open_addressing.py
"""Open addressing with linear probing: a key that finds its home slot taken tries the next one.

Keys are small integers hashed as `key % 8`, so that the collisions are easy to follow.
"""

SLOTS = 8
EMPTY = None
DELETED = "<deleted>"  # a tombstone: the slot is free to reuse, but a search goes on past it


class ProbingSet:
    def __init__(self) -> None:
        self.slots: list[int | str | None] = [EMPTY] * SLOTS

    def probe(self, key: int):
        """The slots to try for `key`: its home slot, then the next ones, wrapping around."""
        home = key % SLOTS
        return [(home + step) % SLOTS for step in range(SLOTS)]

    def add(self, key: int) -> list[int]:
        tried = []
        reusable = None
        for slot in self.probe(key):
            tried.append(slot)
            if self.slots[slot] == key:
                return tried
            if self.slots[slot] == DELETED and reusable is None:
                reusable = slot
            if self.slots[slot] is EMPTY:
                self.slots[slot if reusable is None else reusable] = key
                return tried
        raise RuntimeError("full: a real table resizes long before this")

    def contains(self, key: int) -> tuple[bool, list[int]]:
        tried = []
        for slot in self.probe(key):
            tried.append(slot)
            if self.slots[slot] is EMPTY:
                return False, tried
            if self.slots[slot] == key:
                return True, tried
        return False, tried

    def remove(self, key: int, tombstone: bool = True) -> None:
        for slot in self.probe(key):
            if self.slots[slot] == key:
                self.slots[slot] = DELETED if tombstone else EMPTY
                return


table = ProbingSet()
for key in (3, 11, 19, 6):
    print(f"add {key:>2}: home {key % SLOTS}, tried slots {table.add(key)}")
print("slots:", table.slots)

table.remove(11)
print("remove 11 with a tombstone:", table.slots)
print("contains 19?", table.contains(19))

broken = ProbingSet()
for key in (3, 11, 19):
    broken.add(key)
broken.remove(11, tombstone=False)
print("remove 11 by emptying its slot, contains 19?", broken.contains(19))
```

```output examples/open_addressing.py
add  3: home 3, tried slots [3]
add 11: home 3, tried slots [3, 4]
add 19: home 3, tried slots [3, 4, 5]
add  6: home 6, tried slots [6]
slots: [None, None, None, 3, 11, 19, 6, None]
remove 11 with a tombstone: [None, None, None, 3, '<deleted>', 19, 6, None]
contains 19? (True, [3, 4, 5])
remove 11 by emptying its slot, contains 19? (False, [3, 4])
```

```typescript examples/open_addressing.ts
// Open addressing with linear probing: a key that finds its home slot taken tries the next one.
//
// Keys are small integers hashed as `key % 8`, so that the collisions are easy to follow.

const SLOTS = 8;
const DELETED = "<deleted>"; // a tombstone: the slot is free to reuse, but a search goes on past it

type Slot = number | typeof DELETED | null;

class ProbingSet {
  slots: Slot[] = Array(SLOTS).fill(null);

  /** The slots to try for `key`: its home slot, then the next ones, wrapping around. */
  probe(key: number): number[] {
    const home = key % SLOTS;
    return Array.from({ length: SLOTS }, (_, step) => (home + step) % SLOTS);
  }

  add(key: number): number[] {
    const tried: number[] = [];
    let reusable: number | null = null;
    for (const slot of this.probe(key)) {
      tried.push(slot);
      if (this.slots[slot] === key) return tried;
      if (this.slots[slot] === DELETED && reusable === null) reusable = slot;
      if (this.slots[slot] === null) {
        this.slots[reusable ?? slot] = key;
        return tried;
      }
    }
    throw new Error("full: a real table resizes long before this");
  }

  contains(key: number): [boolean, number[]] {
    const tried: number[] = [];
    for (const slot of this.probe(key)) {
      tried.push(slot);
      if (this.slots[slot] === null) return [false, tried];
      if (this.slots[slot] === key) return [true, tried];
    }
    return [false, tried];
  }

  remove(key: number, tombstone = true): void {
    for (const slot of this.probe(key)) {
      if (this.slots[slot] === key) {
        this.slots[slot] = tombstone ? DELETED : null;
        return;
      }
    }
  }
}

const list = (items: readonly unknown[]): string => `[${items.map(String).join(", ")}]`;
const probed = ([found, tried]: [boolean, number[]]): string => `(${found}, ${list(tried)})`;

const table = new ProbingSet();
for (const key of [3, 11, 19, 6]) {
  const tried = table.add(key);
  console.log(`add ${String(key).padStart(2)}: home ${key % SLOTS}, tried slots ${list(tried)}`);
}
console.log("slots:", list(table.slots));

table.remove(11);
console.log("remove 11 with a tombstone:", list(table.slots));
console.log("contains 19?", probed(table.contains(19)));

const broken = new ProbingSet();
for (const key of [3, 11, 19]) broken.add(key);
broken.remove(11, false);
console.log("remove 11 by emptying its slot, contains 19?", probed(broken.contains(19)));
```

```output examples/open_addressing.ts
add  3: home 3, tried slots [3]
add 11: home 3, tried slots [3, 4]
add 19: home 3, tried slots [3, 4, 5]
add  6: home 6, tried slots [6]
slots: [null, null, null, 3, 11, 19, 6, null]
remove 11 with a tombstone: [null, null, null, 3, <deleted>, 19, 6, null]
contains 19? (true, [3, 4, 5])
remove 11 by emptying its slot, contains 19? (false, [3, 4])
```

```java examples/open_addressing.java
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

// Open addressing with linear probing: a key that finds its home slot taken tries the next one.
//
// Keys are small integers hashed as `key % 8`, so that the collisions are easy to follow.
public class OpenAddressing {
    static final int SLOTS = 8;
    // A tombstone: the slot is free to reuse, but a search goes on past it.
    static final String DELETED = "<deleted>";

    record Probe(boolean found, List<Integer> tried) {
        @Override
        public String toString() {
            return "(" + found + ", " + tried + ")";
        }
    }

    static final class ProbingSet {
        final Object[] slots = new Object[SLOTS]; // null is an empty slot

        /** The slots to try for `key`: its home slot, then the next ones, wrapping around. */
        int[] probe(int key) {
            int home = key % SLOTS;
            int[] order = new int[SLOTS];
            for (int step = 0; step < SLOTS; step++) {
                order[step] = (home + step) % SLOTS;
            }
            return order;
        }

        List<Integer> add(int key) {
            List<Integer> tried = new ArrayList<>();
            Integer reusable = null;
            for (int slot : probe(key)) {
                tried.add(slot);
                if (Integer.valueOf(key).equals(slots[slot])) {
                    return tried;
                }
                if (DELETED.equals(slots[slot]) && reusable == null) {
                    reusable = slot;
                }
                if (slots[slot] == null) {
                    slots[reusable == null ? slot : reusable] = key;
                    return tried;
                }
            }
            throw new IllegalStateException("full: a real table resizes long before this");
        }

        Probe contains(int key) {
            List<Integer> tried = new ArrayList<>();
            for (int slot : probe(key)) {
                tried.add(slot);
                if (slots[slot] == null) {
                    return new Probe(false, tried);
                }
                if (Integer.valueOf(key).equals(slots[slot])) {
                    return new Probe(true, tried);
                }
            }
            return new Probe(false, tried);
        }

        void remove(int key, boolean tombstone) {
            for (int slot : probe(key)) {
                if (Integer.valueOf(key).equals(slots[slot])) {
                    slots[slot] = tombstone ? DELETED : null;
                    return;
                }
            }
        }
    }

    public static void main(String[] args) {
        ProbingSet table = new ProbingSet();
        for (int key : new int[] {3, 11, 19, 6}) {
            List<Integer> tried = table.add(key);
            System.out.printf("add %2d: home %d, tried slots %s%n", key, key % SLOTS, tried);
        }
        System.out.println("slots: " + Arrays.toString(table.slots));

        table.remove(11, true);
        System.out.println("remove 11 with a tombstone: " + Arrays.toString(table.slots));
        System.out.println("contains 19? " + table.contains(19));

        ProbingSet broken = new ProbingSet();
        for (int key : new int[] {3, 11, 19}) {
            broken.add(key);
        }
        broken.remove(11, false);
        System.out.println("remove 11 by emptying its slot, contains 19? " + broken.contains(19));
    }
}
```

```output examples/open_addressing.java
add  3: home 3, tried slots [3]
add 11: home 3, tried slots [3, 4]
add 19: home 3, tried slots [3, 4, 5]
add  6: home 6, tried slots [6]
slots: [null, null, null, 3, 11, 19, 6, null]
remove 11 with a tombstone: [null, null, null, 3, <deleted>, 19, 6, null]
contains 19? (true, [3, 4, 5])
remove 11 by emptying its slot, contains 19? (false, [3, 4])
```

```kotlin examples/open_addressing.kt
// Open addressing with linear probing: a key that finds its home slot taken tries the next one.
//
// Keys are small integers hashed as `key % 8`, so that the collisions are easy to follow.

const val SLOTS = 8
const val DELETED = "<deleted>" // a tombstone: free to reuse, but a search goes on past it

class ProbingSet {
    val slots = arrayOfNulls<Any>(SLOTS) // null is an empty slot

    /** The slots to try for [key]: its home slot, then the next ones, wrapping around. */
    private fun probe(key: Int): List<Int> = List(SLOTS) { step -> (key % SLOTS + step) % SLOTS }

    fun add(key: Int): List<Int> {
        val tried = mutableListOf<Int>()
        var reusable: Int? = null
        for (slot in probe(key)) {
            tried.add(slot)
            if (slots[slot] == key) return tried
            if (slots[slot] == DELETED && reusable == null) reusable = slot
            if (slots[slot] == null) {
                slots[reusable ?: slot] = key
                return tried
            }
        }
        error("full: a real table resizes long before this")
    }

    fun contains(key: Int): Pair<Boolean, List<Int>> {
        val tried = mutableListOf<Int>()
        for (slot in probe(key)) {
            tried.add(slot)
            if (slots[slot] == null) return false to tried
            if (slots[slot] == key) return true to tried
        }
        return false to tried
    }

    fun remove(key: Int, tombstone: Boolean = true) {
        val slot = probe(key).firstOrNull { slots[it] == key } ?: return
        slots[slot] = if (tombstone) DELETED else null
    }
}

fun main() {
    val table = ProbingSet()
    for (key in listOf(3, 11, 19, 6)) {
        println("add %2d: home %d, tried slots %s".format(key, key % SLOTS, table.add(key)))
    }
    println("slots: ${table.slots.contentToString()}")

    table.remove(11)
    println("remove 11 with a tombstone: ${table.slots.contentToString()}")
    println("contains 19? ${table.contains(19)}")

    val broken = ProbingSet()
    for (key in listOf(3, 11, 19)) broken.add(key)
    broken.remove(11, tombstone = false)
    println("remove 11 by emptying its slot, contains 19? ${broken.contains(19)}")
}
```

```output examples/open_addressing.kt
add  3: home 3, tried slots [3]
add 11: home 3, tried slots [3, 4]
add 19: home 3, tried slots [3, 4, 5]
add  6: home 6, tried slots [6]
slots: [null, null, null, 3, 11, 19, 6, null]
remove 11 with a tombstone: [null, null, null, 3, <deleted>, 19, 6, null]
contains 19? (true, [3, 4, 5])
remove 11 by emptying its slot, contains 19? (false, [3, 4])
```

```go examples/open_addressing.go
// Open addressing with linear probing: a key that finds its home slot taken tries the next one.
//
// Keys are small integers hashed as `key % 8`, so that the collisions are easy to follow.
package main

import "fmt"

const slotCount = 8

// deleted is a tombstone: the slot is free to reuse, but a search goes on past it.
const deleted = "<deleted>"

// probingSet holds each key in a slot; nil is an empty slot.
type probingSet struct {
	slots [slotCount]any
}

// probe gives the slots to try for key: its home slot, then the next ones, wrapping around.
func probe(key int) []int {
	home := key % slotCount
	order := make([]int, slotCount)
	for step := range slotCount {
		order[step] = (home + step) % slotCount
	}
	return order
}

func (s *probingSet) add(key int) []int {
	var tried []int
	reusable := -1
	for _, slot := range probe(key) {
		tried = append(tried, slot)
		if s.slots[slot] == key {
			return tried
		}
		if s.slots[slot] == deleted && reusable == -1 {
			reusable = slot
		}
		if s.slots[slot] == nil {
			if reusable == -1 {
				reusable = slot
			}
			s.slots[reusable] = key
			return tried
		}
	}
	panic("full: a real table resizes long before this")
}

// contains reports whether key is in the set, and the slots it tried.
func (s *probingSet) contains(key int) (bool, []int) {
	var tried []int
	for _, slot := range probe(key) {
		tried = append(tried, slot)
		if s.slots[slot] == nil {
			return false, tried
		}
		if s.slots[slot] == key {
			return true, tried
		}
	}
	return false, tried
}

func (s *probingSet) remove(key int, tombstone bool) {
	for _, slot := range probe(key) {
		if s.slots[slot] == key {
			if tombstone {
				s.slots[slot] = deleted
			} else {
				s.slots[slot] = nil
			}
			return
		}
	}
}

func main() {
	var table probingSet
	for _, key := range []int{3, 11, 19, 6} {
		fmt.Printf("add %2d: home %d, tried slots %v\n", key, key%slotCount, table.add(key))
	}
	fmt.Println("slots:", table.slots)

	table.remove(11, true)
	fmt.Println("remove 11 with a tombstone:", table.slots)
	found, tried := table.contains(19)
	fmt.Println("contains 19?", found, tried)

	var broken probingSet
	for _, key := range []int{3, 11, 19} {
		broken.add(key)
	}
	broken.remove(11, false)
	found, tried = broken.contains(19)
	fmt.Println("remove 11 by emptying its slot, contains 19?", found, tried)
}
```

```output examples/open_addressing.go
add  3: home 3, tried slots [3]
add 11: home 3, tried slots [3 4]
add 19: home 3, tried slots [3 4 5]
add  6: home 6, tried slots [6]
slots: [<nil> <nil> <nil> 3 11 19 6 <nil>]
remove 11 with a tombstone: [<nil> <nil> <nil> 3 <deleted> 19 6 <nil>]
contains 19? true [3 4 5]
remove 11 by emptying its slot, contains 19? false [3 4]
```

Keys 3, 11 and 19 all have home slot 3, so each one probes further than the last. Removing 11 with a tombstone keeps 19 reachable; emptying the slot instead loses it. Tombstones have a price: they fill the table like live entries, so a table with many deletions resizes or rebuilds to clear them.

Open addressing keeps entries in one contiguous array, which is friendly to CPU caches and avoids a separate allocation per entry. It is also more sensitive to the load factor: as the table fills, runs of occupied slots merge into long clusters. Knuth's analysis of linear probing gives about `(1 + 1/(1 - α)) / 2` probes for a successful search and `(1 + 1/(1 - α)²) / 2` for an unsuccessful one, so at α = 0.5 a miss takes about 2.5 probes, and at α = 0.9 about 50. Classic linear-probing tables therefore resize at lower load factors than chaining tables do; newer open-addressing designs, such as the Swiss tables of the expert notes, keep probe sequences short in other ways and can run fuller.

### What may be a key

A key's hash must never change while it is stored, and equal keys must hash alike. Languages enforce this in different ways.

```python examples/keys_and_order.py
"""What Python's dict and set accept as keys, and the order a dict keeps."""

from dataclasses import dataclass

stock = {"apples": 3, "pears": 5, "plums": 1}
stock["apples"] = 4  # updating a key keeps its place
del stock["pears"]
stock["pears"] = 2  # a key added again goes to the end
print("insertion order:", list(stock))

for candidate in ([1, 2], {"a": 1}, {1, 2}):
    try:
        {candidate: "value"}
    except TypeError:
        print(f"{type(candidate).__name__:>5} as a key: TypeError, not hashable")
print("tuple as a key:", {(1, 2): "value"}[(1, 2)])


class Point:
    def __init__(self, x: int, y: int) -> None:
        self.x, self.y = x, y

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Point) and (self.x, self.y) == (other.x, other.y)


print("Point overrides __eq__ only, so its __hash__ is", Point.__hash__)


@dataclass(frozen=True)
class FrozenPoint:
    x: int
    y: int


visited = {FrozenPoint(0, 0), FrozenPoint(0, 0), FrozenPoint(1, 2)}
print("a frozen dataclass is hashable; the set holds", len(visited), "points")
```

It prints:

```output examples/keys_and_order.py
insertion order: ['apples', 'plums', 'pears']
 list as a key: TypeError, not hashable
 dict as a key: TypeError, not hashable
  set as a key: TypeError, not hashable
tuple as a key: value
Point overrides __eq__ only, so its __hash__ is None
a frozen dataclass is hashable; the set holds 2 points
```

- A Python `dict` keeps **insertion order**, guaranteed since Python 3.7 (it was an implementation detail of CPython 3.6). Updating a key keeps its place; a key deleted and added again goes to the end.
- Lists, dicts and sets are mutable, so Python refuses to hash them. A tuple of hashable values is hashable.
- A class that defines `__eq__` without `__hash__` has its `__hash__` set to `None`, which makes it unhashable instead of silently wrong. A frozen dataclass derives both from its fields, so two equal points are one key.

Java takes the opposite approach: any object can be a key, and keeping it unchanged is your job.

```java examples/MutableKey.java
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

// Java lets a mutable object be a key. Changing it while it is stored changes its hashCode, so the
// map looks for it in the wrong bucket.
public class MutableKey {
    public static void main(String[] args) {
        List<String> route = new ArrayList<>(List.of("home", "office"));
        Map<List<String>, Integer> minutes = new HashMap<>();
        minutes.put(route, 25);
        System.out.println("before: get(route) = " + minutes.get(route));

        route.add("gym");  // the key changes while it is in the map
        System.out.println("after:  get(route) = " + minutes.get(route));
        System.out.println("after:  containsKey(route) = " + minutes.containsKey(route));
        System.out.println("after:  size() = " + minutes.size());
        boolean stillThere = false;
        for (List<String> key : minutes.keySet()) {
            stillThere |= key == route;
        }
        System.out.println("after:  the same object is still a key = " + stillThere);
    }
}
```

It prints:

```output examples/MutableKey.java
before: get(route) = 25
after:  get(route) = null
after:  containsKey(route) = false
after:  size() = 1
after:  the same object is still a key = true
```

The list's hash code is defined from its elements, so adding `"gym"` changes it. The map still holds the entry, in the bucket chosen by the old hash, but `get` and `containsKey` now look in another bucket and find nothing. The entry is lost to lookups while it still takes space. Java's `Map` documentation warns about exactly this: the behavior of a map is not specified if a key changes in a way that affects `equals` while it is in the map.

## When to use it

- **"Have I seen this before?"** A set of what you have seen turns a quadratic scan of pairs into one pass. Each step asks the set and adds to it.
- **"What goes with this key?"** A map from a key to a value, a count, an index or a list: a lookup table, a cache, a group.
- **"Where was it?"** A map from a value to the position where it was seen.
- **Exact matches only.** For ranges, order or "the nearest key", use a sorted structure: a balanced tree (`TreeMap` in Java, `BTreeMap` in Rust) or a sorted array with binary search. A hash map has no order to search by.

A set or a map costs memory, a few times the size of the keys and values themselves. When the keys are small integers in a known range, such as letters `a` to `z`, a plain array indexed by the key does the same job with less memory and no hashing.

## Common traps

- **Mutating a key.** As the Java example shows, the entry becomes unreachable. Use immutable keys: strings, numbers, tuples, records, frozen dataclasses.
- **Defining equality without the hash.** Override both or neither, and derive both from the same fields.
- **Relying on order.** Python's `dict` and JavaScript's `Map` keep insertion order, but Python's `set` and Java's `HashMap` promise no order at all, and Go makes map iteration order unpredictable on purpose. Sort the keys when the output must be stable.
- **Treating "not found" as a value.** `ages.get("zed")` returns `None` in Python and `null` in Java, which may also be a stored value. Use `in` or `containsKey` when the difference matters.
- **Modifying a map while iterating over it.** Python raises `RuntimeError: dictionary changed size during iteration`; a Java `HashMap` that gains or loses a key during a loop over its keys throws `ConcurrentModificationException`, on a best-effort basis, while changing the value of an existing key is allowed; Go allows it but does not say whether an entry added during the loop will be visited. Collect the changes, then apply them.
- **Assuming the worst case cannot happen.** A poor hash, or keys chosen by someone hostile, can put everything in one bucket. See the expert notes.

## Complexity

With a hash function that spreads keys evenly and a load factor kept below a constant by resizing:

| Operation | Average | Worst case |
|-----------|---------|------------|
| Lookup, insert, delete | O(1) | O(n): every key in one bucket, or one long probe run |
| Insert, counting resizes | O(1) amortized | O(n) for the one insert that triggers a resize |
| Iterate over every entry | O(n + m) for chaining, O(m) for open addressing, with `m` buckets and `m` proportional to `n` | Same |
| Memory | O(n) | O(n) |

Why the average is O(1): with α kept at most, say, 0.75, the expected number of entries in a bucket is at most 0.75 under uniform hashing, so a lookup does the hash plus a constant expected number of comparisons. Hashing itself costs O(L) for a key of length L, so "O(1)" means O(1) hash computations and comparisons; for long strings, the hash and the final `==` comparison each cost O(L).

Why the worst case is O(n): nothing stops all keys from landing in one bucket. Chaining then walks one list of n entries, and linear probing walks one run of n slots. Some implementations bound this: in OpenJDK, a `HashMap` bucket that grows past 8 entries turns into a red-black tree once the table has at least 64 buckets, so a crowded bucket of keys that are `Comparable` costs O(log n), not O(n).

## Expert notes

- **Java `HashMap`.** Default capacity 16 buckets, default load factor 0.75, and the table rehashes into about twice as many buckets when entries exceed capacity times load factor, all as its documentation states. The capacity is a power of two, and the hash is spread first with `h ^ (h >>> 16)` so that the high bits influence the bucket. A bin is a linked list; adding an entry to a bin that already holds 8 (`TREEIFY_THRESHOLD`) turns it into a red-black tree, if the table has at least 64 buckets (`MIN_TREEIFY_CAPACITY`), and below that the table resizes instead. A tree bin becomes a list again when a resize splits it into a part of 6 entries or fewer (`UNTREEIFY_THRESHOLD`), or when removals leave the tree too small by a check of its shape. These constants are implementation details of OpenJDK's source, not guarantees of the API. The documentation only promises that when keys are `Comparable`, the class may use their order to break ties.
- **Python `dict` and `set`.** CPython's dict is an open-addressing table (its source says open addressing is preferred over chaining to avoid the link overhead), made compact and ordered in 3.6, with insertion order a language guarantee since 3.7. Its `set` is a separate hash table and keeps no order. `str` and `bytes` hashes are salted per process, so a set of strings iterates in a different order from run to run.
- **Go `map`.** The language specification says the iteration order over maps is not specified and is not guaranteed to be the same from one iteration to the next, and Go 1 made it unpredictable on purpose so that no program could come to depend on it. Since Go 1.12, `fmt` prints maps sorted by key, which makes test output stable without changing iteration. Go 1.24 rebuilt the built-in map on Swiss Tables, an open-addressing design.
- **JavaScript `Map` versus plain objects.** An object's keys are strings or symbols, so `obj[1]` and `obj["1"]` are the same property, and an object inherits keys from its prototype unless made with `Object.create(null)`. A `Map` takes any value as a key, compares keys with SameValueZero (so `NaN` finds `NaN`), iterates in insertion order, has a `size`, and is the one built for frequent additions and removals.
- **Rust `HashMap`.** Its default hasher is currently SipHash 1-3, randomly seeded, which the documentation says is subject to change, chosen to resist HashDoS: an attacker who cannot see the seed cannot compute which keys collide. The documentation says other hashers outperform it for small keys such as integers, but typically give up that protection; the table itself is a port of Google's SwissTable.
- **Robin Hood and Swiss tables.** Modern open-addressing tables attack long probes in two ways. Robin Hood hashing lets an inserted key take the slot of one that sits closer to its own home slot, which evens out probe lengths. Swiss tables keep one byte of metadata per slot, holding 7 bits of the key's hash and whether the slot is empty, full or deleted, and use SIMD instructions to narrow 16 candidates down to the few whose 7 bits match before comparing any key.
- **Resizing has a latency cost.** Amortized O(1) still means one insert in a while copies the whole table. Systems that cannot afford the pause resize incrementally, moving a few buckets on each operation, or size the table up front when they know how many entries are coming. In Java, `new HashMap<>(100)` is not enough for 100 entries: it makes 128 buckets, which resize past 96. `HashMap.newHashMap(100)`, since Java 19, sizes the table for 100 entries at the default load factor.

## Practice

- `cstudy start contains-duplicate`: the plainest "have I seen this before?". Compare the set against sorting, and against checking every pair.
- `cstudy start two-sum`: find two numbers that add up to a target, faster than by checking every pair.
- `cstudy start valid-anagram`: two strings, one question about their letters. A map of counts works for any alphabet; a fixed array works when the alphabet is small.

## Further reading

- [Java `HashMap`](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/HashMap.html): capacity, load factor 0.75, rehashing to about twice the buckets, and `Comparable` keys breaking ties.
- [Java `Map`](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/util/Map.html): the warning about mutable keys.
- [OpenJDK `HashMap` source](https://github.com/openjdk/jdk/blob/master/src/java.base/share/classes/java/util/HashMap.java): `TREEIFY_THRESHOLD`, `UNTREEIFY_THRESHOLD` and `MIN_TREEIFY_CAPACITY`.
- [Python `dict`](https://docs.python.org/3/library/stdtypes.html#mapping-types-dict): insertion order since 3.7, and which keys are allowed.
- [Python data model: `object.__hash__`](https://docs.python.org/3/reference/datamodel.html#object.__hash__): why overriding `__eq__` removes the hash.
- [The Go specification: for statements with range clause](https://go.dev/ref/spec#For_range): map iteration order is not specified; and the [Go 1 release notes](https://go.dev/doc/go1#iteration) on making it unpredictable.
- [Go 1.12 release notes](https://go.dev/doc/go1.12#fmt) (maps printed sorted) and [Go 1.24 release notes](https://go.dev/doc/go1.24#runtime) (Swiss Tables).
- [MDN: `Map`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Map): SameValueZero, insertion order, and the comparison with objects.
- [Rust `HashMap`](https://doc.rust-lang.org/std/collections/struct.HashMap.html): SipHash 1-3, HashDoS resistance and SwissTable.
