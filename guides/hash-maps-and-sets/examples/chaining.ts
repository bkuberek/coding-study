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
