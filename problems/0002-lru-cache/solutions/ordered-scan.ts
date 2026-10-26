type Entry = { key: number; value: number };

export class LRUCache {
  private readonly capacity: number;
  // Ordered from least to most recently used.
  private readonly entries: Entry[] = [];

  constructor(capacity: number) {
    this.capacity = capacity;
  }

  get(key: number): number {
    const index = this.indexOf(key);
    if (index < 0) {
      return -1;
    }
    const [entry] = this.entries.splice(index, 1);
    this.entries.push(entry);
    return entry.value;
  }

  put(key: number, value: number): void {
    const index = this.indexOf(key);
    if (index >= 0) {
      this.entries.splice(index, 1);
    } else if (this.entries.length === this.capacity) {
      this.entries.shift();
    }
    this.entries.push({ key, value });
  }

  private indexOf(key: number): number {
    return this.entries.findIndex((entry) => entry.key === key);
  }
}
