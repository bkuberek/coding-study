export class LRUCache {
  private readonly capacity: number;
  // A Map iterates in insertion order: least recently used first.
  private readonly entries = new Map<number, number>();
  // One iterator for the cache's whole life. Every key it has passed is deleted, so its next key
  // is the oldest one. A fresh `keys()` would rescan the deleted slots at the front each time.
  private readonly oldest = this.entries.keys();

  constructor(capacity: number) {
    this.capacity = capacity;
  }

  get(key: number): number {
    const value = this.entries.get(key);
    if (value === undefined) {
      return -1;
    }
    // Deleting and re-inserting moves the key to the end of the iteration order.
    this.entries.delete(key);
    this.entries.set(key, value);
    return value;
  }

  put(key: number, value: number): void {
    this.entries.delete(key);
    this.entries.set(key, value);
    if (this.entries.size > this.capacity) {
      const oldest = this.oldest.next();
      if (!oldest.done) {
        this.entries.delete(oldest.value);
      }
    }
  }
}
