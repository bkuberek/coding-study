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
