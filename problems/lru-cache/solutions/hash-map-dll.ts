class Entry {
  readonly key: number;
  value: number;
  // A fresh entry links to itself, so the links are never null.
  prev: Entry = this;
  next: Entry = this;

  constructor(key: number, value: number) {
    this.key = key;
    this.value = value;
  }
}

export class LRUCache {
  private readonly capacity: number;
  private readonly entries = new Map<number, Entry>();
  // Sentinels: head.next is the least recently used entry, tail.prev the most recent.
  private readonly head = new Entry(0, 0);
  private readonly tail = new Entry(0, 0);

  constructor(capacity: number) {
    this.capacity = capacity;
    this.head.next = this.tail;
    this.tail.prev = this.head;
  }

  get(key: number): number {
    const entry = this.entries.get(key);
    if (entry === undefined) {
      return -1;
    }
    this.unlink(entry);
    this.append(entry);
    return entry.value;
  }

  put(key: number, value: number): void {
    let entry = this.entries.get(key);
    if (entry !== undefined) {
      entry.value = value;
      this.unlink(entry);
    } else {
      if (this.entries.size === this.capacity) {
        const oldest = this.head.next;
        this.unlink(oldest);
        this.entries.delete(oldest.key);
      }
      entry = new Entry(key, value);
      this.entries.set(key, entry);
    }
    this.append(entry);
  }

  private unlink(entry: Entry): void {
    entry.prev.next = entry.next;
    entry.next.prev = entry.prev;
  }

  private append(entry: Entry): void {
    const last = this.tail.prev;
    last.next = entry;
    entry.prev = last;
    entry.next = this.tail;
    this.tail.prev = entry;
  }
}
